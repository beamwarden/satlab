"""
Capture high-rate raw IMU data from two ISM330DHCX units on the RPi I2C bus.

Unit 0: address 0x6A (SA0 pin low)
Unit 1: address 0x6B (SA0 pin high)

Reads are interleaved in a tight loop with STATUS_REG polling so no sample
is dropped. Actual achieved sample rate is measured and stored in the output.
Both units share the same I2C bus (half-duplex); the ~3 ms round-trip for
two reads fits comfortably within the 9.6 ms ODR interval at 104 Hz.

Usage:
    python capture.py [--bus 1] [--duration 120] [--output capture.npz]

Output: NumPy .npz with arrays prefixed u0_ and u1_ for each unit:
    t   — monotonic time in seconds from start of capture
    ax, ay, az — accelerometer (g)
    gx, gy, gz — gyroscope (dps)
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from ism330dhcx import ISM330DHCX


def capture(
    bus: int = 1,
    duration_s: float = 120.0,
    output: str = "capture.npz",
) -> str:
    imu0 = ISM330DHCX(bus=bus, addr=0x6A)
    imu1 = ISM330DHCX(bus=bus, addr=0x6B)

    buf0: list[tuple] = []
    buf1: list[tuple] = []

    t_start = time.monotonic()
    t_end   = t_start + duration_s
    last_progress = t_start

    print(f"Capturing {duration_s:.0f}s from 0x6A and 0x6B on i2c-{bus} ...")

    while True:
        mono = time.monotonic()
        if mono >= t_end:
            break

        t  = mono - t_start
        r0 = imu0.read_raw()
        r1 = imu1.read_raw()

        if r0:
            buf0.append((t, *r0))
        if r1:
            buf1.append((t, *r1))

        if not r0 and not r1:
            time.sleep(0.001)  # no new data on either unit; yield briefly

        if mono - last_progress >= 10.0:
            pct = (mono - t_start) / duration_s * 100
            print(f"  {pct:.0f}%  samples: u0={len(buf0)}  u1={len(buf1)}")
            last_progress = mono

    imu0.close()
    imu1.close()

    def _to_dict(buf: list[tuple]) -> dict[str, np.ndarray]:
        a = np.array(buf, dtype=np.float64)
        return {
            "t":  a[:, 0],
            "ax": a[:, 1], "ay": a[:, 2], "az": a[:, 3],
            "gx": a[:, 4], "gy": a[:, 5], "gz": a[:, 6],
        }

    d0 = _to_dict(buf0)
    d1 = _to_dict(buf1)

    dt0 = float(np.mean(np.diff(d0["t"])))
    dt1 = float(np.mean(np.diff(d1["t"])))

    np.savez(
        output,
        **{f"u0_{k}": v for k, v in d0.items()},
        **{f"u1_{k}": v for k, v in d1.items()},
    )

    print(
        f"Done. "
        f"u0: {len(buf0)} samples @ {1/dt0:.1f} Hz  |  "
        f"u1: {len(buf1)} samples @ {1/dt1:.1f} Hz"
    )
    print(f"Saved: {output}")
    return output


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bus",      type=int,   default=1,          help="I2C bus number")
    ap.add_argument("--duration", type=float, default=120.0,      help="Capture duration in seconds")
    ap.add_argument("--output",   default="capture.npz",          help="Output .npz path")
    args = ap.parse_args()
    capture(bus=args.bus, duration_s=args.duration, output=args.output)


if __name__ == "__main__":
    main()
