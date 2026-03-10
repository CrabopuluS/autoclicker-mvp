"""Domain models and state transitions for the AutoClicker."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AppState(Enum):
    """Runtime state of the application clicker engine."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class ClickMode(Enum):
    """How click coordinates are resolved."""

    SAVED_POINT = "SAVED_POINT"
    CURRENT_POSITION = "CURRENT_POSITION"


class MouseButton(Enum):
    """Mouse buttons supported by the clicker."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    MIDDLE = "MIDDLE"


@dataclass(slots=True)
class ClickConfig:
    """Validated click settings used by the click worker."""

    mode: ClickMode
    button: MouseButton
    interval_ms: int
    click_limit: int | None
    target_x: int | None
    target_y: int | None


@dataclass(frozen=True, slots=True)
class ScreenBounds:
    """Represents virtual desktop bounds in physical screen coordinates."""

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        """Inclusive right edge."""
        return self.left + self.width - 1

    @property
    def bottom(self) -> int:
        """Inclusive bottom edge."""
        return self.top + self.height - 1

    def contains(self, x: int, y: int) -> bool:
        """Returns True if the point is inside virtual desktop bounds."""
        return self.left <= x <= self.right and self.top <= y <= self.bottom


_ALLOWED_TRANSITIONS: dict[AppState, frozenset[AppState]] = {
    AppState.IDLE: frozenset({AppState.RUNNING, AppState.STOPPED}),
    AppState.RUNNING: frozenset({AppState.PAUSED, AppState.STOPPED}),
    AppState.PAUSED: frozenset({AppState.RUNNING, AppState.STOPPED}),
    AppState.STOPPED: frozenset({AppState.RUNNING, AppState.IDLE}),
}


def can_transition(current: AppState, target: AppState) -> bool:
    """Checks whether a state transition is valid for the finite-state model."""
    if current == target:
        return True
    return target in _ALLOWED_TRANSITIONS.get(current, frozenset())
