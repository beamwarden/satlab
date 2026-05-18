from __future__ import annotations

import pytest
from datetime import datetime, timezone

from health import (
    NodeState,
    SubsystemHealth,
    SubsystemState,
    HealthVector,
    _WEIGHTS,
)
from thresholds import ViolationLevel, ThresholdViolation


# ── fixtures ──────────────────────────────────────────────────────────────────

def _soft(field: str = "temp_c", value: float = 10.0) -> ThresholdViolation:
    return ThresholdViolation(ViolationLevel.SOFT, field, value, "soft violation")


def _hard(field: str = "temp_c", value: float = 0.0) -> ThresholdViolation:
    return ThresholdViolation(ViolationLevel.HARD, field, value, "hard violation")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── SubsystemHealth.record() ──────────────────────────────────────────────────

class TestSubsystemHealthRecord:
    def test_initial_state_is_unknown(self):
        sh = SubsystemHealth(name="tcs")
        assert sh.state == SubsystemState.UNKNOWN

    def test_no_violations_is_nominal(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [])
        assert sh.state == SubsystemState.NOMINAL
        assert sh.active_faults == []

    def test_soft_violation_is_degraded(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_soft()])
        assert sh.state == SubsystemState.DEGRADED

    def test_hard_violation_is_critical(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_hard()])
        assert sh.state == SubsystemState.CRITICAL

    def test_mixed_worst_wins(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_soft(), _hard()])
        assert sh.state == SubsystemState.CRITICAL

    def test_multi_sensor_worst_wins(self):
        sh = SubsystemHealth(name="structural")
        sh.record("structural_sound", [_soft()])
        sh.record("structural_bmp280", [_hard()])
        assert sh.state == SubsystemState.CRITICAL

    def test_clearing_violations_returns_to_nominal(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_hard()])
        sh.record("tcs_dht", [])
        assert sh.state == SubsystemState.NOMINAL

    def test_active_faults_populated(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_soft()])
        assert len(sh.active_faults) == 1

    def test_active_faults_cleared_on_nominal(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_soft()])
        sh.record("tcs_dht", [])
        assert sh.active_faults == []

    def test_multi_sensor_faults_aggregate(self):
        sh = SubsystemHealth(name="structural")
        sh.record("structural_sound", [_soft("raw", 750.0)])
        sh.record("structural_bmp280", [_soft("pressure_hpa", 970.0)])
        assert len(sh.active_faults) == 2

    def test_second_sensor_clear_does_not_erase_first(self):
        sh = SubsystemHealth(name="structural")
        sh.record("structural_sound", [_hard()])
        sh.record("structural_bmp280", [])
        assert sh.state == SubsystemState.CRITICAL


# ── SubsystemHealth.apply_ae() ────────────────────────────────────────────────

class TestSubsystemHealthAe:
    def test_no_violations_decays_only(self):
        sh = SubsystemHealth(name="tcs")
        sh.ae_score = 1.0
        sh.apply_ae()
        assert abs(sh.ae_score - 0.85) < 1e-9

    def test_soft_violation_accumulates(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_soft()])
        sh.ae_score = 0.0
        sh.apply_ae()
        assert abs(sh.ae_score - 0.10) < 1e-9

    def test_hard_violation_accumulates_more(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_hard()])
        sh.ae_score = 0.0
        sh.apply_ae()
        assert abs(sh.ae_score - 0.40) < 1e-9

    def test_ae_score_capped_at_one(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_hard()])
        sh.ae_score = 0.95
        sh.apply_ae()
        assert sh.ae_score <= 1.0

    def test_repeated_decay_approaches_zero(self):
        sh = SubsystemHealth(name="tcs")
        sh.ae_score = 1.0
        for _ in range(100):
            sh.apply_ae()
        assert sh.ae_score < 0.01


# ── SubsystemHealth.to_dict() ─────────────────────────────────────────────────

class TestSubsystemHealthToDict:
    def test_structure(self):
        sh = SubsystemHealth(name="tcs")
        sh.record("tcs_dht", [_soft()])
        d = sh.to_dict()
        assert set(d.keys()) == {"state", "active_faults", "ae_score"}
        assert d["state"] == "DEGRADED"
        assert isinstance(d["active_faults"], list)
        assert isinstance(d["ae_score"], float)


# ── HealthVector ──────────────────────────────────────────────────────────────

class TestHealthVectorRefresh:
    def test_all_nominal_state(self):
        v = HealthVector()
        for name, sub in v.subsystems.items():
            sub.record(name, [])
        v.refresh()
        assert v.state == NodeState.NOMINAL

    def test_unknown_subsystems_cause_degraded(self):
        v = HealthVector()
        # No record() calls — all subsystems remain UNKNOWN
        v.refresh()
        assert v.state == NodeState.DEGRADED

    def test_one_degraded_causes_degraded_node(self):
        v = HealthVector()
        for name, sub in v.subsystems.items():
            sub.record(name, [])
        v.subsystems["tcs"].record("tcs_dht", [_soft()])
        v.refresh()
        assert v.state == NodeState.DEGRADED

    def test_one_critical_causes_critical_node(self):
        v = HealthVector()
        for name, sub in v.subsystems.items():
            sub.record(name, [])
        v.subsystems["adcs"].record("adcs_lis3dh", [_hard()])
        v.refresh()
        assert v.state == NodeState.CRITICAL

    def test_sequence_increments(self):
        v = HealthVector()
        assert v.sequence == 0
        v.refresh()
        assert v.sequence == 1
        v.refresh()
        assert v.sequence == 2

    def test_full_nominal_capability(self):
        v = HealthVector()
        for name, sub in v.subsystems.items():
            sub.record(name, [])
        v.refresh()
        assert v.mission_capability == 1.0

    def test_critical_adcs_reduces_capability(self):
        v = HealthVector()
        for name, sub in v.subsystems.items():
            sub.record(name, [])
        v.subsystems["adcs"].record("adcs_lis3dh", [_hard()])
        v.refresh()
        # adcs weight=0.30, contribution=0.0 when CRITICAL; rest=0.70 nominal
        expected = round(0.70 / sum(_WEIGHTS.values()), 4)
        assert v.mission_capability == expected

    def test_degraded_subsystem_half_weight(self):
        v = HealthVector()
        for name, sub in v.subsystems.items():
            sub.record(name, [])
        v.subsystems["eps"].record("eps_light", [_soft()])
        v.refresh()
        # eps weight=0.25 at 0.5 contribution; rest=0.75 at full
        expected = round((0.25 * 0.5 + 0.20 + 0.15 + 0.10 + 0.30) / sum(_WEIGHTS.values()), 4)
        assert v.mission_capability == expected

    def test_available_for_tasking_nominal(self):
        v = HealthVector()
        for name, sub in v.subsystems.items():
            sub.record(name, [])
        v.refresh()
        assert v.available_for_tasking is True

    def test_available_for_tasking_false_when_critical(self):
        v = HealthVector()
        for name, sub in v.subsystems.items():
            sub.record(name, [])
        v.subsystems["adcs"].record("adcs_lis3dh", [_hard()])
        v.subsystems["eps"].record("eps_light", [_hard()])
        v.subsystems["tcs"].record("tcs_dht", [_hard()])
        v.refresh()
        assert v.state == NodeState.CRITICAL
        assert v.available_for_tasking is False

    def test_available_for_tasking_false_at_low_capability(self):
        v = HealthVector()
        # Make adcs and eps CRITICAL so capability drops below 0.5
        for name, sub in v.subsystems.items():
            sub.record(name, [])
        v.subsystems["adcs"].record("adcs_lis3dh", [_hard()])
        v.subsystems["eps"].record("eps_light", [_hard()])
        v.refresh()
        # adcs(0.30) + eps(0.25) lost = 0.55 capability → remains CRITICAL
        assert v.available_for_tasking is False


# ── HealthVector.record_sensor() ─────────────────────────────────────────────

class TestHealthVectorRecordSensor:
    def test_known_subsystem_recorded(self):
        v = HealthVector()
        v.record_sensor("adcs_lis3dh", "adcs", [_soft()])
        assert v.subsystems["adcs"].state == SubsystemState.DEGRADED

    def test_unknown_subsystem_ignored(self):
        v = HealthVector()
        v.record_sensor("propulsion_xe", "propulsion", [_hard()])
        # No KeyError; no subsystems changed
        assert "propulsion" not in v.subsystems


# ── HealthVector.to_payload() ────────────────────────────────────────────────

class TestHealthVectorToPayload:
    def test_naive_datetime_raises(self):
        v = HealthVector()
        with pytest.raises(ValueError, match="UTC-aware"):
            v.to_payload(datetime(2026, 1, 1, 12, 0, 0))

    def test_aware_datetime_succeeds(self):
        v = HealthVector()
        v.refresh()
        payload = v.to_payload(_utc_now())
        assert isinstance(payload, dict)

    def test_payload_keys(self):
        v = HealthVector()
        v.refresh()
        payload = v.to_payload(_utc_now())
        expected_keys = {
            "node_id", "timestamp", "sequence", "state",
            "mission_capability", "available_for_tasking",
            "subsystems", "ae_summaries", "nis_summaries", "hmac_tag",
        }
        assert set(payload.keys()) == expected_keys

    def test_subsystems_contains_all_tracked(self):
        v = HealthVector()
        v.refresh()
        payload = v.to_payload(_utc_now())
        assert set(payload["subsystems"].keys()) == set(_WEIGHTS.keys())

    def test_state_serialized_as_string(self):
        v = HealthVector()
        v.refresh()
        payload = v.to_payload(_utc_now())
        assert payload["state"] == "DEGRADED"  # UNKNOWN subsystems → DEGRADED

    def test_mission_capability_is_float(self):
        v = HealthVector()
        v.refresh()
        payload = v.to_payload(_utc_now())
        assert isinstance(payload["mission_capability"], float)
