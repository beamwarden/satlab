from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sense_hat import SenseHat


class Health(Enum):
    OK = "ok"
    DEGRADED = "degraded"
    FAULT = "fault"


_COLORS: dict[Health, tuple[int, int, int]] = {
    Health.OK:       (0,   200, 0),
    Health.DEGRADED: (200, 100, 0),
    Health.FAULT:    (200, 0,   0),
}


class LedDisplay:
    def __init__(self, sense: SenseHat) -> None:
        self._sense = sense
        self._current: Health | None = None

    def set_health(self, health: Health) -> None:
        if health == self._current:
            return
        self._current = health
        self._sense.clear(*_COLORS[health])

    def off(self) -> None:
        self._sense.clear()
