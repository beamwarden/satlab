from __future__ import annotations

"""
LoRa cross-link transceiver (Meshtastic), iteration 2 radio layer.

Wraps a meshtastic.serial_interface.SerialInterface for the Wio Tracker L1
attached to this node, and provides a health-vector send/receive path over
the mesh. See docs/crosslink-setup.md for the physical bring-up checklist
(region/channel config, node pairing) this module assumes is already done --
this file is Phase 5 (agent integration) only.

This is a resilience/redundancy signal, not the primary telemetry path: each
node still ingests its own health vector to Beamwarden directly over
USB/WiFi via BeamwardenClient (see main.py). The cross-link additionally
broadcasts a compact summary so a neighbor can observe this node's state
even if this node's own ground link is down -- the scenario the SBIR
proposal's cross-link requirement is actually for.

Meshtastic's maximum text payload is 237 bytes. A full HealthVector
.to_payload() (five subsystems, active-fault text, ae/nis summaries) is far
over that. COMPACT_KEYS below trims to the four fields a neighbor actually
needs: sequence (detect gaps/reordering), top-level state,
mission_capability, and available_for_tasking. Per-subsystem detail and
fault text stay ground-side-only, reachable via the node's own direct
Beamwarden ingest -- not lost, just not repeated over the radio budget. The
sender's own node ID is Meshtastic's problem, not the payload's:
SerialInterface exposes it in the packet metadata (fromId) on receive, so it
is not duplicated here.

Environment variables (see also docs/crosslink-setup.md):
    SATLAB_CROSSLINK_PORT   Serial device for the Wio Tracker (by-id path)
    SATLAB_PEER_NODE_ID     Meshtastic node ID of the peer, e.g. "!a1b2c3d4"
"""

import json
import logging
from typing import Callable

logger = logging.getLogger(__name__)

# NodeState.value -> single-char wire code. Keep in sync with health.NodeState;
# a state missing here is a bug (encode_compact raises rather than emitting a
# placeholder a stale receiver couldn't decode).
_STATE_CODES: dict[str, str] = {
    "NOMINAL":   "N",
    "DEGRADED":  "D",
    "CRITICAL":  "C",
    "SAFE_MODE": "F",
    "SILENT":    "X",
}
_STATE_CODES_REVERSE: dict[str, str] = {v: k for k, v in _STATE_CODES.items()}

MAX_PAYLOAD_BYTES = 237


def encode_compact(vector_payload: dict) -> str:
    """
    Compress a HealthVector.to_payload() dict to a short-key JSON string for
    the mesh radio link. Raises ValueError if the state is unrecognized, or
    if the result would still exceed MAX_PAYLOAD_BYTES -- the four fields
    kept here should never get close, but a payload shape change elsewhere
    shouldn't fail silently over the air.
    """
    state = vector_payload["state"]
    if state not in _STATE_CODES:
        raise ValueError(f"unknown health state {state!r}, add it to _STATE_CODES")

    compact = {
        "s": vector_payload["sequence"],
        "t": _STATE_CODES[state],
        "c": vector_payload["mission_capability"],
        "a": 1 if vector_payload["available_for_tasking"] else 0,
    }
    encoded = json.dumps(compact, separators=(",", ":"))
    size = len(encoded.encode("utf-8"))
    if size > MAX_PAYLOAD_BYTES:
        raise ValueError(
            f"compact health vector is {size} bytes, exceeds the "
            f"{MAX_PAYLOAD_BYTES}-byte Meshtastic payload limit"
        )
    return encoded


def decode_compact(text: str) -> dict:
    """
    Inverse of encode_compact. Raises ValueError on malformed input -- e.g. a
    stray human text message on the shared channel that isn't one of our
    packets. Callers should catch this and skip the packet rather than crash
    the receive loop.
    """
    try:
        raw = json.loads(text)
        return {
            "sequence":              raw["s"],
            "state":                 _STATE_CODES_REVERSE[raw["t"]],
            "mission_capability":    raw["c"],
            "available_for_tasking": bool(raw["a"]),
        }
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"not a valid compact health vector: {text!r}") from exc


class CrosslinkTransceiver:
    """
    Owns the Meshtastic SerialInterface for this node's Wio Tracker and the
    one peer this bench setup talks to (docs/crosslink-setup.md is written
    for exactly two nodes; broadcast-to-many is future scope).
    """

    def __init__(self, port: str, peer_node_id: str) -> None:
        # Imported here, not at module level: meshtastic pulls in protobuf/
        # pubsub, and every other module in this package should stay
        # importable (and testable) without it if this file is never touched.
        from meshtastic.serial_interface import SerialInterface
        from pubsub import pub

        self._peer_node_id = peer_node_id
        self._on_peer_vector: Callable[[dict], None] | None = None
        self._iface = SerialInterface(port)
        pub.subscribe(self._on_receive, "meshtastic.receive.text")

    def send_health_vector(self, vector_payload: dict) -> bool:
        """
        Encode and transmit this node's health vector to the peer. Returns
        False (and logs) on any encode or transport failure rather than
        raising -- a failed cross-link send must never take down the main
        ingest loop in main.py.
        """
        try:
            encoded = encode_compact(vector_payload)
        except ValueError as exc:
            logger.warning("crosslink encode failed: %s", exc)
            return False
        try:
            self._iface.sendText(encoded, destinationId=self._peer_node_id)
        except Exception as exc:  # meshtastic raises assorted transport errors
            logger.warning("crosslink send failed: %s", exc)
            return False
        logger.debug(
            "crosslink tx seq=%s -> %s", vector_payload.get("sequence"), self._peer_node_id,
        )
        return True

    def on_peer_vector(self, callback: Callable[[dict], None]) -> None:
        """
        Register a callback invoked with the decoded dict each time a peer
        health vector is received. main.py uses this to log receipt per
        docs/crosslink-setup.md Phase 5 -- it does not re-ingest peer data to
        Beamwarden under this node's own token (see module docstring: each
        node ingests its own vector directly).
        """
        self._on_peer_vector = callback

    def _on_receive(self, packet: dict, interface) -> None:
        from_id = packet.get("fromId")
        if from_id != self._peer_node_id:
            return  # not our bench peer -- ignore other mesh traffic
        text = packet.get("decoded", {}).get("text")
        if text is None:
            return
        try:
            vector = decode_compact(text)
        except ValueError as exc:
            logger.debug("ignoring non-health-vector text from %s: %s", from_id, exc)
            return
        logger.info(
            "crosslink rx from %s: seq=%s state=%s capability=%.2f",
            from_id, vector["sequence"], vector["state"], vector["mission_capability"],
        )
        if self._on_peer_vector:
            self._on_peer_vector(vector)

    def close(self) -> None:
        self._iface.close()
