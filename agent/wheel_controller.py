from __future__ import annotations

"""
Outer attitude loop for the reaction-wheel demonstrator.

Reads a BNO055 quaternion directly off the RPi's own I2C bus (see
docs/reaction-wheel.md Build sequence step 5 -- BNO055 does NOT go through
the Uno Q), extracts yaw (this is a single-axis demonstrator; the pivot
frame's axle is vertical, so yaw is the only rotation the platform is free
to make), and runs an attitude PID against a commanded target to produce a
wheel velocity setpoint written to the Uno Q over serial.

PID gains are the charleslabs heritage starting point noted in
docs/reaction-wheel.md ("Control heritage"): P=2.5, I=0, D=400. Their
controller runs on a stepper driving a full mechanical assembly directly;
ours drives a velocity setpoint into SimpleFOC's own inner loop, so these
are a starting point for bench tuning (build sequence step 6), not assumed
correct as-is.

NOT yet wired to Beamwarden: BeamwardenClient (beamwarden.py) currently only
exposes ingest(), no command-fetch/subscription endpoint. set_target() is
directly callable (e.g. from a bench-test script) for build sequence step 6
ahead of that integration.
"""

import logging
import math
import time
from dataclasses import dataclass

import serial
from smbus2 import SMBus

logger = logging.getLogger(__name__)

_BNO055_ADDR = 0x28
_BNO055_CHIP_ID_REG = 0x00
_BNO055_CHIP_ID_EXPECTED = 0xA0
_BNO055_OPR_MODE_REG = 0x3D
_BNO055_OPR_MODE_CONFIG = 0x00
_BNO055_OPR_MODE_NDOF = 0x0C
_BNO055_QUATERNION_REG = 0x20
_BNO055_QUATERNION_SCALE = 1.0 / 16384.0  # datasheet: 1 LSB = 2^-14

_OUTER_LOOP_HZ = 20  # docs/reaction-wheel.md: "~20Hz; much slower than the
                      # inner loop to maintain cascade stability"


@dataclass
class Quaternion:
    w: float
    x: float
    y: float
    z: float


def _quat_to_yaw(q: Quaternion) -> float:
    """Extract yaw (rotation about Z) in radians, standard aerospace convention."""
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def _wrap_pi(angle: float) -> float:
    """Wrap an angle to (-pi, pi] -- mirrors the charleslabs PIDAngleController's ±180° wrap."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


class _PID:
    def __init__(self, p: float, i: float, d: float) -> None:
        self.p, self.i, self.d = p, i, d
        self._integral = 0.0
        self._prev_error: float | None = None

    def step(self, error: float, dt: float) -> float:
        self._integral += error * dt
        derivative = 0.0 if self._prev_error is None else (error - self._prev_error) / dt
        self._prev_error = error
        return self.p * error + self.i * self._integral + self.d * derivative


class BNO055:
    """Minimal direct-I2C NDOF quaternion reader -- no CircuitPython/Blinka
    dependency, consistent with this project's existing preference for
    direct register access (see arduino/subsystem_sim's LIS3DH driver)."""

    def __init__(self, bus_num: int = 1, addr: int = _BNO055_ADDR) -> None:
        self._addr = addr
        self._bus = SMBus(bus_num)

    def begin(self) -> bool:
        try:
            chip_id = self._bus.read_byte_data(self._addr, _BNO055_CHIP_ID_REG)
        except OSError as exc:
            logger.error("BNO055 not responding at 0x%02X: %s", self._addr, exc)
            return False
        if chip_id != _BNO055_CHIP_ID_EXPECTED:
            logger.error("BNO055 chip ID mismatch: got 0x%02X, expected 0x%02X",
                        chip_id, _BNO055_CHIP_ID_EXPECTED)
            return False
        self._bus.write_byte_data(self._addr, _BNO055_OPR_MODE_REG, _BNO055_OPR_MODE_CONFIG)
        time.sleep(0.02)
        self._bus.write_byte_data(self._addr, _BNO055_OPR_MODE_REG, _BNO055_OPR_MODE_NDOF)
        time.sleep(0.02)
        return True

    def read_quaternion(self) -> Quaternion:
        raw = self._bus.read_i2c_block_data(self._addr, _BNO055_QUATERNION_REG, 8)
        w, x, y, z = (
            int.from_bytes(bytes(raw[i:i + 2]), "little", signed=True) * _BNO055_QUATERNION_SCALE
            for i in (0, 2, 4, 6)
        )
        return Quaternion(w, x, y, z)


class WheelController:
    def __init__(self, wheel_port: str, i2c_bus: int = 1) -> None:
        self._wheel_serial = serial.Serial(wheel_port, 9600, timeout=1)
        self._bno = BNO055(bus_num=i2c_bus)
        self._pid = _PID(p=2.5, i=0.0, d=400.0)
        self._target_yaw = 0.0
        self._running = False

    def set_target(self, q: Quaternion) -> None:
        self._target_yaw = _quat_to_yaw(q)

    def start(self) -> bool:
        if not self._bno.begin():
            return False
        self._running = True
        return True

    def stop(self) -> None:
        self._running = False

    def run_forever(self) -> None:
        """Blocking outer-loop body -- run this in its own thread from main.py."""
        period_s = 1.0 / _OUTER_LOOP_HZ
        last_time = time.monotonic()
        while self._running:
            now = time.monotonic()
            dt = now - last_time
            if dt < period_s:
                time.sleep(period_s - dt)
                continue
            last_time = now

            try:
                current_yaw = _quat_to_yaw(self._bno.read_quaternion())
            except OSError as exc:
                logger.warning("BNO055 read failed: %s", exc)
                continue

            error = _wrap_pi(self._target_yaw - current_yaw)
            velocity_setpoint = self._pid.step(error, dt)

            cmd = f'{{"cmd":"vel","val":{velocity_setpoint:.3f}}}\n'
            self._wheel_serial.write(cmd.encode("ascii"))
