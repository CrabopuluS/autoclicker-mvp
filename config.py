"""Application-wide constants for the AutoClicker MVP."""

from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "AutoClicker MVP"
APP_VERSION = "1.0.0"
APP_MUTEX_NAME = "Global\\AutoClickerMVP_SingleInstanceMutex"
APP_ORG = "AutoClicker Team"
APP_REPO_URL = "https://github.com/CrabopuluS/autoclicker-mvp.git"

INTERVAL_MIN_MS = 0
INTERVAL_MAX_MS = 3_600_000
COUNT_MIN = 1
COUNT_MAX = 10_000_000
LOG_MAX_LINES = 1_000
HIGH_RES_TIMER_PERIOD_MS = 1

HOTKEY_ACTION_START = "start"
HOTKEY_ACTION_STOP = "stop"
HOTKEY_ACTION_PAUSE_RESUME = "pause_resume"
HOTKEY_ACTION_CAPTURE = "capture"

HOTKEY_ID_START = 1
HOTKEY_ID_STOP = 2
HOTKEY_ID_PAUSE_RESUME = 3
HOTKEY_ID_CAPTURE = 4

MOD_NOREPEAT = 0x4000

VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78


@dataclass(frozen=True, slots=True)
class HotkeyBinding:
    """Represents a global hotkey registration."""

    hotkey_id: int
    action: str
    vk_code: int
    display: str


HOTKEY_BINDINGS = (
    HotkeyBinding(HOTKEY_ID_START, HOTKEY_ACTION_START, VK_F6, "F6"),
    HotkeyBinding(HOTKEY_ID_STOP, HOTKEY_ACTION_STOP, VK_F7, "F7"),
    HotkeyBinding(HOTKEY_ID_PAUSE_RESUME, HOTKEY_ACTION_PAUSE_RESUME, VK_F8, "F8"),
    HotkeyBinding(HOTKEY_ID_CAPTURE, HOTKEY_ACTION_CAPTURE, VK_F9, "F9"),
)
