"""
Full commissioning run for two ISM330DHCX units.

Steps:
  1. Capture 120 s of high-rate IMU data from both units.
  2. Compute overlapping Allan deviation per channel.
  3. Build noise fingerprints and derive a hardware HMAC key.
  4. Save fingerprint.json (for Beamwarden) and capture.npz (raw data).
  5. Print SATLAB_HW_KEY for the operator to add to the agent .env.

Usage (on the RPi, from satlab/commissioning/):
    pip install -r requirements.txt
    python commission.py [--bus 1] [--duration 120] [--out commissioning_output]

After commissioning:
  - On the beamwarden host:
      python manage.py set_hw_signature <serial_number> <out>/fingerprint.json
  - On beamrider-0003, add to .env:
      SATLAB_HW_KEY=<printed hex>
"""
from __future__ import annotations

import argparse
import json
import os

from capture import capture
from fingerprint import build_commission_record


def run(bus: int, duration_s: float, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    npz_path = os.path.join(out_dir, "capture.npz")
    fp_path  = os.path.join(out_dir, "fingerprint.json")

    capture(bus=bus, duration_s=duration_s, output=npz_path)

    print("\nComputing fingerprints ...")
    record = build_commission_record(npz_path)

    # fingerprint.json is safe to send to Beamwarden — hw_key_hex stays local
    beamwarden_record = {k: v for k, v in record.items() if k != "hw_key_hex"}
    with open(fp_path, "w") as f:
        json.dump(beamwarden_record, f, indent=2)

    u0 = record["units"]["ism330dhcx_0"]
    u1 = record["units"]["ism330dhcx_1"]
    dist = record["distinguishability_cosine"]
    distinguishable = dist > 0.005

    print(f"\nUnit 0 (0x6A)  hash: {u0['hash'][:24]}...")
    print(f"Unit 1 (0x6B)  hash: {u1['hash'][:24]}...")
    print(
        f"Cosine distance:     {dist:.6f}  "
        f"{'DISTINGUISHABLE' if distinguishable else 'WARNING: units may be indistinct — re-run or check wiring'}"
    )
    print(f"\nFingerprint saved:   {fp_path}")
    print(f"Raw capture saved:   {npz_path}")

    print("\n" + "─" * 64)
    print("Add to .env on beamrider-0003 before starting the agent:")
    print(f"  SATLAB_HW_KEY={record['hw_key_hex']}")
    print("─" * 64)
    print("\nTo register with Beamwarden (on the beamwarden host):")
    print(f"  python manage.py set_hw_signature <serial_number> {fp_path}")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Commission ISM330DHCX hardware signature.")
    ap.add_argument("--bus",      type=int,   default=1,
                    help="I2C bus number (default 1 for RPi GPIO header)")
    ap.add_argument("--duration", type=float, default=120.0,
                    help="Capture duration in seconds (min 120 for full tau range)")
    ap.add_argument("--out",      default="commissioning_output",
                    help="Output directory for fingerprint.json and capture.npz")
    args = ap.parse_args()
    run(bus=args.bus, duration_s=args.duration, out_dir=args.out)


if __name__ == "__main__":
    main()
