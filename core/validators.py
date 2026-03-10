"""Validation utilities for click settings and runtime preconditions."""

from __future__ import annotations

import ctypes

from config import COUNT_MAX, COUNT_MIN, INTERVAL_MAX_MS, INTERVAL_MIN_MS
from core.models import AppState, ClickConfig, ClickMode, ScreenBounds

user32 = ctypes.WinDLL("user32", use_last_error=True)

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int


def get_virtual_screen_bounds() -> ScreenBounds:
    """Returns virtual desktop bounds for multi-monitor coordinate validation."""
    left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))

    if width <= 0 or height <= 0:
        left = 0
        top = 0
        width = int(user32.GetSystemMetrics(SM_CXSCREEN))
        height = int(user32.GetSystemMetrics(SM_CYSCREEN))

    return ScreenBounds(left=left, top=top, width=width, height=height)


def validate_config(
    config: ClickConfig,
    screen_bounds: ScreenBounds,
    current_state: AppState,
) -> list[str]:
    """Validates click configuration and startup preconditions."""
    errors: list[str] = []

    if current_state not in (AppState.IDLE, AppState.STOPPED):
        errors.append(
            "Запуск недоступен: кликер уже выполняется или находится в промежуточном состоянии."
        )

    if not (INTERVAL_MIN_MS <= config.interval_ms <= INTERVAL_MAX_MS):
        errors.append(
            f"Интервал должен быть в диапазоне от {INTERVAL_MIN_MS} до {INTERVAL_MAX_MS} мс."
        )

    if config.click_limit is not None and not (COUNT_MIN <= config.click_limit <= COUNT_MAX):
        errors.append(
            f"Количество кликов должно быть в диапазоне от {COUNT_MIN} до {COUNT_MAX}."
        )

    if config.mode is ClickMode.SAVED_POINT:
        if config.target_x is None or config.target_y is None:
            errors.append("Для режима клика по сохраненной точке нужно указать координаты X и Y.")
        elif not screen_bounds.contains(config.target_x, config.target_y):
            errors.append(
                "Координаты вне виртуального экрана: "
                f"X={config.target_x}, Y={config.target_y}. "
                f"Допустимый диапазон: X {screen_bounds.left}..{screen_bounds.right}, "
                f"Y {screen_bounds.top}..{screen_bounds.bottom}."
            )

    return errors
