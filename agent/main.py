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
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

from beamwarden import BeamwardenClient
from bench import Benchmarker
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


def main() -> None:
    serial_port = _require_env("SATLAB_SERIAL_PORT")
    bw_url      = _require_env("BEAMWARDEN_URL")
    bw_token    = _require_env("BEAMWARDEN_TOKEN")
    norad_id    = os.environ.get("SATLAB_NORAD_ID", "25544")

    client     = BeamwardenClient(bw_url, bw_token)
    propagator = OrbitalPropagator(norad_id)
    vector     = HealthVector()
    bench      = Benchmarker()

    def _on_exit(signum, frame):
        bench.log_summary()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _on_exit)
    signal.signal(signal.SIGTERM, _on_exit)

    logger.info(
        "satlab agent starting — port=%s beamwarden=%s norad=%s node_id=%s",
        serial_port, bw_url, norad_id, vector.node_id,
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
            client.ingest(
                sensor_name="health_vector",
                recorded_at=now,
                payload=vector.to_payload(now),
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
