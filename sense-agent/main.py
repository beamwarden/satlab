from __future__ import annotations

import logging
import os
import signal
import sys
import time

from beamwarden import BeamwardenClient
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


def main() -> None:
    bw_url   = _require_env("BEAMWARDEN_URL")
    bw_token = _require_env("BEAMWARDEN_TOKEN")

    client  = BeamwardenClient(bw_url, bw_token)
    reader  = SenseReader()
    display = LedDisplay(reader.sense)

    shutdown = False

    def _on_signal(sig, frame):  # noqa: ANN001
        nonlocal shutdown
        logger.info("shutdown signal received")
        shutdown = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT,  _on_signal)

    logger.info("sense-agent starting (beamrider-0004)")
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
    logger.info("sense-agent stopped")


if __name__ == "__main__":
    main()
