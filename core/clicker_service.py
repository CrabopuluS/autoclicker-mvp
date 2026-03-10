"""Clicker execution service with a non-blocking worker thread."""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from typing import Final

from PySide6.QtCore import QObject, QThread, Signal

from config import HIGH_RES_TIMER_PERIOD_MS
from core.models import AppState, ClickConfig, ClickMode, MouseButton, can_transition

user32 = ctypes.WinDLL("user32", use_last_error=True)
winmm = ctypes.WinDLL("winmm", use_last_error=True)

INPUT_MOUSE: Final[int] = 0
MOUSEEVENTF_LEFTDOWN: Final[int] = 0x0002
MOUSEEVENTF_LEFTUP: Final[int] = 0x0004
MOUSEEVENTF_RIGHTDOWN: Final[int] = 0x0008
MOUSEEVENTF_RIGHTUP: Final[int] = 0x0010
MOUSEEVENTF_MIDDLEDOWN: Final[int] = 0x0020
MOUSEEVENTF_MIDDLEUP: Final[int] = 0x0040

WPARAM = wintypes.WPARAM if hasattr(wintypes, "WPARAM") else ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    """WinAPI MOUSEINPUT structure."""

    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", WPARAM),
    ]


class INPUT_UNION(ctypes.Union):
    """Union member for WinAPI INPUT structure."""

    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    """WinAPI INPUT structure."""

    _fields_ = [("type", wintypes.DWORD), ("data", INPUT_UNION)]


user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
winmm.timeBeginPeriod.argtypes = [wintypes.UINT]
winmm.timeBeginPeriod.restype = wintypes.UINT
winmm.timeEndPeriod.argtypes = [wintypes.UINT]
winmm.timeEndPeriod.restype = wintypes.UINT

_BUTTON_FLAGS: dict[MouseButton, tuple[int, int]] = {
    MouseButton.LEFT: (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    MouseButton.RIGHT: (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    MouseButton.MIDDLE: (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


def _send_input_click(button: MouseButton) -> bool:
    """Sends a single mouse click with WinAPI SendInput."""
    down_flag, up_flag = _BUTTON_FLAGS[button]
    inputs = (INPUT * 2)(
        INPUT(
            type=INPUT_MOUSE,
            data=INPUT_UNION(
                mi=MOUSEINPUT(
                    dx=0,
                    dy=0,
                    mouseData=0,
                    dwFlags=down_flag,
                    time=0,
                    dwExtraInfo=0,
                )
            ),
        ),
        INPUT(
            type=INPUT_MOUSE,
            data=INPUT_UNION(
                mi=MOUSEINPUT(
                    dx=0,
                    dy=0,
                    mouseData=0,
                    dwFlags=up_flag,
                    time=0,
                    dwExtraInfo=0,
                )
            ),
        ),
    )
    sent = int(user32.SendInput(2, inputs, ctypes.sizeof(INPUT)))
    return sent == 2


def _set_cursor_position(x: int, y: int) -> bool:
    """Moves cursor to absolute screen coordinates."""
    return bool(user32.SetCursorPos(x, y))


class ClickWorker(QThread):
    """Background click loop running in a dedicated thread."""

    click_performed = Signal(int)
    log = Signal(str)
    error = Signal(str)
    done = Signal(bool)

    def __init__(self, config: ClickConfig) -> None:
        super().__init__()
        self._config = config
        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self._resume_event.set()

    def run(self) -> None:
        """Runs click sequence until stopped or click limit reached."""
        timer_armed = _enable_high_res_timer(HIGH_RES_TIMER_PERIOD_MS)
        self.log.emit("Поток кликов запущен.")
        clicks_done = 0
        completed_by_limit = False

        try:
            while not self._stop_event.is_set():
                if not self._resume_event.is_set():
                    if not self._wait_until_resumed_or_stopped():
                        break

                if self._stop_event.is_set():
                    break

                if self._config.mode is ClickMode.SAVED_POINT:
                    target_x = self._config.target_x
                    target_y = self._config.target_y
                    if target_x is None or target_y is None:
                        self.error.emit(
                            "Внутренняя ошибка: координаты для режима сохраненной точки не заданы."
                        )
                        break
                    if not _set_cursor_position(target_x, target_y):
                        error_code = ctypes.get_last_error()
                        self.error.emit(
                            f"Не удалось переместить курсор в ({target_x}, {target_y}). "
                            f"Код WinAPI: {error_code}."
                        )
                        break

                if not _send_input_click(self._config.button):
                    error_code = ctypes.get_last_error()
                    self.error.emit(f"Не удалось выполнить клик. Код WinAPI: {error_code}.")
                    break

                clicks_done += 1
                self.click_performed.emit(clicks_done)

                if self._config.click_limit is not None and clicks_done >= self._config.click_limit:
                    completed_by_limit = True
                    self.log.emit("Достигнуто заданное количество кликов.")
                    break

                if not self._wait_interval(self._config.interval_ms):
                    break
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Необработанная ошибка в потоке кликов: {exc}.")
        finally:
            if timer_armed:
                _disable_high_res_timer(HIGH_RES_TIMER_PERIOD_MS)
            self.done.emit(completed_by_limit)
            self.log.emit("Поток кликов завершен.")

    def pause(self) -> None:
        """Pauses click loop."""
        self._resume_event.clear()

    def resume(self) -> None:
        """Resumes click loop."""
        self._resume_event.set()

    def stop(self) -> None:
        """Requests worker shutdown."""
        self._stop_event.set()
        self._resume_event.set()

    def _wait_until_resumed_or_stopped(self) -> bool:
        """Waits while paused and returns False if stopped."""
        while not self._stop_event.is_set() and not self._resume_event.is_set():
            time.sleep(0.005)
        return not self._stop_event.is_set()

    def _wait_interval(self, interval_ms: int) -> bool:
        """Waits between clicks with high responsiveness and max-speed mode support."""
        if interval_ms <= 0:
            return not self._stop_event.is_set()

        remaining = interval_ms / 1000.0
        while remaining > 0.0:
            if self._stop_event.is_set():
                return False
            if not self._resume_event.is_set():
                if not self._wait_until_resumed_or_stopped():
                    return False
                continue

            started_at = time.perf_counter()
            if remaining > 0.003:
                time.sleep(min(0.001, remaining))
            else:
                # Yield without long sleep for very short intervals.
                time.sleep(0)
            remaining -= max(0.0, time.perf_counter() - started_at)
        return True


class ClickerService(QObject):
    """Facade managing worker lifecycle and emitting UI-friendly signals."""

    state_changed = Signal(object)
    click_count_changed = Signal(int)
    log = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._state = AppState.IDLE
        self._click_count = 0
        self._worker: ClickWorker | None = None

    @property
    def state(self) -> AppState:
        """Current clicker state."""
        return self._state

    def start(self, config: ClickConfig) -> None:
        """Starts click loop with given validated config."""
        if self._worker is not None and self._worker.isRunning():
            self.error.emit("Кликер уже запущен. Остановите текущую сессию перед новым стартом.")
            return

        if not can_transition(self._state, AppState.RUNNING):
            self.error.emit(
                f"Невозможно запустить кликер из состояния {self._state.value}."
            )
            return

        self._click_count = 0
        self.click_count_changed.emit(self._click_count)

        worker = ClickWorker(config)
        worker.click_performed.connect(self._on_click_performed)
        worker.log.connect(self.log)
        worker.error.connect(self._on_worker_error)
        worker.done.connect(self._on_worker_done)
        worker.finished.connect(self._on_worker_finished)

        self._worker = worker
        self._set_state(AppState.RUNNING)
        self.log.emit("Кликер запущен.")
        worker.start()

    def pause(self) -> None:
        """Pauses running click loop."""
        if self._state is not AppState.RUNNING:
            self.error.emit("Пауза доступна только в состоянии RUNNING.")
            return
        if self._worker is None or not self._worker.isRunning():
            self.error.emit("Нельзя поставить на паузу: поток кликов не активен.")
            return

        self._worker.pause()
        self._set_state(AppState.PAUSED)
        self.log.emit("Кликер поставлен на паузу.")

    def resume(self) -> None:
        """Resumes paused click loop."""
        if self._state is not AppState.PAUSED:
            self.error.emit("Возобновление доступно только в состоянии PAUSED.")
            return
        if self._worker is None or not self._worker.isRunning():
            self.error.emit("Нельзя возобновить: поток кликов не активен.")
            return

        self._worker.resume()
        self._set_state(AppState.RUNNING)
        self.log.emit("Кликер возобновлен.")

    def stop(self) -> None:
        """Stops active click loop."""
        if self._state not in (AppState.RUNNING, AppState.PAUSED):
            self.log.emit("Остановка игнорирована: кликер не запущен.")
            return

        if self._worker is not None and self._worker.isRunning():
            self._worker.stop()

        self._set_state(AppState.STOPPED)
        self.log.emit("Запрошена остановка кликера.")

    def shutdown(self, timeout_ms: int = 2000) -> None:
        """Gracefully stops worker during app shutdown."""
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.stop()
            if not worker.wait(timeout_ms):
                self.error.emit(
                    "Не удалось корректно остановить поток кликов перед завершением приложения."
                )

        if self._state in (AppState.RUNNING, AppState.PAUSED):
            self._set_state(AppState.STOPPED)

        self._worker = None

    def _set_state(self, new_state: AppState) -> None:
        """Transitions service state and emits update signal."""
        if new_state == self._state:
            return

        if not can_transition(self._state, new_state):
            self.error.emit(
                f"Недопустимый переход состояния: {self._state.value} -> {new_state.value}."
            )
            return

        self._state = new_state
        self.state_changed.emit(self._state)

    def _on_click_performed(self, click_count: int) -> None:
        """Updates click counter from worker."""
        self._click_count = click_count
        self.click_count_changed.emit(click_count)

    def _on_worker_error(self, message: str) -> None:
        """Handles worker errors and forces STOPPED state."""
        self.error.emit(message)
        if self._state in (AppState.RUNNING, AppState.PAUSED):
            self._set_state(AppState.STOPPED)

    def _on_worker_done(self, completed_by_limit: bool) -> None:
        """Finalizes state when worker exits."""
        if completed_by_limit:
            self.log.emit("Серия кликов завершена по заданному лимиту.")

        if self._state in (AppState.RUNNING, AppState.PAUSED):
            self._set_state(AppState.STOPPED)

        self.finished.emit()

    def _on_worker_finished(self) -> None:
        """Cleans up worker reference."""
        sender = self.sender()
        if isinstance(sender, ClickWorker):
            sender.deleteLater()
            if self._worker is sender:
                self._worker = None


def _enable_high_res_timer(period_ms: int) -> bool:
    """Requests higher Windows timer resolution for tighter click intervals."""
    return winmm.timeBeginPeriod(period_ms) == 0


def _disable_high_res_timer(period_ms: int) -> None:
    """Restores Windows timer resolution after worker exit."""
    winmm.timeEndPeriod(period_ms)
