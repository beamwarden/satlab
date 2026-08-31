"""
Extract a hardware noise fingerprint from captured IMU data.

The fingerprint is the overlapping Allan deviation evaluated at a fixed set
of tau points for each of the 6 sensor channels (ax, ay, az, gx, gy, gz).
Because the ISM330DHCX units share the same model but differ in die, their
noise floors (ARW, bias instability) are measurably distinct.

Commissioning taus: [0.1, 0.3, 1.0, 3.0, 10.0, 30.0] s — requires ~120 s capture.
Verification taus:  [0.1, 0.3, 1.0, 3.0] s           — requires ~30 s capture.

Fingerprint hash: SHA-256 of the flattened ADEV vector (4-decimal scientific
notation), used to derive the SATLAB_HW_KEY for HealthVector HMAC tagging.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import numpy as np

from allan import oadev, eval_at

CHANNELS          = ["ax", "ay", "az", "gx", "gy", "gz"]
COMMISSION_TAUS   = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
VERIFY_TAUS       = [0.1, 0.3, 1.0, 3.0]


def _unit_fingerprint(data: dict[str, np.ndarray], taus: list[float]) -> dict:
    dt = float(np.mean(np.diff(data["t"])))

    results = {ch: oadev(data[ch], tau0=dt) for ch in CHANNELS}

    # Clamp taus to what the dataset can support
    t_max = results["ax"][0][-1]
    valid_taus = [t for t in taus if t <= t_max]

    fp: dict[str, list[float]] = {}
    for ch in CHANNELS:
        t_ch, a_ch = results[ch]
        fp[ch] = eval_at(t_ch, a_ch, valid_taus)

    return {
        "taus_s": valid_taus,
        "adev":   fp,
        "tau0_s": round(dt, 6),
        "n":      len(data["t"]),
    }


def _fp_vector(fp: dict) -> np.ndarray:
    vals: list[float] = []
    for ch in CHANNELS:
        vals.extend(fp["adev"][ch])
    return np.array(vals, dtype=np.float64)


def fingerprint_hash(fp: dict) -> str:
    vec     = _fp_vector(fp)
    payload = ",".join(f"{v:.4e}" for v in vec)
    return hashlib.sha256(payload.encode()).hexdigest()


def hw_key_from_fingerprints(fp0: dict, fp1: dict) -> bytes:
    """
    Derive a 32-byte HMAC key from both commissioned fingerprint hashes.
    Stored as SATLAB_HW_KEY (hex). If the hardware is substituted, the
    fingerprint changes, the derived key changes, and HMAC tags mismatch.
    """
    combined = (fingerprint_hash(fp0) + fingerprint_hash(fp1)).encode()
    return hashlib.sha256(combined).digest()


def cosine_distance(fp_a: dict, fp_b: dict) -> float:
    """Cosine distance in [0, 1]; 0 = identical noise profiles."""
    va = _fp_vector(fp_a)
    vb = _fp_vector(fp_b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 1.0
    return float(1.0 - np.dot(va, vb) / denom)


def mape(fp_baseline: dict, fp_new: dict) -> float:
    """Mean absolute percentage error between two fingerprints at matched taus."""
    va = _fp_vector(fp_baseline)
    vb = _fp_vector(fp_new)
    return float(np.mean(np.abs((vb - va) / (np.abs(va) + 1e-30))))


def trim_to_taus(fp: dict, taus: list[float]) -> dict:
    """
    Return a copy of fp containing only ADEV values at the requested taus.
    Uses nearest-match with 1% tolerance to avoid float-equality issues.
    """
    base = fp["taus_s"]
    idx: list[int] = []
    for t in taus:
        diffs = [abs(bt - t) / max(t, 1e-9) for bt in base]
        best  = min(range(len(diffs)), key=lambda i: diffs[i])
        if diffs[best] < 0.01:
            idx.append(best)
    return {
        "taus_s": [base[i] for i in idx],
        "adev":   {ch: [fp["adev"][ch][i] for i in idx] for ch in fp["adev"]},
    }


def build_commission_record(npz_path: str) -> dict:
    """
    Load a capture .npz and return the full commissioning record.

    The hw_key_hex field is NOT written to the Beamwarden fingerprint.json;
    it is kept local and loaded into the agent via SATLAB_HW_KEY env var.
    """
    data = np.load(npz_path)

    def _unit_data(prefix: str) -> dict[str, np.ndarray]:
        return {k: data[f"{prefix}_{k}"] for k in ["t", "ax", "ay", "az", "gx", "gy", "gz"]}

    d0, d1 = _unit_data("u0"), _unit_data("u1")
    fp0    = _unit_fingerprint(d0, COMMISSION_TAUS)
    fp1    = _unit_fingerprint(d1, COMMISSION_TAUS)
    h0     = fingerprint_hash(fp0)
    h1     = fingerprint_hash(fp1)
    dist   = cosine_distance(fp0, fp1)
    key    = hw_key_from_fingerprints(fp0, fp1)

    return {
        "schema":                   1,
        "commissioned_at":          datetime.now(timezone.utc).isoformat(),
        "units": {
            "ism330dhcx_0": {"i2c_addr": "0x6A", "fingerprint": fp0, "hash": h0},
            "ism330dhcx_1": {"i2c_addr": "0x6B", "fingerprint": fp1, "hash": h1},
        },
        "distinguishability_cosine": round(dist, 6),
        "hw_key_hex":                key.hex(),
    }
