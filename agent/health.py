from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from thresholds import ViolationLevel, ThresholdViolation


class NodeState(str, Enum):
    NOMINAL   = "NOMINAL"
    DEGRADED  = "DEGRADED"
    CRITICAL  = "CRITICAL"
    SAFE_MODE = "SAFE_MODE"
    SILENT    = "SILENT"


class SubsystemState(str, Enum):
    NOMINAL  = "NOMINAL"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNKNOWN  = "UNKNOWN"


# Contribution of each subsystem to mission_capability.
_WEIGHTS: dict[str, float] = {
    "adcs":       0.30,
    "eps":        0.25,
    "tcs":        0.20,
    "structural": 0.15,
    "orbit":      0.10,
}

_AE_DECAY       = 0.85   # applied once per publish cycle
_AE_SOFT_WEIGHT = 0.10
_AE_HARD_WEIGHT = 0.40


@dataclass
class SubsystemHealth:
    name: str
    state: SubsystemState = SubsystemState.UNKNOWN
    active_faults: list[str] = field(default_factory=list)
    ae_score: float = 0.0

    def __post_init__(self) -> None:
        # Keyed by sensor_name so multi-sensor subsystems (e.g. structural)
        # accumulate faults from both sensors independently.
        self._per_sensor: dict[str, list[ThresholdViolation]] = {}

    def record(self, sensor_name: str, violations: list[ThresholdViolation]) -> None:
        """Store latest threshold results for one sensor; recompute subsystem state."""
        if violations:
            self._per_sensor[sensor_name] = violations
        else:
            self._per_sensor.pop(sensor_name, None)

        all_v = [v for vs in self._per_sensor.values() for v in vs]
        self.active_faults = [v.message for v in all_v]

        if not all_v:
            self.state = SubsystemState.NOMINAL
        else:
            worst = max(all_v, key=lambda v: v.level.value).level
            self.state = (SubsystemState.CRITICAL if worst == ViolationLevel.HARD
                          else SubsystemState.DEGRADED)

    def apply_ae(self) -> None:
        """Decay ae_score and accumulate from current violations. Call once per publish cycle."""
        self.ae_score *= _AE_DECAY
        all_v = [v for vs in self._per_sensor.values() for v in vs]
        if all_v:
            worst = max(all_v, key=lambda v: v.level.value).level
            w = _AE_HARD_WEIGHT if worst == ViolationLevel.HARD else _AE_SOFT_WEIGHT
            self.ae_score = min(1.0, self.ae_score + w)

    def to_dict(self) -> dict:
        return {
            "state":         self.state.value,
            "active_faults": self.active_faults,
            "ae_score":      round(self.ae_score, 4),
        }


def _make_node_id() -> str:
    return os.environ.get("SATLAB_NODE_ID") or str(uuid.uuid4())


@dataclass
class HealthVector:
    node_id: str = field(default_factory=_make_node_id)
    sequence: int = 0
    state: NodeState = NodeState.NOMINAL
    mission_capability: float = 1.0
    available_for_tasking: bool = True
    # nis_summaries populated by Tier 3 (not yet implemented)
    nis_summaries: dict[str, float] = field(default_factory=dict)
    # hmac_tag deferred — field present for schema completeness
    hmac_tag: str | None = None

    def __post_init__(self) -> None:
        self.subsystems: dict[str, SubsystemHealth] = {
            name: SubsystemHealth(name=name) for name in _WEIGHTS
        }

    def record_sensor(self, sensor_name: str, subsystem: str,
                      violations: list[ThresholdViolation]) -> None:
        if subsystem in self.subsystems:
            self.subsystems[subsystem].record(sensor_name, violations)

    def refresh(self) -> None:
        """Apply ae decay, derive top-level state and capability, increment sequence."""
        for sub in self.subsystems.values():
            sub.apply_ae()

        self.sequence += 1
        states = [s.state for s in self.subsystems.values()]

        if SubsystemState.CRITICAL in states:
            self.state = NodeState.CRITICAL
        elif SubsystemState.DEGRADED in states or SubsystemState.UNKNOWN in states:
            self.state = NodeState.DEGRADED
        else:
            self.state = NodeState.NOMINAL

        cap = sum(
            _WEIGHTS[name] * (
                1.0 if sub.state == SubsystemState.NOMINAL else
                0.5 if sub.state in (SubsystemState.DEGRADED, SubsystemState.UNKNOWN) else
                0.0
            )
            for name, sub in self.subsystems.items()
        )
        self.mission_capability = round(cap / sum(_WEIGHTS.values()), 4)
        self.available_for_tasking = (
            self.mission_capability > 0.5
            and self.state not in (NodeState.CRITICAL, NodeState.SAFE_MODE)
        )

    def to_payload(self, timestamp: datetime) -> dict:
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be UTC-aware; got a naive datetime")
        return {
            "node_id":               self.node_id,
            "timestamp":             timestamp.isoformat(),
            "sequence":              self.sequence,
            "state":                 self.state.value,
            "mission_capability":    self.mission_capability,
            "available_for_tasking": self.available_for_tasking,
            "subsystems":            {k: v.to_dict() for k, v in self.subsystems.items()},
            "ae_summaries":          {k: round(v.ae_score, 4) for k, v in self.subsystems.items()},
            "nis_summaries":         self.nis_summaries,
            "hmac_tag":              self.hmac_tag,
        }
