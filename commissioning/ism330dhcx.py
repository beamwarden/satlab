from __future__ import annotations

import time

import smbus2

# Register map
_WHO_AM_I = 0x0F
_CTRL1_XL = 0x10  # accel: ODR, FS, LPF2
_CTRL2_G  = 0x11  # gyro: ODR, FS, FS_125
_STATUS   = 0x1E  # bit0=XLDA, bit1=GDA
_OUTX_L_G = 0x22  # first of 12 contiguous output bytes (gyro then accel)

_WHO_AM_I_EXPECTED = 0x6B  # ISM330DHCX

# CTRL1_XL: ODR=104 Hz (0x4<<4), FS=±2g (0x0<<2), LPF2 disabled
_CTRL1_XL_VAL = 0x40
# CTRL2_G: ODR=104 Hz (0x4<<4), FS_125=1 → ±125 dps
_CTRL2_G_VAL  = 0x42

ACCEL_SENS_G   = 0.061e-3   # g/LSB at ±2g
GYRO_SENS_DPS  = 4.375e-3   # dps/LSB at ±125 dps
ODR_HZ         = 104.0


def _s16(lo: int, hi: int) -> int:
    v = lo | (hi << 8)
    return v - 65536 if v >= 32768 else v


class ISM330DHCX:
    """
    Direct-register I2C driver for the ISM330DHCX 6-DoF IMU via smbus2.

    Two units can share one I2C bus via different SA0 pin states:
        addr=0x6A  (SA0 low)
        addr=0x6B  (SA0 high)

    Configured at 104 Hz / ±2g / ±125 dps for maximum noise-floor sensitivity.
    In I2C mode, the ISM330DHCX auto-increments the register address on
    multi-byte reads (IF_INC default=1), so a single read from OUTX_L_G
    returns all 12 output bytes in order: gx, gy, gz, ax, ay, az.
    """

    def __init__(self, bus: int = 1, addr: int = 0x6A) -> None:
        self._bus  = smbus2.SMBus(bus)
        self._addr = addr
        who = self._bus.read_byte_data(addr, _WHO_AM_I)
        if who != _WHO_AM_I_EXPECTED:
            raise RuntimeError(
                f"WHO_AM_I mismatch at 0x{addr:02X}: "
                f"got 0x{who:02X}, expected 0x{_WHO_AM_I_EXPECTED:02X}"
            )
        self._bus.write_byte_data(addr, _CTRL1_XL, _CTRL1_XL_VAL)
        self._bus.write_byte_data(addr, _CTRL2_G,  _CTRL2_G_VAL)
        time.sleep(0.05)  # one ODR period to settle

    def read_raw(self) -> tuple[float, float, float, float, float, float] | None:
        """
        Return (ax_g, ay_g, az_g, gx_dps, gy_dps, gz_dps) or None if no new sample.
        Caller should poll; new data arrives at ~9.6 ms intervals at 104 Hz.
        """
        status = self._bus.read_byte_data(self._addr, _STATUS)
        if not (status & 0x03):
            return None
        raw = self._bus.read_i2c_block_data(self._addr, _OUTX_L_G, 12)
        gx = _s16(raw[0],  raw[1])  * GYRO_SENS_DPS
        gy = _s16(raw[2],  raw[3])  * GYRO_SENS_DPS
        gz = _s16(raw[4],  raw[5])  * GYRO_SENS_DPS
        ax = _s16(raw[6],  raw[7])  * ACCEL_SENS_G
        ay = _s16(raw[8],  raw[9])  * ACCEL_SENS_G
        az = _s16(raw[10], raw[11]) * ACCEL_SENS_G
        return ax, ay, az, gx, gy, gz

    def close(self) -> None:
        self._bus.close()
