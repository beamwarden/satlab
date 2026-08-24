from __future__ import annotations

"""
satlab Sense HAT agent (beamrider-0004).

Required environment variables:
    BEAMWARDEN_URL   Base URL of Beamwarden (e.g. http://192.168.1.10:8000)
    BEAMWARDEN_TOKEN Beamrider bearer token from Beamwarden

Optional (LoRa cross-link, see docs/crosslink-setup.md and crosslink.py):
    SATLAB_CROSSLINK_PORT Serial device for the Wio Tracker (by-id path). If
                          unset, the cross-link is skipped entirely -- nodes
                          without this hardware are unaffected.
    SATLAB_PEER_NODE_ID   Meshtastic node ID of the peer node, e.g. "!a1b2c3d4".
                          Required together with SATLAB_CROSSLINK_PORT.

This node has no HealthVector of its own (unlike agent/main.py's
beamrider-0003) -- the cross-link here is receive-only: it logs the peer's
incoming health vector but never calls send_health_vector.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

from beamwarden import BeamwardenClient
from crosslink import CrosslinkTransceiver
from led_display import Health, LedDisplay
from sense_reader import SenseReader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

READ_INTERVAL_S = 10


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        logger.critical("missing required env var: %s", name)
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
    bw_url   = _require_env("BEAMWARDEN_URL")
    bw_token = _require_env("BEAMWARDEN_TOKEN")

    client  = BeamwardenClient(bw_url, bw_token)
    reader  = SenseReader()
    display = LedDisplay(reader.sense)

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

    shutdown = False

    def _on_signal(sig, frame):  # noqa: ANN001
        nonlocal shutdown
        logger.info("shutdown signal received")
        shutdown = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT,  _on_signal)

    logger.info(
        "sense-agent starting (beamrider-0004) crosslink=%s",
        peer_node_id if crosslink else "disabled",
    )
    display.set_health(Health.FAULT)  # amber until first successful cycle

    while not shutdown:
        ok = 0
        fail = 0

        try:
            imu = reader.read_imu()
            if client.ingest("lsm9ds1", imu.ts, {
                "accel_x_g":   imu.accel_x_g,
                "accel_y_g":   imu.accel_y_g,
                "accel_z_g":   imu.accel_z_g,
                "gyro_x_dps":  imu.gyro_x_dps,
                "gyro_y_dps":  imu.gyro_y_dps,
                "gyro_z_dps":  imu.gyro_z_dps,
                "mag_x_ut":    imu.mag_x_ut,
                "mag_y_ut":    imu.mag_y_ut,
                "mag_z_ut":    imu.mag_z_ut,
            }):
                ok += 1
            else:
                fail += 1
        except Exception as exc:
            logger.error("imu read/ingest failed: %s", exc)
            fail += 1

        try:
            env = reader.read_env()
            if client.ingest("hts221", env.ts, {
                "temp_c":       env.temp_hts221_c,
                "humidity_pct": env.humidity_pct,
            }):
                ok += 1
            else:
                fail += 1

            if client.ingest("lps25h", env.ts, {
                "temp_c":        env.temp_lps25h_c,
                "pressure_mbar": env.pressure_mbar,
            }):
                ok += 1
            else:
                fail += 1
        except Exception as exc:
            logger.error("env read/ingest failed: %s", exc)
            fail += 1

        if fail == 0:
            display.set_health(Health.OK)
        elif ok > 0:
            display.set_health(Health.DEGRADED)
        else:
            display.set_health(Health.FAULT)

        logger.info("cycle ok=%d fail=%d", ok, fail)
        time.sleep(READ_INTERVAL_S)

    display.off()
    if crosslink:
        crosslink.close()
    logger.info("sense-agent stopped")


if __name__ == "__main__":
    main()
