from __future__ import annotations

"""
satlab RPi agent — iteration 1 (serial/USB)

Reads JSON telemetry packets from the Arduino over serial, runs Tier 1
threshold checks, maintains a health vector, overlays orbital state from
SGP4, and ingests everything to Beamwarden as a Beamrider node.

Required environment variables:
    SATLAB_SERIAL_PORT    Serial device (e.g. /dev/ttyUSB0 or /dev/ttyACM0)
    BEAMWARDEN_URL        Base URL of Beamwarden (e.g. http://192.168.1.10:8000)
    BEAMWARDEN_TOKEN      Beamrider bearer token from Beamwarden
    SATLAB_NORAD_ID       NORAD ID to propagate (default: 25544 — ISS)
    SATLAB_NODE_ID        Stable node identity UUID (generated at startup if absent)

Optional (LoRa cross-link, see docs/crosslink-setup.md and crosslink.py):
    SATLAB_CROSSLINK_PORT Serial device for the Wio Tracker (by-id path). If
                          unset, the cross-link is skipped entirely -- nodes
                          without this hardware are unaffected.
    SATLAB_PEER_NODE_ID   Meshtastic node ID of the peer node, e.g. "!a1b2c3d4".
                          Required together with SATLAB_CROSSLINK_PORT.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

from beamwarden import BeamwardenClient
from bench import Benchmarker
from crosslink import CrosslinkTransceiver
from health import HealthVector, NodeState
from orbit import OrbitalPropagator
from serial_reader import read_packets
from thresholds import ViolationLevel, evaluate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("satlab.agent")

ORBIT_INTERVAL_S       = 30
_HV_INTERVAL_NOMINAL_S  = 30
_HV_INTERVAL_DEGRADED_S = 10

# Maps the combined sensor key (subsystem_sensor) to the health vector subsystem.
_SENSOR_SUBSYSTEM: dict[str, str] = {
    "eps_light":         "eps",
    "structural_sound":  "structural",
    "structural_bmp280": "structural",
    "tcs_dht":           "tcs",
    "adcs_lis3dh":       "adcs",
    "orbit_sgp4":        "orbit",
}


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        logger.error("missing required environment variable: %s", name)
        sys.exit(1)
    return val


def _on_peer_vector(client: BeamwardenClient, peer_node_id: str, vector: dict) -> None:
    """Log a received peer health vector and record it in Beamwarden as this
    node's own "I heard my fallback-channel peer" activity -- ingested under
    this node's own token, as crosslink_rx, never as the peer's health_vector
    (that would misattribute the peer's data to this device; the peer already
    ingests its own health_vector directly over its own ground link).

    Deliberately omits the peer's raw sequence number from the payload: it's
    a monotonic counter that resets on the peer's own process restarts, and
    re-exposing it here as a numeric field would recreate the exact
    UKF-anomaly false-positive this project already found and fixed on the
    beamwarden side once (see beamwarden PR #205)."""
    logger.info(
        "peer health vector: seq=%s state=%s capability=%.2f tasking=%s",
        vector["sequence"], vector["state"], vector["mission_capability"], vector["available_for_tasking"],
    )
    if not client.ingest(
        sensor_name="crosslink_rx",
        recorded_at=datetime.now(timezone.utc),
        payload={
            "peer_node_id": peer_node_id,
            "peer_state": vector["state"],
            "peer_mission_capability": vector["mission_capability"],
            "peer_available_for_tasking": vector["available_for_tasking"],
        },
    ):
        logger.warning("crosslink_rx ingest failed for peer %s", peer_node_id)


def main() -> None:
    serial_port = _require_env("SATLAB_SERIAL_PORT")
    bw_url      = _require_env("BEAMWARDEN_URL")
    bw_token    = _require_env("BEAMWARDEN_TOKEN")
    norad_id    = os.environ.get("SATLAB_NORAD_ID", "25544")

    client     = BeamwardenClient(bw_url, bw_token)
    propagator = OrbitalPropagator(norad_id)
    vector     = HealthVector()
    bench      = Benchmarker()

    crosslink_port = os.environ.get("SATLAB_CROSSLINK_PORT")
    peer_node_id   = os.environ.get("SATLAB_PEER_NODE_ID")
    crosslink: CrosslinkTransceiver | None = None
    if crosslink_port and peer_node_id:
        # The radio can be mid-reboot (e.g. right after a config write) when
        # this runs. A connection failure here must not take down the whole
        # agent -- ingestion of the actual sensor data is the primary job;
        # the cross-link is a bonus. Found live 2026-08-23: an unguarded
        # construction here crashed the entire process (not just crosslink)
        # when the Wio Tracker wasn't ready yet, and systemd's restart-on-
        # failure was the only thing that recovered it.
        try:
            crosslink = CrosslinkTransceiver(crosslink_port, peer_node_id)
        except Exception as exc:
            logger.warning("crosslink connection failed, continuing without it: %s", exc)
            crosslink = None
        else:
            crosslink.on_peer_vector(lambda v: _on_peer_vector(client, peer_node_id, v))
    elif crosslink_port or peer_node_id:
        logger.warning(
            "SATLAB_CROSSLINK_PORT and SATLAB_PEER_NODE_ID must both be set "
            "to enable the cross-link -- cross-link disabled"
        )

    def _on_exit(signum, frame):
        bench.log_summary()
        if crosslink:
            crosslink.close()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _on_exit)
    signal.signal(signal.SIGTERM, _on_exit)

    logger.info(
        "satlab agent starting — port=%s beamwarden=%s norad=%s node_id=%s crosslink=%s",
        serial_port, bw_url, norad_id, vector.node_id,
        peer_node_id if crosslink else "disabled",
    )

    last_orbit_push: float = 0.0
    last_hv_push:    float = 0.0
    last_bench_push: float = 0.0
    prev_hv_state          = vector.state

    for packet in read_packets(serial_port):
        now = datetime.now(timezone.utc)

        subsystem   = packet.get("subsystem", "unknown")
        sensor_name = packet.get("sensor", "unknown")
        payload     = packet.get("payload", {})

        if subsystem == "system" and sensor_name == "init":
            logger.info("arduino init: %s", payload)
            continue

        # serial_reader guarantees ts is already replaced with a UTC-aware ISO
        # string. Parse it to preserve the exact measurement timestamp set by
        # the reader. Reject naive datetimes (Arduino firmware sending a bare
        # ISO string without tz offset) rather than silently storing them.
        ts_str = packet.get("ts", "")
        try:
            recorded_at = datetime.fromisoformat(ts_str)
            if recorded_at.tzinfo is None:
                logger.warning("ts field missing timezone, using now: %r", ts_str)
                recorded_at = now
        except ValueError:
            recorded_at = now

        full_sensor = f"{subsystem}_{sensor_name}"

        if not client.ingest(sensor_name=full_sensor, recorded_at=recorded_at, payload=payload):
            logger.warning("ingest failed for %s — reading dropped", full_sensor)

        # ── Tier 1 threshold evaluation ───────────────────────────────────────
        violations = evaluate(full_sensor, payload)
        sub_name   = _SENSOR_SUBSYSTEM.get(full_sensor)
        if sub_name:
            vector.record_sensor(full_sensor, sub_name, violations)
        for v in violations:
            if v.level == ViolationLevel.HARD:
                logger.warning("TIER1 HARD  %s: %s", full_sensor, v.message)
            else:
                logger.info("TIER1 SOFT  %s: %s", full_sensor, v.message)

        mono = time.monotonic()

        # ── Orbital state push ────────────────────────────────────────────────
        if mono - last_orbit_push >= ORBIT_INTERVAL_S:
            state         = propagator.propagate(now)
            orbit_payload = state.to_payload()
            client.ingest(sensor_name="orbit_sgp4", recorded_at=now, payload=orbit_payload)
            orbit_violations = evaluate("orbit_sgp4", orbit_payload)
            vector.record_sensor("orbit_sgp4", "orbit", orbit_violations)
            last_orbit_push = mono
            logger.debug("orbit state pushed: error_code=%d", state.error_code)

        # ── Health vector push ────────────────────────────────────────────────
        hv_interval = (
            _HV_INTERVAL_DEGRADED_S
            if vector.state in (NodeState.DEGRADED, NodeState.CRITICAL)
            else _HV_INTERVAL_NOMINAL_S
        )
        if mono - last_hv_push >= hv_interval:
            vector.refresh()
            hv_payload = vector.to_payload(now)
            client.ingest(
                sensor_name="health_vector",
                recorded_at=now,
                payload=hv_payload,
            )
            if crosslink and crosslink.send_health_vector(hv_payload):
                client.ingest(
                    sensor_name="crosslink_tx",
                    recorded_at=now,
                    payload={"peer_node_id": peer_node_id},
                )

            bench_reading = bench.sample()
            client.ingest(
                sensor_name="kpp_bench",
                recorded_at=now,
                payload=bench_reading,
            )
            last_bench_push = mono
            last_hv_push = mono

            if vector.state != prev_hv_state:
                logger.info(
                    "health state: %s → %s  capability=%.2f  tasking=%s",
                    prev_hv_state.value, vector.state.value,
                    vector.mission_capability, vector.available_for_tasking,
                )
                prev_hv_state = vector.state
            else:
                logger.debug(
                    "health vector seq=%d state=%s capability=%.2f",
                    vector.sequence, vector.state.value, vector.mission_capability,
                )


if __name__ == "__main__":
    main()
