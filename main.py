"""Windows entrypoint for the AutoClicker MVP desktop application."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from config import APP_MUTEX_NAME, APP_NAME, APP_ORG, APP_VERSION
from core.clicker_service import ClickerService
from core.hotkey_service import HotkeyService
from ui.main_window import MainWindow

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

ERROR_ALREADY_EXISTS = 183
MB_OK = 0x00000000
MB_ICONERROR = 0x00000010

kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
user32.MessageBoxW.restype = ctypes.c_int


class SingleInstanceGuard:
    """Named mutex guard that prevents launching a second app instance."""

    def __init__(self, mutex_name: str) -> None:
        self._mutex_name = mutex_name
        self._handle: int | None = None

    def acquire(self) -> bool:
        """Acquires named mutex and returns False if another instance exists."""
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, False, self._mutex_name)
        if not handle:
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "CreateMutexW failed")

        self._handle = int(handle)
        return ctypes.get_last_error() != ERROR_ALREADY_EXISTS

    def release(self) -> None:
        """Releases mutex handle."""
        if self._handle is None:
            return
        kernel32.CloseHandle(self._handle)
        self._handle = None


def _show_already_running_message() -> None:
    """Shows a native dialog when second app instance is blocked."""
    user32.MessageBoxW(
        None,
        "Приложение уже запущено. Закройте существующий экземпляр и попробуйте снова.",
        APP_NAME,
        MB_OK | MB_ICONERROR,
    )


def main() -> int:
    """Bootstraps application services and starts Qt event loop."""
    if sys.platform != "win32":
        print("Это приложение поддерживается только на Windows.")
        return 1

    instance_guard = SingleInstanceGuard(APP_MUTEX_NAME)
    try:
        if not instance_guard.acquire():
            _show_already_running_message()
            return 0

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName(APP_ORG)

        icon_path = Path(__file__).resolve().parent / "assets" / "branding" / "app_icon.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        clicker_service = ClickerService()
        hotkey_service = HotkeyService(app)
        window = MainWindow(clicker_service, hotkey_service)

        cleaned = False

        def cleanup() -> None:
            nonlocal cleaned
            if cleaned:
                return
            cleaned = True
            hotkey_service.shutdown()
            clicker_service.shutdown()
            instance_guard.release()

        app.aboutToQuit.connect(cleanup)

        if hotkey_service.register_default_hotkeys():
            window.append_log("Глобальные hotkeys зарегистрированы (F6/F7/F8/F9).")
        else:
            window.append_log("Регистрация hotkeys завершилась с ошибками.")

        window.show()
        exit_code = app.exec()
        cleanup()
        return int(exit_code)
    finally:
        instance_guard.release()


if __name__ == "__main__":
    raise SystemExit(main())
