from __future__ import annotations

import math
import pytest

from thresholds import ViolationLevel, ThresholdViolation, evaluate


# ── helpers ───────────────────────────────────────────────────────────────────

def _levels(violations: list[ThresholdViolation]) -> list[ViolationLevel]:
    return [v.level for v in violations]


def _fields(violations: list[ThresholdViolation]) -> list[str]:
    return [v.field for v in violations]


# ── evaluate() dispatch ───────────────────────────────────────────────────────

class TestEvaluateDispatch:
    def test_unknown_sensor_returns_empty(self):
        assert evaluate("propulsion_xenon", {"flow": 1.0}) == []

    def test_known_sensor_dispatches(self):
        result = evaluate("orbit_sgp4", {"error_code": 1})
        assert len(result) == 1
        assert result[0].level == ViolationLevel.HARD


# ── eps_light ─────────────────────────────────────────────────────────────────

class TestEpsLight:
    def test_nominal(self):
        assert evaluate("eps_light", {"pct": 50}) == []

    def test_missing_pct(self):
        assert evaluate("eps_light", {}) == []

    def test_low_illumination(self):
        v = evaluate("eps_light", {"pct": 3})
        assert _levels(v) == [ViolationLevel.SOFT]
        assert _fields(v) == ["pct"]

    def test_saturated(self):
        v = evaluate("eps_light", {"pct": 95})
        assert _levels(v) == [ViolationLevel.SOFT]

    def test_boundary_at_5_is_nominal(self):
        assert evaluate("eps_light", {"pct": 5}) == []

    def test_boundary_at_90_is_nominal(self):
        assert evaluate("eps_light", {"pct": 90}) == []


# ── structural_sound ──────────────────────────────────────────────────────────

class TestStructuralSound:
    def test_nominal(self):
        assert evaluate("structural_sound", {"raw": 500}) == []

    def test_missing_raw(self):
        assert evaluate("structural_sound", {}) == []

    def test_soft_vibration(self):
        v = evaluate("structural_sound", {"raw": 750})
        assert _levels(v) == [ViolationLevel.SOFT]
        assert _fields(v) == ["raw"]

    def test_hard_shock(self):
        v = evaluate("structural_sound", {"raw": 960})
        assert _levels(v) == [ViolationLevel.HARD]

    def test_boundary_700_is_nominal(self):
        assert evaluate("structural_sound", {"raw": 700}) == []

    def test_boundary_950_is_soft(self):
        v = evaluate("structural_sound", {"raw": 951})
        assert _levels(v) == [ViolationLevel.HARD]


# ── tcs_dht ───────────────────────────────────────────────────────────────────

class TestTcsDht:
    def test_nominal(self):
        assert evaluate("tcs_dht", {"temp_c": 25.0, "humidity_pct": 50.0}) == []

    def test_temp_critically_low(self):
        v = evaluate("tcs_dht", {"temp_c": 3.0, "humidity_pct": 50.0})
        temp_v = [x for x in v if x.field == "temp_c"]
        assert temp_v[0].level == ViolationLevel.HARD

    def test_temp_critically_high(self):
        v = evaluate("tcs_dht", {"temp_c": 50.0, "humidity_pct": 50.0})
        temp_v = [x for x in v if x.field == "temp_c"]
        assert temp_v[0].level == ViolationLevel.HARD

    def test_temp_soft_low(self):
        v = evaluate("tcs_dht", {"temp_c": 10.0, "humidity_pct": 50.0})
        temp_v = [x for x in v if x.field == "temp_c"]
        assert temp_v[0].level == ViolationLevel.SOFT

    def test_temp_soft_high(self):
        v = evaluate("tcs_dht", {"temp_c": 40.0, "humidity_pct": 50.0})
        temp_v = [x for x in v if x.field == "temp_c"]
        assert temp_v[0].level == ViolationLevel.SOFT

    def test_humidity_critically_high(self):
        v = evaluate("tcs_dht", {"temp_c": 25.0, "humidity_pct": 95.0})
        hum_v = [x for x in v if x.field == "humidity_pct"]
        assert hum_v[0].level == ViolationLevel.HARD

    def test_humidity_soft_high(self):
        v = evaluate("tcs_dht", {"temp_c": 25.0, "humidity_pct": 80.0})
        hum_v = [x for x in v if x.field == "humidity_pct"]
        assert hum_v[0].level == ViolationLevel.SOFT

    def test_humidity_soft_low(self):
        v = evaluate("tcs_dht", {"temp_c": 25.0, "humidity_pct": 15.0})
        hum_v = [x for x in v if x.field == "humidity_pct"]
        assert hum_v[0].level == ViolationLevel.SOFT

    def test_multiple_violations(self):
        v = evaluate("tcs_dht", {"temp_c": 50.0, "humidity_pct": 95.0})
        assert len(v) == 2
        fields = _fields(v)
        assert "temp_c" in fields
        assert "humidity_pct" in fields

    def test_missing_temp_only_checks_humidity(self):
        v = evaluate("tcs_dht", {"humidity_pct": 95.0})
        assert len(v) == 1
        assert v[0].field == "humidity_pct"


# ── structural_bmp280 ─────────────────────────────────────────────────────────

class TestStructuralBmp280:
    def test_nominal(self):
        assert evaluate("structural_bmp280", {"temp_c": 25.0, "pressure_hpa": 1013.0}) == []

    def test_pressure_critically_low(self):
        v = evaluate("structural_bmp280", {"pressure_hpa": 950.0})
        pres_v = [x for x in v if x.field == "pressure_hpa"]
        assert pres_v[0].level == ViolationLevel.HARD

    def test_pressure_critically_high(self):
        v = evaluate("structural_bmp280", {"pressure_hpa": 1060.0})
        pres_v = [x for x in v if x.field == "pressure_hpa"]
        assert pres_v[0].level == ViolationLevel.HARD

    def test_pressure_soft_low(self):
        v = evaluate("structural_bmp280", {"pressure_hpa": 975.0})
        pres_v = [x for x in v if x.field == "pressure_hpa"]
        assert pres_v[0].level == ViolationLevel.SOFT

    def test_pressure_soft_high(self):
        v = evaluate("structural_bmp280", {"pressure_hpa": 1040.0})
        pres_v = [x for x in v if x.field == "pressure_hpa"]
        assert pres_v[0].level == ViolationLevel.SOFT

    def test_temp_and_pressure_violations(self):
        v = evaluate("structural_bmp280", {"temp_c": 50.0, "pressure_hpa": 950.0})
        assert len(v) == 2

    def test_missing_pressure(self):
        assert evaluate("structural_bmp280", {"temp_c": 25.0}) == []


# ── adcs_lis3dh ───────────────────────────────────────────────────────────────

class TestAdcsLis3dh:
    def test_nominal_unit_vector(self):
        assert evaluate("adcs_lis3dh", {"ax_g": 0.0, "ay_g": 0.0, "az_g": 1.0}) == []

    def test_missing_axis(self):
        assert evaluate("adcs_lis3dh", {"ax_g": 0.0, "ay_g": 0.0}) == []
        assert evaluate("adcs_lis3dh", {}) == []

    def test_soft_vibration(self):
        # |g| = sqrt(2) ≈ 1.414 → dev = 0.414, between 0.20 and 0.50
        v = evaluate("adcs_lis3dh", {"ax_g": 1.0, "ay_g": 1.0, "az_g": 0.0})
        assert _levels(v) == [ViolationLevel.SOFT]
        assert _fields(v) == ["magnitude"]

    def test_hard_shock(self):
        # |g| = sqrt(3) ≈ 1.732 → dev = 0.732 > 0.50
        v = evaluate("adcs_lis3dh", {"ax_g": 1.0, "ay_g": 1.0, "az_g": 1.0})
        assert _levels(v) == [ViolationLevel.HARD]

    def test_nearly_zero_g_is_hard(self):
        v = evaluate("adcs_lis3dh", {"ax_g": 0.0, "ay_g": 0.0, "az_g": 0.0})
        assert _levels(v) == [ViolationLevel.HARD]

    def test_violation_message_contains_magnitude(self):
        v = evaluate("adcs_lis3dh", {"ax_g": 0.0, "ay_g": 0.0, "az_g": 2.0})
        assert "|g|=" in v[0].message

    def test_value_is_magnitude(self):
        v = evaluate("adcs_lis3dh", {"ax_g": 0.0, "ay_g": 0.0, "az_g": 2.0})
        assert abs(v[0].value - 2.0) < 1e-6


# ── orbit_sgp4 ────────────────────────────────────────────────────────────────

class TestOrbitSgp4:
    def test_nominal_error_code_zero(self):
        assert evaluate("orbit_sgp4", {"error_code": 0}) == []

    def test_missing_error_code(self):
        assert evaluate("orbit_sgp4", {}) == []

    def test_propagation_fault(self):
        v = evaluate("orbit_sgp4", {"error_code": 2})
        assert _levels(v) == [ViolationLevel.HARD]
        assert _fields(v) == ["error_code"]
        assert v[0].value == 2.0
        assert "code=2" in v[0].message
