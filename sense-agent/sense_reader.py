from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sense_hat import SenseHat

logger = logging.getLogger(__name__)


@dataclass
class ImuReading:
    ts: datetime
    accel_x_g: float
    accel_y_g: float
    accel_z_g: float
    gyro_x_dps: float
    gyro_y_dps: float
    gyro_z_dps: float
    mag_x_ut: float
    mag_y_ut: float
    mag_z_ut: float


@dataclass
class EnvReading:
    ts: datetime
    temp_hts221_c: float
    humidity_pct: float
    temp_lps25h_c: float
    pressure_mbar: float


class SenseReader:
    def __init__(self) -> None:
        self.sense = SenseHat()
        self.sense.set_imu_config(True, True, True)  # compass, gyro, accel

    def read_imu(self) -> ImuReading:
        accel = self.sense.get_accelerometer_raw()
        gyro  = self.sense.get_gyroscope_raw()
        mag   = self.sense.get_compass_raw()
        return ImuReading(
            ts=datetime.now(timezone.utc),
            accel_x_g=round(accel["x"], 4),
            accel_y_g=round(accel["y"], 4),
            accel_z_g=round(accel["z"], 4),
            gyro_x_dps=round(gyro["x"], 4),
            gyro_y_dps=round(gyro["y"], 4),
            gyro_z_dps=round(gyro["z"], 4),
            mag_x_ut=round(mag["x"], 4),
            mag_y_ut=round(mag["y"], 4),
            mag_z_ut=round(mag["z"], 4),
        )

    def read_env(self) -> EnvReading:
        return EnvReading(
            ts=datetime.now(timezone.utc),
            temp_hts221_c=round(self.sense.get_temperature(), 2),
            humidity_pct=round(self.sense.get_humidity(), 2),
            temp_lps25h_c=round(self.sense.get_temperature_from_pressure(), 2),
            pressure_mbar=round(self.sense.get_pressure(), 2),
        )
