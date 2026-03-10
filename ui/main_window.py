"""Main application window for the AutoClicker MVP."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import (
    APP_NAME,
    APP_VERSION,
    COUNT_MAX,
    COUNT_MIN,
    HOTKEY_BINDINGS,
    INTERVAL_MAX_MS,
    INTERVAL_MIN_MS,
    LOG_MAX_LINES,
)
from core.clicker_service import ClickerService
from core.hotkey_service import HotkeyService
from core.models import AppState, ClickConfig, ClickMode, MouseButton
from core.validators import get_virtual_screen_bounds, validate_config

user32 = ctypes.WinDLL("user32", use_last_error=True)


class POINT(ctypes.Structure):
    """WinAPI POINT structure."""

    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL


def _get_cursor_position() -> tuple[int, int] | None:
    """Returns current cursor coordinates from WinAPI."""
    point = POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        return None
    return int(point.x), int(point.y)


class MainWindow(QMainWindow):
    """Primary user interface for clicker configuration and control."""

    def __init__(self, clicker_service: ClickerService, hotkey_service: HotkeyService) -> None:
        super().__init__()
        self._clicker_service = clicker_service
        self._hotkey_service = hotkey_service
        self._state = clicker_service.state

        self._build_ui()
        self._connect_signals()
        self._apply_styles()
        self._apply_state(self._state)
        self._append_hotkey_hint()
        self.append_log("Приложение готово к работе.")

    def append_log(self, message: str) -> None:
        """Appends timestamped entry to GUI log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.appendPlainText(f"[{timestamp}] {message}")

    def handle_start(self) -> None:
        """Starts clicker after form validation."""
        config = self._collect_click_config()
        bounds = get_virtual_screen_bounds()
        errors = validate_config(config, bounds, self._clicker_service.state)
        if errors:
            text = "Невозможно запустить кликер:\n\n" + "\n".join(f"- {err}" for err in errors)
            self._show_error(text)
            self.append_log("Запуск отклонен: ошибки валидации формы.")
            return

        self._clicker_service.start(config)

    def handle_stop(self) -> None:
        """Stops active clicker session."""
        self._clicker_service.stop()

    def handle_pause(self) -> None:
        """Pauses active clicker session."""
        self._clicker_service.pause()

    def handle_resume(self) -> None:
        """Resumes paused clicker session."""
        self._clicker_service.resume()

    def capture_cursor_position(self) -> None:
        """Captures cursor coordinates into point fields."""
        if self._state not in (AppState.IDLE, AppState.STOPPED):
            self.append_log("Захват координат доступен только когда кликер не выполняется.")
            return

        position = _get_cursor_position()
        if position is None:
            self._show_error("Не удалось получить текущие координаты курсора.")
            self.append_log("Ошибка захвата координат курсора.")
            return

        x, y = position
        self.x_input.setText(str(x))
        self.y_input.setText(str(y))
        self.append_log(f"Координаты захвачены: X={x}, Y={y}.")

    def _build_ui(self) -> None:
        """Creates all widgets and layouts."""
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1120, 760)
        self.setMinimumSize(980, 680)
        self._try_set_window_icon()

        central = QWidget(self)
        central.setObjectName("root")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 18, 20, 18)
        header_layout.setSpacing(6)

        title_label = QLabel("AutoClicker MVP")
        title_label.setObjectName("titleLabel")
        title_label.setFont(QFont("Segoe UI Semibold", 20))

        subtitle_label = QLabel(
            "Высокоскоростной автокликер для Windows. "
            "Интервал 0 мс включает максимальную скорость."
        )
        subtitle_label.setObjectName("subtitleLabel")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        root.addWidget(header_card)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)
        root.addLayout(content_layout, stretch=1)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(14)
        content_layout.addLayout(left_panel, stretch=3)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(14)
        content_layout.addLayout(right_panel, stretch=2)

        self.settings_card = QFrame()
        self.settings_card.setObjectName("card")
        settings_layout = QVBoxLayout(self.settings_card)
        settings_layout.setContentsMargins(16, 14, 16, 14)
        settings_layout.setSpacing(10)

        settings_title = QLabel("Настройки")
        settings_title.setObjectName("cardTitle")
        settings_layout.addWidget(settings_title)

        settings_form = QFormLayout()
        settings_form.setHorizontalSpacing(12)
        settings_form.setVerticalSpacing(10)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("По сохраненной точке", ClickMode.SAVED_POINT)
        self.mode_combo.addItem("По текущему положению курсора", ClickMode.CURRENT_POSITION)
        settings_form.addRow("Режим клика:", self.mode_combo)

        point_container = QWidget()
        point_layout = QHBoxLayout(point_container)
        point_layout.setContentsMargins(0, 0, 0, 0)
        point_layout.setSpacing(8)

        int_validator = QIntValidator(-(2**31), 2**31 - 1, self)
        self.x_input = QLineEdit()
        self.x_input.setPlaceholderText("X")
        self.x_input.setValidator(int_validator)
        self.y_input = QLineEdit()
        self.y_input.setPlaceholderText("Y")
        self.y_input.setValidator(int_validator)
        self.capture_button = QPushButton("Захватить (F9)")
        self.capture_button.setObjectName("secondaryButton")

        point_layout.addWidget(QLabel("X:"))
        point_layout.addWidget(self.x_input)
        point_layout.addWidget(QLabel("Y:"))
        point_layout.addWidget(self.y_input)
        point_layout.addWidget(self.capture_button)
        settings_form.addRow("Координаты:", point_container)

        self.button_combo = QComboBox()
        self.button_combo.addItem("Левая", MouseButton.LEFT)
        self.button_combo.addItem("Правая", MouseButton.RIGHT)
        self.button_combo.addItem("Средняя", MouseButton.MIDDLE)
        settings_form.addRow("Кнопка мыши:", self.button_combo)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(INTERVAL_MIN_MS, INTERVAL_MAX_MS)
        self.interval_spin.setValue(1)
        self.interval_spin.setSuffix(" мс")
        settings_form.addRow("Интервал:", self.interval_spin)

        self.interval_hint_label = QLabel("Подсказка: 0 мс = максимальная скорость кликов.")
        self.interval_hint_label.setObjectName("hintLabel")
        settings_form.addRow("", self.interval_hint_label)

        count_container = QWidget()
        count_layout = QHBoxLayout(count_container)
        count_layout.setContentsMargins(0, 0, 0, 0)
        count_layout.setSpacing(10)

        self.infinite_checkbox = QCheckBox("Бесконечно")
        self.infinite_checkbox.setChecked(True)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(COUNT_MIN, COUNT_MAX)
        self.count_spin.setValue(1000)
        count_layout.addWidget(self.infinite_checkbox)
        count_layout.addWidget(self.count_spin)
        settings_form.addRow("Количество кликов:", count_container)

        settings_layout.addLayout(settings_form)
        left_panel.addWidget(self.settings_card)

        controls_card = QFrame()
        controls_card.setObjectName("card")
        controls_layout = QGridLayout(controls_card)
        controls_layout.setContentsMargins(16, 14, 16, 14)
        controls_layout.setHorizontalSpacing(10)
        controls_layout.setVerticalSpacing(10)

        controls_title = QLabel("Управление")
        controls_title.setObjectName("cardTitle")
        controls_layout.addWidget(controls_title, 0, 0, 1, 2)

        self.start_button = QPushButton("Start (F6)")
        self.start_button.setObjectName("startButton")
        self.stop_button = QPushButton("Stop (F7)")
        self.stop_button.setObjectName("stopButton")
        self.pause_button = QPushButton("Pause")
        self.pause_button.setObjectName("secondaryButton")
        self.resume_button = QPushButton("Resume")
        self.resume_button.setObjectName("secondaryButton")

        controls_layout.addWidget(self.start_button, 1, 0)
        controls_layout.addWidget(self.stop_button, 1, 1)
        controls_layout.addWidget(self.pause_button, 2, 0)
        controls_layout.addWidget(self.resume_button, 2, 1)

        left_panel.addWidget(controls_card)

        self.hotkey_hint_label = QLabel()
        self.hotkey_hint_label.setObjectName("hintLabel")
        left_panel.addWidget(self.hotkey_hint_label)
        left_panel.addStretch(1)

        status_card = QFrame()
        status_card.setObjectName("card")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(16, 14, 16, 14)
        status_layout.setSpacing(10)

        status_title = QLabel("Статус")
        status_title.setObjectName("cardTitle")
        status_layout.addWidget(status_title)

        self.state_badge = QLabel("IDLE")
        self.state_badge.setObjectName("stateBadge")
        self.state_badge.setAlignment(Qt.AlignCenter)

        self.count_label = QLabel("Клики: 0")
        self.count_label.setObjectName("metricLabel")

        status_layout.addWidget(self.state_badge)
        status_layout.addWidget(self.count_label)
        right_panel.addWidget(status_card)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 14, 16, 14)
        log_layout.setSpacing(10)

        log_title = QLabel("Журнал событий")
        log_title.setObjectName("cardTitle")
        log_layout.addWidget(log_title)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(LOG_MAX_LINES)
        self.log_output.setObjectName("logOutput")
        log_layout.addWidget(self.log_output, stretch=1)

        right_panel.addWidget(log_card, stretch=1)

    def _connect_signals(self) -> None:
        """Wires UI, clicker, and hotkey signals."""
        self.start_button.clicked.connect(self.handle_start)
        self.stop_button.clicked.connect(self.handle_stop)
        self.pause_button.clicked.connect(self.handle_pause)
        self.resume_button.clicked.connect(self.handle_resume)
        self.capture_button.clicked.connect(self.capture_cursor_position)

        self.mode_combo.currentIndexChanged.connect(self._update_point_controls)
        self.infinite_checkbox.toggled.connect(self._on_infinite_toggled)

        self._clicker_service.state_changed.connect(self._on_state_changed)
        self._clicker_service.click_count_changed.connect(self._on_click_count_changed)
        self._clicker_service.log.connect(self.append_log)
        self._clicker_service.error.connect(self._on_service_error)

        self._hotkey_service.start_requested.connect(self.handle_start)
        self._hotkey_service.stop_requested.connect(self.handle_stop)
        self._hotkey_service.pause_resume_requested.connect(self._on_pause_resume_hotkey)
        self._hotkey_service.capture_requested.connect(self.capture_cursor_position)
        self._hotkey_service.error.connect(self._on_hotkey_error)

    def _collect_click_config(self) -> ClickConfig:
        """Builds click config from form values."""
        mode = cast(ClickMode, self.mode_combo.currentData())
        button = cast(MouseButton, self.button_combo.currentData())
        interval_ms = int(self.interval_spin.value())
        click_limit = None if self.infinite_checkbox.isChecked() else int(self.count_spin.value())

        target_x: int | None = None
        target_y: int | None = None
        if mode is ClickMode.SAVED_POINT:
            target_x = self._parse_coordinate(self.x_input.text())
            target_y = self._parse_coordinate(self.y_input.text())

        return ClickConfig(
            mode=mode,
            button=button,
            interval_ms=interval_ms,
            click_limit=click_limit,
            target_x=target_x,
            target_y=target_y,
        )

    def _on_state_changed(self, state: AppState) -> None:
        """Receives clicker state updates."""
        self._state = state
        self._apply_state(state)
        self.append_log(f"Состояние изменено: {state.value}.")

    def _on_click_count_changed(self, click_count: int) -> None:
        """Updates click counter label."""
        self.count_label.setText(f"Клики: {click_count}")

    def _on_service_error(self, message: str) -> None:
        """Shows user-facing clicker error."""
        self.append_log(f"Ошибка: {message}")
        self._show_error(message)

    def _on_hotkey_error(self, message: str) -> None:
        """Shows user-facing hotkey registration/dispatch error."""
        self.append_log(f"Ошибка hotkey: {message}")
        self._show_error(message)

    def _on_pause_resume_hotkey(self) -> None:
        """Toggles pause/resume on F8 hotkey."""
        if self._state is AppState.RUNNING:
            self.handle_pause()
            return
        if self._state is AppState.PAUSED:
            self.handle_resume()
            return
        self.append_log("Hotkey Pause/Resume проигнорирован: кликер не запущен.")

    def _on_infinite_toggled(self, checked: bool) -> None:
        """Disables fixed count input in infinite mode."""
        editable = self._state in (AppState.IDLE, AppState.STOPPED)
        self.count_spin.setEnabled(editable and not checked)

    def _apply_state(self, state: AppState) -> None:
        """Applies state-dependent UI enablement rules."""
        editable = state in (AppState.IDLE, AppState.STOPPED)

        self.mode_combo.setEnabled(editable)
        self.button_combo.setEnabled(editable)
        self.interval_spin.setEnabled(editable)
        self.infinite_checkbox.setEnabled(editable)
        self.count_spin.setEnabled(editable and not self.infinite_checkbox.isChecked())

        self.start_button.setEnabled(state in (AppState.IDLE, AppState.STOPPED))
        self.stop_button.setEnabled(state in (AppState.RUNNING, AppState.PAUSED))
        self.pause_button.setEnabled(state is AppState.RUNNING)
        self.resume_button.setEnabled(state is AppState.PAUSED)

        self._apply_state_badge(state)
        self._update_point_controls()

    def _update_point_controls(self) -> None:
        """Enables/disables coordinate controls based on mode and state."""
        editable = self._state in (AppState.IDLE, AppState.STOPPED)
        mode = cast(ClickMode, self.mode_combo.currentData())
        point_editable = editable and mode is ClickMode.SAVED_POINT

        self.x_input.setEnabled(point_editable)
        self.y_input.setEnabled(point_editable)
        self.capture_button.setEnabled(editable)

    def _append_hotkey_hint(self) -> None:
        """Displays static hint about registered default hotkeys."""
        items = ", ".join(f"{binding.display}={binding.action}" for binding in HOTKEY_BINDINGS)
        self.hotkey_hint_label.setText(f"Глобальные hotkeys: {items}")

    def _apply_state_badge(self, state: AppState) -> None:
        """Applies visual style for current clicker state."""
        self.state_badge.setText(state.value)
        palette = {
            AppState.IDLE: ("#374151", "#E5E7EB"),
            AppState.RUNNING: ("#065F46", "#D1FAE5"),
            AppState.PAUSED: ("#92400E", "#FEF3C7"),
            AppState.STOPPED: ("#9A3412", "#FFEDD5"),
        }
        fg, bg = palette[state]
        self.state_badge.setStyleSheet(
            f"color: {fg}; background: {bg}; border-radius: 12px; padding: 8px 12px; font-weight: 700;"
        )

    def _try_set_window_icon(self) -> None:
        """Sets app window icon if branded icon file exists."""
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "branding" / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    @staticmethod
    def _parse_coordinate(value: str) -> int | None:
        """Parses coordinate text input."""
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return int(cleaned)
        except ValueError:
            return None

    def _show_error(self, message: str) -> None:
        """Shows an error dialog to the user."""
        QMessageBox.critical(self, "Ошибка", message)

    def _apply_styles(self) -> None:
        """Applies polished visual style for a premium desktop look."""
        self.setStyleSheet(
            """
            QWidget#root {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f0f7ff, stop: 1 #eef2ff);
                color: #111827;
                font-family: "Segoe UI";
                font-size: 13px;
            }
            QFrame#headerCard {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #1d4ed8, stop: 1 #2563eb);
                border-radius: 16px;
            }
            QLabel#titleLabel {
                color: #ffffff;
                font-weight: 700;
            }
            QLabel#subtitleLabel {
                color: rgba(255, 255, 255, 230);
                font-size: 12px;
            }
            QFrame#card {
                background: #ffffff;
                border: 1px solid #dbe7ff;
                border-radius: 14px;
            }
            QLabel#cardTitle {
                font-size: 14px;
                font-weight: 700;
                color: #1f2937;
            }
            QLabel#hintLabel {
                color: #4b5563;
                font-size: 12px;
            }
            QLabel#metricLabel {
                font-size: 16px;
                font-weight: 600;
                color: #0f172a;
            }
            QLineEdit, QSpinBox, QComboBox, QPlainTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 6px 8px;
                background: #ffffff;
                selection-background-color: #2563eb;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {
                border: 1px solid #3b82f6;
            }
            QPushButton {
                border: none;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 600;
                background: #e5e7eb;
                color: #111827;
            }
            QPushButton#startButton {
                background: #10b981;
                color: #ffffff;
            }
            QPushButton#startButton:hover {
                background: #059669;
            }
            QPushButton#stopButton {
                background: #ef4444;
                color: #ffffff;
            }
            QPushButton#stopButton:hover {
                background: #dc2626;
            }
            QPushButton#secondaryButton {
                background: #e2e8f0;
                color: #0f172a;
            }
            QPushButton#secondaryButton:hover {
                background: #cbd5e1;
            }
            QPushButton:disabled {
                background: #f1f5f9;
                color: #94a3b8;
            }
            QPlainTextEdit#logOutput {
                background: #0b1220;
                color: #dbeafe;
                border: 1px solid #1e293b;
                border-radius: 10px;
                font-family: Consolas;
                font-size: 12px;
            }
            """
        )
