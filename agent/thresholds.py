from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ViolationLevel(Enum):
    NONE = 0
    SOFT = 1
    HARD = 2


@dataclass(frozen=True)
class ThresholdViolation:
    level: ViolationLevel
    field: str
    value: float
    message: str


def evaluate(sensor_name: str, payload: dict[str, Any]) -> list[ThresholdViolation]:
    """Run Tier 1 threshold checks for a sensor reading. Empty list = nominal."""
    fn = _EVALUATORS.get(sensor_name)
    return fn(payload) if fn else []


# ── per-sensor evaluators ─────────────────────────────────────────────────────

def _temp_violations(label: str, temp: float | None) -> list[ThresholdViolation]:
    if temp is None:
        return []
    if temp < 5.0:
        return [ThresholdViolation(ViolationLevel.HARD, "temp_c", temp,
                                   f"{label} temp critically low ({temp}°C)")]
    if temp > 45.0:
        return [ThresholdViolation(ViolationLevel.HARD, "temp_c", temp,
                                   f"{label} temp critically high ({temp}°C)")]
    if temp < 15.0:
        return [ThresholdViolation(ViolationLevel.SOFT, "temp_c", temp,
                                   f"{label} temp low ({temp}°C)")]
    if temp > 35.0:
        return [ThresholdViolation(ViolationLevel.SOFT, "temp_c", temp,
                                   f"{label} temp high ({temp}°C)")]
    return []


def _eps_light(p: dict) -> list[ThresholdViolation]:
    pct = p.get("pct")
    if pct is None:
        return []
    if pct < 5:
        return [ThresholdViolation(ViolationLevel.SOFT, "pct", pct,
                                   f"eps illumination low ({pct}%)")]
    if pct > 90:
        return [ThresholdViolation(ViolationLevel.SOFT, "pct", pct,
                                   f"eps illumination saturated ({pct}%)")]
    return []


def _structural_sound(p: dict) -> list[ThresholdViolation]:
    raw = p.get("raw")
    if raw is None:
        return []
    if raw > 950:
        return [ThresholdViolation(ViolationLevel.HARD, "raw", raw,
                                   f"structural vibration severe (raw={raw})")]
    if raw > 700:
        return [ThresholdViolation(ViolationLevel.SOFT, "raw", raw,
                                   f"structural vibration event (raw={raw})")]
    return []


def _tcs_dht(p: dict) -> list[ThresholdViolation]:
    v = _temp_violations("tcs", p.get("temp_c"))
    hum = p.get("humidity_pct")
    if hum is not None:
        if hum > 90.0:
            v.append(ThresholdViolation(ViolationLevel.HARD, "humidity_pct", hum,
                                        f"tcs humidity critically high ({hum}%)"))
        elif hum > 75.0:
            v.append(ThresholdViolation(ViolationLevel.SOFT, "humidity_pct", hum,
                                        f"tcs humidity high ({hum}%)"))
        elif hum < 20.0:
            v.append(ThresholdViolation(ViolationLevel.SOFT, "humidity_pct", hum,
                                        f"tcs humidity low ({hum}%)"))
    return v


def _structural_bmp280(p: dict) -> list[ThresholdViolation]:
    v = _temp_violations("structural", p.get("temp_c"))
    hpa = p.get("pressure_hpa")
    if hpa is not None:
        if hpa < 960.0:
            v.append(ThresholdViolation(ViolationLevel.HARD, "pressure_hpa", hpa,
                                        f"structural pressure critically low ({hpa} hPa)"))
        elif hpa > 1050.0:
            v.append(ThresholdViolation(ViolationLevel.HARD, "pressure_hpa", hpa,
                                        f"structural pressure critically high ({hpa} hPa)"))
        elif hpa < 990.0:
            v.append(ThresholdViolation(ViolationLevel.SOFT, "pressure_hpa", hpa,
                                        f"structural pressure low ({hpa} hPa)"))
        elif hpa > 1030.0:
            v.append(ThresholdViolation(ViolationLevel.SOFT, "pressure_hpa", hpa,
                                        f"structural pressure high ({hpa} hPa)"))
    return v


def _adcs_lis3dh(p: dict) -> list[ThresholdViolation]:
    ax, ay, az = p.get("ax_g"), p.get("ay_g"), p.get("az_g")
    if ax is None or ay is None or az is None:
        return []
    mag = math.sqrt(ax**2 + ay**2 + az**2)
    dev = abs(mag - 1.0)
    if dev > 0.50:
        return [ThresholdViolation(ViolationLevel.HARD, "magnitude", mag,
                                   f"adcs shock event (|g|={mag:.3f})")]
    if dev > 0.20:
        return [ThresholdViolation(ViolationLevel.SOFT, "magnitude", mag,
                                   f"adcs vibration (|g|={mag:.3f})")]
    return []


def _orbit_sgp4(p: dict) -> list[ThresholdViolation]:
    err = p.get("error_code")
    if err is not None and err != 0:
        return [ThresholdViolation(ViolationLevel.HARD, "error_code", float(err),
                                   f"orbit propagation fault (code={err})")]
    return []


_EVALUATORS: dict[str, Any] = {
    "eps_light":         _eps_light,
    "structural_sound":  _structural_sound,
    "tcs_dht":           _tcs_dht,
    "structural_bmp280": _structural_bmp280,
    "adcs_lis3dh":       _adcs_lis3dh,
    "orbit_sgp4":        _orbit_sgp4,
}
