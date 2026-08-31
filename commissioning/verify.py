"""
Re-measure both ISM330DHCX units and compare to the commissioned fingerprint.

A short 30-second capture is sufficient to evaluate ADEV at the verification
tau points [0.1, 0.3, 1.0, 3.0] s. MAPE above the threshold flags the unit
as anomalous — indicating hardware degradation or substitution.

Usage:
    python verify.py --baseline commissioning_output/fingerprint.json \\
                     [--bus 1] [--duration 30]

Exit code: 0 = both units pass, 1 = one or both fail.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

import numpy as np

from capture import capture
from fingerprint import _unit_fingerprint, mape, trim_to_taus, VERIFY_TAUS

_MAPE_THRESHOLD = 0.15  # 15% mean absolute deviation from baseline


def _unit_data(npz: np.lib.npyio.NpzFile, prefix: str) -> dict[str, np.ndarray]:
    return {k: npz[f"{prefix}_{k}"] for k in ["t", "ax", "ay", "az", "gx", "gy", "gz"]}


def verify(baseline_path: str, bus: int = 1, duration_s: float = 30.0) -> bool:
    with open(baseline_path) as f:
        baseline = json.load(f)

    with tempfile.TemporaryDirectory() as td:
        npz_path = os.path.join(td, "verify.npz")
        capture(bus=bus, duration_s=duration_s, output=npz_path)
        npz = np.load(npz_path)
        d0  = _unit_data(npz, "u0")
        d1  = _unit_data(npz, "u1")

    fp0_new = _unit_fingerprint(d0, VERIFY_TAUS)
    fp1_new = _unit_fingerprint(d1, VERIFY_TAUS)

    # Trim the baseline fingerprints to the verification tau set
    bl0 = trim_to_taus(baseline["units"]["ism330dhcx_0"]["fingerprint"], VERIFY_TAUS)
    bl1 = trim_to_taus(baseline["units"]["ism330dhcx_1"]["fingerprint"], VERIFY_TAUS)

    e0, e1 = mape(bl0, fp0_new), mape(bl1, fp1_new)
    ok0, ok1 = e0 < _MAPE_THRESHOLD, e1 < _MAPE_THRESHOLD

    commissioned_at = baseline.get("commissioned_at", "unknown")
    print(f"Baseline commissioned: {commissioned_at}")
    print(f"Threshold: {_MAPE_THRESHOLD:.0%}")
    print()
    print(f"  Unit 0 (0x6A)  MAPE={e0:.2%}  {'PASS' if ok0 else 'FAIL'}")
    print(f"  Unit 1 (0x6B)  MAPE={e1:.2%}  {'PASS' if ok1 else 'FAIL'}")
    print()

    if ok0 and ok1:
        print("Result: PASS — hardware signatures match baseline.")
    else:
        failed = [u for u, ok in [("0x6A", ok0), ("0x6B", ok1)] if not ok]
        print(f"Result: FAIL — unit(s) {failed} deviate beyond threshold.")
        print("Possible causes: hardware substitution, sensor degradation, thermal drift.")

    return ok0 and ok1


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify ISM330DHCX hardware signatures.")
    ap.add_argument("--baseline", required=True,
                    help="Path to fingerprint.json from commission.py")
    ap.add_argument("--bus",      type=int,   default=1)
    ap.add_argument("--duration", type=float, default=30.0,
                    help="Capture duration in seconds (min 30 for full verify tau range)")
    args = ap.parse_args()
    ok = verify(args.baseline, bus=args.bus, duration_s=args.duration)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
