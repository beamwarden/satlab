from __future__ import annotations

"""
satlab RPi agent — iteration 1 (serial/USB)

Reads JSON telemetry packets from the Arduino over serial, overlays orbital
state from SGP4, and ingests everything to Beamwarden as a Beamrider node.

Required environment variables:
    SATLAB_SERIAL_PORT    Serial device (e.g. /dev/ttyUSB0 or /dev/ttyACM0)
    BEAMWARDEN_URL        Base URL of Beamwarden (e.g. http://192.168.1.10:8000)
    BEAMWARDEN_TOKEN      Beamrider bearer token from Beamwarden
    SATLAB_NORAD_ID       NORAD ID to propagate (default: 25544 — ISS)
"""

import logging
import os
import sys
from datetime import datetime, timezone

from beamwarden import BeamwardenClient
from orbit import OrbitalPropagator
from serial_reader import read_packets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("satlab.agent")

# How often to push an orbital state reading regardless of sensor cadence (s).
ORBIT_INTERVAL_S = 30


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        logger.error("missing required environment variable: %s", name)
        sys.exit(1)
    return val


def main() -> None:
    serial_port  = _require_env("SATLAB_SERIAL_PORT")
    bw_url       = _require_env("BEAMWARDEN_URL")
    bw_token     = _require_env("BEAMWARDEN_TOKEN")
    norad_id     = os.environ.get("SATLAB_NORAD_ID", "25544")

    client      = BeamwardenClient(bw_url, bw_token)
    propagator  = OrbitalPropagator(norad_id)

    last_orbit_push: float = 0.0

    logger.info("satlab agent starting — port=%s beamwarden=%s norad=%s",
                serial_port, bw_url, norad_id)

    for packet in read_packets(serial_port):
        now = datetime.now(timezone.utc)

        subsystem   = packet.get("subsystem", "unknown")
        sensor_name = packet.get("sensor", "unknown")
        payload     = packet.get("payload", {})

        # System init packets are informational — log and skip ingestion.
        if subsystem == "system" and sensor_name == "init":
            logger.info("arduino init: %s", payload)
            continue

        ts_str = packet.get("ts", now.isoformat())
        try:
            recorded_at = datetime.fromisoformat(ts_str)
        except ValueError:
            recorded_at = now

        ok = client.ingest(
            sensor_name=f"{subsystem}_{sensor_name}",
            recorded_at=recorded_at,
            payload=payload,
        )
        if ok:
            logger.debug("ingested %s/%s", subsystem, sensor_name)

        # Push orbital state on interval, tied to any incoming packet as a tick.
        import time
        elapsed = time.monotonic() - last_orbit_push
        if elapsed >= ORBIT_INTERVAL_S:
            state = propagator.propagate(now)
            client.ingest(
                sensor_name="orbit_sgp4",
                recorded_at=now,
                payload=state.to_payload(),
            )
            last_orbit_push = time.monotonic()
            logger.debug("orbit state pushed: error_code=%d", state.error_code)


if __name__ == "__main__":
    main()
