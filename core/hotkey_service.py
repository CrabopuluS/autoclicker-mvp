"""Global hotkey registration and dispatch via WinAPI WM_HOTKEY."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QObject, Signal
from PySide6.QtWidgets import QApplication

from config import (
    HOTKEY_ACTION_CAPTURE,
    HOTKEY_ACTION_PAUSE_RESUME,
    HOTKEY_ACTION_START,
    HOTKEY_ACTION_STOP,
    HOTKEY_BINDINGS,
    MOD_NOREPEAT,
)

user32 = ctypes.WinDLL("user32", use_last_error=True)

WM_HOTKEY = 0x0312

WPARAM = wintypes.WPARAM if hasattr(wintypes, "WPARAM") else ctypes.c_size_t
LPARAM = wintypes.LPARAM if hasattr(wintypes, "LPARAM") else ctypes.c_ssize_t


class POINT(ctypes.Structure):
    """WinAPI POINT structure."""

    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    """WinAPI MSG structure."""

    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", WPARAM),
        ("lParam", LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL


class _NativeHotkeyFilter(QAbstractNativeEventFilter):
    """Qt native event filter that listens for WM_HOTKEY messages."""

    def __init__(self, callback) -> None:
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type, message):  # type: ignore[override]
        """Dispatches hotkey ID from native MSG structure."""
        event_name = _normalize_event_type(event_type)
        if event_name not in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            return False, 0

        try:
            message_ptr = _extract_native_pointer(message)
            if message_ptr is None:
                return False, 0

            msg = ctypes.cast(message_ptr, ctypes.POINTER(MSG)).contents
            if msg.message == WM_HOTKEY:
                self._callback(int(msg.wParam))
                return False, 0
        except Exception:  # noqa: BLE001
            return False, 0

        return False, 0


class HotkeyService(QObject):
    """Registers global hotkeys and exposes action signals."""

    start_requested = Signal()
    stop_requested = Signal()
    pause_resume_requested = Signal()
    capture_requested = Signal()
    error = Signal(str)

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self._registered_ids: set[int] = set()
        self._event_filter = _NativeHotkeyFilter(self._dispatch_hotkey)
        self._filter_installed = False

    def register_default_hotkeys(self) -> bool:
        """Registers fixed F6/F7/F8/F9 global hotkeys."""
        if not self._filter_installed:
            self._app.installNativeEventFilter(self._event_filter)
            self._filter_installed = True

        for binding in HOTKEY_BINDINGS:
            if binding.hotkey_id in self._registered_ids:
                continue

            registered = bool(
                user32.RegisterHotKey(None, binding.hotkey_id, MOD_NOREPEAT, binding.vk_code)
            )
            if not registered:
                # Some environments reject MOD_NOREPEAT without modifiers.
                registered = bool(user32.RegisterHotKey(None, binding.hotkey_id, 0, binding.vk_code))
            if not registered:
                error_code = ctypes.get_last_error()
                self.error.emit(
                    f"Не удалось зарегистрировать hotkey {binding.display}. "
                    f"Код WinAPI: {error_code}."
                )
                self.unregister_all()
                return False

            self._registered_ids.add(binding.hotkey_id)

        return True

    def unregister_all(self) -> None:
        """Unregisters all active global hotkeys."""
        for hotkey_id in list(self._registered_ids):
            user32.UnregisterHotKey(None, hotkey_id)
            self._registered_ids.discard(hotkey_id)

    def shutdown(self) -> None:
        """Releases hotkeys and native event filter on app shutdown."""
        self.unregister_all()
        if self._filter_installed:
            self._app.removeNativeEventFilter(self._event_filter)
            self._filter_installed = False

    def _dispatch_hotkey(self, hotkey_id: int) -> None:
        """Maps hotkey IDs to user-facing action signals."""
        action = next((b.action for b in HOTKEY_BINDINGS if b.hotkey_id == hotkey_id), None)
        if action == HOTKEY_ACTION_START:
            self.start_requested.emit()
        elif action == HOTKEY_ACTION_STOP:
            self.stop_requested.emit()
        elif action == HOTKEY_ACTION_PAUSE_RESUME:
            self.pause_resume_requested.emit()
        elif action == HOTKEY_ACTION_CAPTURE:
            self.capture_requested.emit()
        else:
            self.error.emit(f"Получен неизвестный hotkey id={hotkey_id}.")


def _normalize_event_type(event_type: Any) -> str:
    """Normalizes Qt native event type value to plain text."""
    if isinstance(event_type, QByteArray):
        return bytes(event_type).decode(errors="ignore")
    if isinstance(event_type, (bytes, bytearray)):
        return bytes(event_type).decode(errors="ignore")
    return str(event_type)


def _extract_native_pointer(message: Any) -> int | None:
    """Extracts integer pointer from PySide native event message argument."""
    if isinstance(message, int):
        return message if message != 0 else None

    for attr in ("value",):
        value = getattr(message, attr, None)
        if isinstance(value, int) and value != 0:
            return value

    try:
        ptr = int(message)
    except Exception:  # noqa: BLE001
        return None

    return ptr if ptr != 0 else None
