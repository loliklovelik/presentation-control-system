import time
import json

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QFrame,
                             QMessageBox, QSizePolicy
                             )
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QByteArray
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QFontMetrics
from presentation_script import PresentationScript, PresentationStage
from powerpoint_controller import PowerPointController
from datetime import datetime

from timer_engine import TimerEngine, TimerMode
from sound_manager import SoundManager
from compact_window import CompactWindow
from settings_manager import SettingsManager
from utils import time_str_to_ms, validate_time_input
from database_manager import DatabaseManager
from script_editor import ScriptEditor

from ui.button_styles import (
    START_BUTTON,
    RESET_BUTTON,
    COMPACT_BUTTON,
    SETTINGS_BUTTON,
    FINISH_BUTTON,
    PAUSE_BUTTON,
    RESUME_BUTTON,
    QUICK_TIME_BUTTON
)

from ui.main_style import MAIN_STYLE, SECONDARY_TIMER_LABEL, TIME_INPUT, INPUT_LABEL, PAUSE_STATS_LABEL



class ScaledLabel(QLabel):
    """QLabel с автоматическим масштабированием шрифта относительно родительского окна"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.base_font_size = 16
        self._original_text = text
        self.transparent_mode = False
        self._update_font()

    def _update_font(self):
        font = QFont("Arial", self.base_font_size, QFont.Weight.Bold)
        self.setFont(font)

    def setBaseFontSize(self, size: int):
        self.base_font_size = size
        self._update_font()

    def setText(self, text):
        super().setText(text)
        self._original_text = text

    def scale_font(self, window_width, window_height, base_width, base_height):
        """Масштабирование шрифта относительно размеров окна"""
        if window_width <= 0 or window_height <= 0:
            return

        scale_x = window_width / base_width
        scale_y = window_height / base_height
        scale = min(scale_x, scale_y)
        scale = max(0.7, min(scale, 2.0))

        new_size = int(self.base_font_size * scale)
        new_size = max(8, min(new_size, 36))

        font = self.font()
        font.setPointSize(new_size)
        self.setFont(font)


class ScaledLineEdit(QLineEdit):
    """QLineEdit с автоматическим масштабированием шрифта относительно родительского окна"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.base_font_size = 20
        self._update_font()

    def _update_font(self):
        font = QFont("Arial", self.base_font_size, QFont.Weight.Bold)
        self.setFont(font)

    def setBaseFontSize(self, size: int):
        self.base_font_size = size
        self._update_font()

    def scale_font(self, window_width, window_height, base_width, base_height):
        """Масштабирование шрифта относительно размеров окна"""
        if window_width <= 0 or window_height <= 0:
            return

        scale_x = window_width / base_width
        scale_y = window_height / base_height
        scale = min(scale_x, scale_y)
        scale = max(0.7, min(scale, 2.0))

        new_size = int(self.base_font_size * scale)
        new_size = max(10, min(new_size, 36))

        font = self.font()
        font.setPointSize(new_size)
        self.setFont(font)


class ScaledTimerLabel(QLabel):
    """Специальная метка для таймера с масштабированием по ширине и высоте"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.base_font_size = 60
        self.is_secondary = False
        self._original_width = 0
        self._original_height = 0
        self._update_font()

    def _update_font(self):
        """Устанавливает начальный шрифт"""
        font = QFont("Arial", self.base_font_size, QFont.Weight.Bold)
        self.setFont(font)

    def showEvent(self, event):
        """Запоминаем исходные размеры при первом показе"""
        super().showEvent(event)
        if self._original_width == 0 and self.width() > 0:
            self._original_width = self.width()
        if self._original_height == 0 and self.height() > 0:
            self._original_height = self.height()
        self.scale_font()

    def resizeEvent(self, event):
        """Автоматически масштабирует шрифт при изменении размера"""
        super().resizeEvent(event)
        self.scale_font()

    def scale_font(self):
        """Масштабирование шрифта с учётом ширины и высоты"""
        if self.width() <= 0 or self.height() <= 0:
            return

        if self._original_width == 0:
            self._original_width = self.width()
        if self._original_height == 0:
            self._original_height = self.height()

        if self._original_width <= 0 or self._original_height <= 0:
            return

        text = self.text()
        if not text:
            return

        # Вычисляем коэффициенты масштабирования по ширине и высоте
        scale_x = self.width() / self._original_width
        scale_y = self.height() / self._original_height

        # Берём минимальный коэффициент, чтобы шрифт не вылезал за пределы
        scale = min(scale_x, scale_y)
        scale = max(0.5, min(scale, 4.0))

        new_size = int(self.base_font_size * scale)

        if self.is_secondary:
            new_size = max(12, min(new_size, 120))
        else:
            new_size = max(20, min(new_size, 300))

        # ПРОВЕРКА ПО ШИРИНЕ: уменьшаем шрифт, если не влезает
        available_width = self.width() - 20

        while new_size > 12:
            font = QFont("Arial", new_size, QFont.Weight.Bold)
            metrics = QFontMetrics(font)
            text_width = metrics.horizontalAdvance(text)

            if text_width <= available_width:
                break
            new_size -= 2

        font = self.font()
        font.setPointSize(new_size)
        self.setFont(font)



class ScaledButton(QPushButton):
    """QPushButton с автоматическим масштабированием шрифта по ширине и высоте"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.base_font_size = 22
        self._original_text = text
        self._original_width = 0
        self._original_height = 0
        self._font_initialized = False
        self._update_font()

    def _update_font(self):
        """Устанавливает начальный шрифт"""
        font = QFont("Arial", self.base_font_size, QFont.Weight.Bold)
        self.setFont(font)

    def setText(self, text):
        """Переопределяем setText для сохранения оригинального текста"""
        super().setText(text)
        self._original_text = text
        self.scale_font()

    def showEvent(self, event):
        """Запоминаем исходные размеры при первом показе"""
        super().showEvent(event)
        if not self._font_initialized and self.width() > 0 and self.height() > 0:
            self._original_width = self.width()
            self._original_height = self.height()
            self._font_initialized = True

    def resizeEvent(self, event):
        """Автоматически масштабирует шрифт при изменении размера"""
        super().resizeEvent(event)
        if not self._font_initialized and self.width() > 0 and self.height() > 0:
            self._original_width = self.width()
            self._original_height = self.height()
            self._font_initialized = True
        self.scale_font()

    def scale_font(self):
        """Масштабирование шрифта с учётом ширины и высоты кнопки"""
        if self.width() <= 0 or self.height() <= 0:
            return

        if self._original_width <= 0 or self._original_height <= 0:
            return

        # Вычисляем коэффициенты масштабирования по ширине и высоте
        scale_x = self.width() / self._original_width
        scale_y = self.height() / self._original_height

        # Берём минимальный коэффициент, чтобы шрифт не вылезал за пределы
        scale = min(scale_x, scale_y)
        scale = max(0.7, min(scale, 3.0))

        new_size = int(self.base_font_size * scale)
        new_size = max(8, min(new_size, 50))

        # Дополнительная проверка: если текст не влезает по ширине, уменьшаем шрифт
        text = self.text()
        if text:
            available_width = self.width() - 20  # отступы
            while new_size > 8:
                font = QFont("Arial", new_size, QFont.Weight.Bold)
                metrics = QFontMetrics(font)
                text_width = metrics.horizontalAdvance(text)
                if text_width <= available_width:
                    break
                new_size -= 2

        font = self.font()
        font.setPointSize(new_size)
        self.setFont(font)


class ScaledStatsLabel(QLabel):
    """QLabel для статистики с автоматическим масштабированием шрифта"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.base_font_size = 14
        self._original_height = 0
        self._update_font()

    def _update_font(self):
        """Обновляет шрифт с текущим размером"""
        font = QFont("Arial", self.base_font_size, QFont.Weight.Bold)
        self.setFont(font)

    def setBaseFontSize(self, size: int):
        """Установка базового размера шрифта"""
        self.base_font_size = size
        self._update_font()
        self.scale_font()

    def resizeEvent(self, event):
        """Автоматически масштабирует шрифт при изменении размера"""
        super().resizeEvent(event)
        if self._original_height == 0:
            self._original_height = self.height()
        self.scale_font()

    def scale_font(self):
        """Масштабирование шрифта пропорционально высоте виджета"""
        if self.height() > 0 and self._original_height > 0:
            scale_factor = self.height() / self._original_height
            scale_factor = max(0.5, min(scale_factor, 2.0))
            new_size = int(self.base_font_size * scale_factor)
            new_size = max(10, min(new_size, 24))
            font = self.font()
            font.setPointSize(new_size)
            self.setFont(font)


class MainWindow(QMainWindow):
    """Главное окно приложения - адаптивная версия"""
    script_changed = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()
        self.sound_manager = SoundManager()
        self.compact_window = None
        self.timer_engine = None
        self.settings_window = None
        self.ppt_controller = PowerPointController(self)
        self.is_ending_presentation = False

        # Цвета - будут загружены из настроек
        self.normal_bg_color = "#2E7D32"
        self.warning_bg_color = "#F9A825"
        self.overtime_bg_color = "#C62828"
        self.normal_text_color = "#FFFFFF"

        self.last_set_time = "05:00"
        self.base_width = 750
        self.base_height = 520
        self._first_show = True
        self.last_pause_stats_message = ""

        self.db_manager = DatabaseManager()

        self.current_script = None
        self.current_script_id = None
        self.stage_already_reset = False
        self.stage_stats_list = []
        self.inter_stage_pause_start = None
        self.total_inter_stage_pause_ms = 0

        self.inter_stage_timer = QTimer()
        self.inter_stage_timer.timeout.connect(self._update_inter_stage_display)

        self.pause_display_timer = QTimer()
        self.pause_display_timer.timeout.connect(self._update_pause_display)
        self.current_pause_start = None

        self.setup_ui()
        self.setup_timer()
        self.load_settings()
        self.setup_connections()
        self.setup_shortcuts()


        # === ЗАПУСК МОНИТОРИНГА POWERPOINT ===
        QTimer.singleShot(3000, self.start_ppt_monitoring)

        # Таймер для задержки сброса экрана после завершения
        self.reset_delay_timer = QTimer()
        self.reset_delay_timer.setSingleShot(True)
        self.reset_delay_timer.timeout.connect(self._do_reset_display)

    def setup_ui(self):
        """Настройка интерфейса главного окна"""
        self.setWindowTitle("Таймер выступления")

        # Устанавливаем начальный размер
        self.resize(self.base_width, self.base_height)

        # Убираем жесткие ограничения размера
        self.setMinimumSize(500, 400)

        # Разрешаем изменение размера
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Центральный виджет с автоматическими отступами
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        # Динамические отступы (будут масштабироваться)
        self.base_margins = 20
        self.base_spacing = 15

        self.main_layout.setContentsMargins(
            self.base_margins, self.base_margins,
            self.base_margins, self.base_margins
        )
        self.main_layout.setSpacing(self.base_spacing)

        # === ЗАГОЛОВОК ===
        self.title_label = ScaledLabel("ТАЙМЕР ВЫСТУПЛЕНИЯ")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setBaseFontSize(22)
        self.title_label.setStyleSheet("color: #2C3E50; margin-bottom: 5px;")
        self.main_layout.addWidget(self.title_label)

        # === ОСНОВНОЙ ДИСПЛЕЙ ТАЙМЕРА ===
        self.display_frame = QFrame()
        self.display_frame.setObjectName("displayFrame")
        self.display_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.display_frame.setMinimumHeight(150)

        display_layout = QVBoxLayout(self.display_frame)
        display_layout.setContentsMargins(10, 10, 10, 10)
        display_layout.setSpacing(10)

        # Основной таймер
        self.timer_label = ScaledTimerLabel("05:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Вторичный таймер
        self.secondary_timer_label = ScaledTimerLabel("")
        self.secondary_timer_label.is_secondary = True
        self.secondary_timer_label.base_font_size = 30
        self.secondary_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.secondary_timer_label.setObjectName("secondaryTimerLabel")
        self.secondary_timer_label.setStyleSheet(SECONDARY_TIMER_LABEL)
        self.secondary_timer_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.secondary_timer_label.hide()

        display_layout.addWidget(self.timer_label, 2)
        display_layout.addWidget(self.secondary_timer_label, 1)
        self.main_layout.addWidget(self.display_frame, 3)

        # === КОНТЕЙНЕР ДЛЯ СТАТИСТИКИ (ВСЕГДА ЗАНИМАЕТ МЕСТО) ===
        self.stats_container = QFrame()
        self.stats_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.stats_container.setFixedHeight(38)
        self.stats_container.setContentsMargins(0, 0, 0, 0)

        stats_layout = QVBoxLayout(self.stats_container)
        stats_layout.setContentsMargins(10, 0, 10, 0)
        stats_layout.setSpacing(0)

        # Горизонтальная черта - всегда невидимая
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFixedHeight(1)
        self.separator.setVisible(False)
        stats_layout.addWidget(self.separator)

        # Метка для статистики пауз
        self.pause_stats_label = QLabel("")
        self.pause_stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pause_stats_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 5px 5px 5px;
                background-color: transparent;
            }
        """)
        self.pause_stats_label.setWordWrap(False)
        self.pause_stats_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        stats_layout.addWidget(self.pause_stats_label)

        self.main_layout.addWidget(self.stats_container)

        # === ПАНЕЛЬ ВВОДА И БЫСТРОГО ВЫБОРА ВРЕМЕНИ ===
        time_selection_frame = QFrame()
        time_selection_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        time_selection_layout = QHBoxLayout(time_selection_frame)
        time_selection_layout.setSpacing(10)
        time_selection_layout.setContentsMargins(0, 5, 0, 5)

        # Поле ввода времени с подписью
        self.input_label = ScaledLabel("Время (ММ:СС):")
        self.input_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_label.setStyleSheet(INPUT_LABEL)
        self.input_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        # Поле ввода времени
        self.time_input = ScaledLineEdit("05:00")
        self.time_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_input.setPlaceholderText("ММ:СС")
        self.time_input.setStyleSheet(TIME_INPUT)
        self.time_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.time_input.setMinimumWidth(100)

        # Кнопки быстрого выбора времени
        quick_times = [("03:00", "3 мин"), ("05:00", "5 мин"), ("07:00", "7 мин")]
        self.quick_buttons = []

        # Добавляем элементы в строку
        time_selection_layout.addStretch()
        time_selection_layout.addWidget(self.input_label)
        time_selection_layout.addWidget(self.time_input, 2)

        for time_str, tooltip in quick_times:
            btn = ScaledButton(time_str)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, ts=time_str: self.set_time_from_button(ts))
            btn.setStyleSheet(QUICK_TIME_BUTTON)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self.quick_buttons.append(btn)
            time_selection_layout.addWidget(btn, 1)

            # === КНОПКА "СЛЕДУЮЩИЙ ЭТАП" (скрыта по умолчанию) ===
        self.next_stage_btn = ScaledButton("Далее")
        self.next_stage_btn.setToolTip("Перейти к следующему этапу сценария")
        self.next_stage_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3498DB;
                        color: white;
                        border-radius: 6px;
                        font-weight: bold;
                        padding: 4px;
                    }
                    QPushButton:hover { background-color: #2980B9; }
                    QPushButton:pressed { background-color: #1F6DA0; }
                """)
        self.next_stage_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.next_stage_btn.clicked.connect(self.on_next_stage)
        self.next_stage_btn.setVisible(False)  # скрыта в обычном режиме
        time_selection_layout.addWidget(self.next_stage_btn, 1)

        time_selection_layout.addStretch()
        self.main_layout.addWidget(time_selection_frame, 1)

        # === ПАНЕЛЬ ОСНОВНЫХ КНОПОК УПРАВЛЕНИЯ ===
        control_frame = QFrame()
        control_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setSpacing(10)
        control_layout.setContentsMargins(0, 5, 0, 5)

        # Создаем кнопки управления
        self.start_pause_btn = ScaledButton("СТАРТ")
        self.start_pause_btn.setStyleSheet(START_BUTTON)
        self.start_pause_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.start_pause_btn.setMinimumHeight(40)

        self.reset_btn = ScaledButton("СБРОС")
        self.reset_btn.setStyleSheet(RESET_BUTTON)
        self.reset_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.reset_btn.setMinimumHeight(40)

        self.compact_btn = ScaledButton("🗣")
        self.compact_btn.setToolTip("Компактный режим")
        self.compact_btn.setStyleSheet(COMPACT_BUTTON)
        self.compact_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.compact_btn.setMinimumHeight(40)


        self.settings_btn = ScaledButton("⚙")
        self.settings_btn.setToolTip("Настройки")
        self.settings_btn.setStyleSheet(SETTINGS_BUTTON)
        self.settings_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.settings_btn.setMinimumHeight(40)

        self.finish_btn = ScaledButton("✓")
        self.finish_btn.setToolTip("Завершить выступление")
        self.finish_btn.setStyleSheet(FINISH_BUTTON)
        self.finish_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.finish_btn.setMinimumHeight(40)

        # Добавляем в layout (порядок: Старт, Сброс, Компакт, Сценарий, Настройки, Завершить)
        control_layout.addStretch()
        control_layout.addWidget(self.start_pause_btn, 2)
        control_layout.addWidget(self.reset_btn, 2)
        control_layout.addWidget(self.compact_btn, 1)
        control_layout.addWidget(self.settings_btn, 1)
        control_layout.addWidget(self.finish_btn, 1)
        control_layout.addStretch()

        self.main_layout.addWidget(control_frame, 1)

        # Добавляем небольшой spacer в конце для красоты
        self.main_layout.addStretch()

        # Основной стиль окна
        self.setStyleSheet(MAIN_STYLE)

    def showEvent(self, event):
        """Вызывается при первом показе окна"""
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(0, self.restore_geometry)

    def restore_geometry(self):
        """Восстановление сохраненной геометрии окна"""
        geometry = self.settings.load_window_geometry()
        if geometry and isinstance(geometry, QByteArray) and not geometry.isEmpty():
            self.restoreGeometry(geometry)
        else:
            screen = self.screen().availableGeometry()
            self.setGeometry(
                screen.width() // 2 - self.base_width // 2,
                screen.height() // 2 - self.base_height // 2,
                self.base_width,
                self.base_height
            )

    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)

        scale_x = self.width() / self.base_width
        scale_y = self.height() / self.base_height
        scale = min(scale_x, scale_y, 1.5)
        scale = max(0.7, scale)

        new_margins = int(self.base_margins * scale)
        new_spacing = int(self.base_spacing * scale)

        if self.main_layout:
            self.main_layout.setContentsMargins(new_margins, new_margins, new_margins, new_margins)
            self.main_layout.setSpacing(new_spacing)

        # Масштабируем заголовок и input_label относительно размеров окна
        self.title_label.scale_font(self.width(), self.height(), self.base_width, self.base_height)
        self.input_label.scale_font(self.width(), self.height(), self.base_width, self.base_height)
        self.time_input.scale_font(self.width(), self.height(), self.base_width, self.base_height)

    def setup_timer(self):
        """Настройка таймера"""
        self.timer_engine = TimerEngine()
        self.timer_engine.time_updated.connect(self.update_timer_display)
        self.timer_engine.phase_changed.connect(self.on_phase_changed)
        self.timer_engine.time_is_up.connect(self.on_time_is_up)
        self.timer_engine.timer_state_changed.connect(self.on_timer_state_changed)
        self.timer_engine.pause_stats_updated.connect(self.update_pause_stats)
        self.timer_engine.presentation_finished.connect(self.on_presentation_finished)

    def on_presentation_finished(self, stats: dict):
        """Обработка сигнала завершения выступления"""
        pass

    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        self.start_pause_btn.clicked.connect(self.toggle_timer)
        self.reset_btn.clicked.connect(self.on_reset_timer)
        self.compact_btn.clicked.connect(self.toggle_compact)
        self.settings_btn.clicked.connect(self.show_settings)
        self.finish_btn.clicked.connect(self.finish_presentation)
        self.time_input.textChanged.connect(self.on_time_input_changed)

        # === POWERPOINT КОНТРОЛЛЕР ===
        self.ppt_controller.slide_show_started.connect(self.on_slide_show_started)
        self.ppt_controller.slide_show_ended.connect(self.on_slide_show_ended)
        self.ppt_controller.slide_changed.connect(self.on_slide_changed_auto)
        self.ppt_controller.connection_status.connect(self._on_ppt_connection)

        self.time_input.installEventFilter(self)

    def _on_ppt_connection(self, connected: bool):
        """Статус подключения к PowerPoint"""
        if connected:
            print("✅ Подключено к PowerPoint")
        else:
            print("❌ PowerPoint не найден")

    def open_script_editor(self, edit_script_id=None):
        """Открыть редактор сценариев"""
        self.editor = ScriptEditor(
            db_manager=self.db_manager,
            parent=None,
            edit_script_id=edit_script_id
        )
        self.editor.script_applied.connect(self.on_script_from_editor)
        self.editor.show()

    def on_script_applied(self, script):
        """Сценарий загружен из редактора"""
        print(f"✅ Загружен сценарий: {script.name}")
        print(f"📋 Количество этапов: {len(script.stages)}")

        for i, stage in enumerate(script.stages):
            print(f"   {i + 1}. {stage.name}: {stage.get_duration_str()}")

        # Сохраняем сценарий в БД
        script_id = self.db_manager.add_script(script.name)
        for i, stage in enumerate(script.stages):
            self.db_manager.add_script_stage(
                script_id,
                stage.name,
                stage.duration_ms,
                i,
                track_overtime=True
            )

        # Показываем сообщение
        QMessageBox.information(
            self,
            "Сценарий загружен",
            f"Сценарий «{script.name}» сохранён в БД.\n\n"
            f"📋 Этапов: {len(script.stages)}\n"
            f"⏱️ Общая длительность: {script.get_total_duration_str()}\n\n"
            f"💡 Скоро появится возможность запускать сценарии автоматически."
        )

    def eventFilter(self, obj, event):
        """Фильтр событий для запрета удаления двоеточия"""
        if obj == self.time_input and event.type() == event.Type.KeyPress:
            text = self.time_input.text()
            cursor_pos = self.time_input.cursorPosition()

            if event.key() == Qt.Key.Key_Backspace:
                if cursor_pos > 0 and text[cursor_pos - 1] == ':':
                    self.time_input.setCursorPosition(cursor_pos - 1)
                    return True

            elif event.key() == Qt.Key.Key_Delete:
                if cursor_pos < len(text) and text[cursor_pos] == ':':
                    self.time_input.setCursorPosition(cursor_pos + 1)
                    return True

        return super().eventFilter(obj, event)

    def setup_shortcuts(self):
        """Настройка локальных горячих клавиш (только когда окно в фокусе)"""
        # Ctrl+Space
        shortcut_ctrl_space = QShortcut(QKeySequence("Ctrl+Space"), self)
        shortcut_ctrl_space.activated.connect(self.toggle_timer)

        # Ctrl+R
        shortcut_reset = QShortcut(QKeySequence("Ctrl+R"), self)
        shortcut_reset.activated.connect(self.on_reset_timer)

        # Ctrl+H
        shortcut_compact = QShortcut(QKeySequence("Ctrl+H"), self)
        shortcut_compact.activated.connect(self.toggle_compact)

        # Ctrl+F
        shortcut_finish = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_finish.activated.connect(self.finish_presentation)

        # Ctrl+S
        shortcut_settings = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_settings.activated.connect(self.show_settings)

        # Ctrl+G
        shortcut_statistics = QShortcut(QKeySequence("Ctrl+G"), self)
        shortcut_statistics.activated.connect(self.toggle_statistics)

        # Быстрое время
        shortcut_time_3 = QShortcut(QKeySequence("Ctrl+1"), self)
        shortcut_time_3.activated.connect(lambda: self.set_time_from_button("03:00"))

        shortcut_time_5 = QShortcut(QKeySequence("Ctrl+2"), self)
        shortcut_time_5.activated.connect(lambda: self.set_time_from_button("05:00"))

        shortcut_time_7 = QShortcut(QKeySequence("Ctrl+3"), self)
        shortcut_time_7.activated.connect(lambda: self.set_time_from_button("07:00"))

        shortcut_time_10 = QShortcut(QKeySequence("Ctrl+4"), self)
        shortcut_time_10.activated.connect(lambda: self.set_time_from_button("10:00"))

        # Режимы
        shortcut_mode_down = QShortcut(QKeySequence("Ctrl+D"), self)
        shortcut_mode_down.activated.connect(lambda: self.set_timer_mode(TimerMode.COUNTDOWN))

        shortcut_mode_up = QShortcut(QKeySequence("Ctrl+U"), self)
        shortcut_mode_up.activated.connect(lambda: self.set_timer_mode(TimerMode.COUNTUP))

        shortcut_mode_both = QShortcut(QKeySequence("Ctrl+B"), self)
        shortcut_mode_both.activated.connect(lambda: self.set_timer_mode(TimerMode.BOTH))

        shortcut_next_stage = QShortcut(QKeySequence("Ctrl+N"), self)
        shortcut_next_stage.activated.connect(self.on_next_stage_hotkey)

        shortcut_prev_stage = QShortcut(QKeySequence("Ctrl+P"), self)
        shortcut_prev_stage.activated.connect(self.on_previous_stage_hotkey)

        shortcut_start_stage = QShortcut(QKeySequence("Ctrl+E"), self)
        shortcut_start_stage.activated.connect(self.on_start_stage_hotkey)

    def load_settings(self):
        """Загрузка настроек"""
        normal_color, warning_color, overtime_color = self.settings.load_colors()
        self.normal_bg_color = normal_color
        self.warning_bg_color = warning_color
        self.overtime_bg_color = overtime_color

        mode_str = self.settings.load_timer_mode()
        if mode_str == TimerMode.COUNTUP.value:
            self.timer_engine.set_mode(TimerMode.COUNTUP)
        elif mode_str == TimerMode.BOTH.value:
            self.timer_engine.set_mode(TimerMode.BOTH)
        else:
            self.timer_engine.set_mode(TimerMode.COUNTDOWN)

        sound_enabled = self.settings.load_sound_enabled()
        self.sound_manager.set_enabled(sound_enabled)

        warning_time = self.settings.load_warning_time()
        if self.timer_engine:
            self.timer_engine.warning_threshold = warning_time * 1000

        self.sound_manager.load_sounds()

        self.timer_label.setStyleSheet(f"""
            #timerLabel {{
                background-color: {self.normal_bg_color};
                color: {self.normal_text_color};
                border-radius: 10px;
            }}
        """)

        self.transparent_mode = self.settings.load_transparent_mode()
        self.update_display_mode()

        # === ВОССТАНОВЛЕНИЕ СЦЕНАРИЯ ===
        saved_script_id = self.settings.load_current_script_id()
        if saved_script_id:
            script_data = self.db_manager.get_script_with_stages(saved_script_id)
            if script_data:
                self.load_script_from_db(script_data)

    def update_display_mode(self):
        """Обновление отображения в зависимости от режима таймера"""
        if self.timer_engine.mode == TimerMode.COUNTDOWN:
            self.secondary_timer_label.hide()
            self.timer_label.base_font_size = 100
            if not self.timer_engine.is_running:
                current_time = self.time_input.text()
                if validate_time_input(current_time):
                    self.timer_label.setText(current_time)
        elif self.timer_engine.mode == TimerMode.COUNTUP:
            self.secondary_timer_label.hide()
            self.timer_label.base_font_size = 100
            if not self.timer_engine.is_running:
                self.timer_label.setText("00:00")
        else:  # BOTH
            self.secondary_timer_label.show()
            if not self.timer_engine.is_running:
                current_time = self.time_input.text()
                if validate_time_input(current_time):
                    self.timer_label.setText(current_time)
                    self.secondary_timer_label.setText("00:00")

    def update_pause_stats(self, count: int, total_seconds: int):
        """Обновление отображения статистики пауз"""
        if count > 0:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            text = f"Пауз: {count}  |  Общее время пауз: {minutes:02d}:{seconds:02d}"
            self.pause_stats_label.setText(text)
        else:
            self.pause_stats_label.setText("")

    def save_settings(self):
        """Сохранение текущих настроек"""
        self.settings.save_window_geometry(self.saveGeometry())
        self.settings.save_window_state(self.saveState())

        self.settings.save_colors(
            self.normal_bg_color,
            self.warning_bg_color,
            self.overtime_bg_color
        )

        self.settings.save_sound_enabled(self.sound_manager.enabled)

        if self.timer_engine:
            warning_seconds = self.timer_engine.warning_threshold // 1000
            self.settings.save_warning_time(warning_seconds)
            self.settings.save_timer_mode(self.timer_engine.mode.value)

    def _update_inter_stage_display(self):
        """Обновление отображения времени ожидания между этапами"""
        if self.inter_stage_pause_start:
            elapsed = int(time.time() - self.inter_stage_pause_start)
            pause_duration = self.settings.settings.value("ppt/pause_duration", 30, type=int)
            remaining = max(0, pause_duration - elapsed)

            self.pause_stats_label.setText(
                f"⏸️ Пауза перед следующим этапом: {remaining} сек"
            )

            if remaining <= 0 and elapsed > 0:
                self.inter_stage_timer.stop()
                self.inter_stage_pause_start = None
                self.pause_stats_label.setText("")
                print("🚀 Пауза закончилась, запускаем этап")
                self._auto_start_next_stage()
    def on_time_input_changed(self, text):
        """Обработка изменения ввода времени с умным форматированием"""
        if not text:
            return

        filtered_text = ''
        for char in text:
            if char.isdigit() or char == ':':
                filtered_text += char

        if filtered_text != text:
            self.time_input.blockSignals(True)
            self.time_input.setText(filtered_text)
            self.time_input.setCursorPosition(len(filtered_text))
            self.time_input.blockSignals(False)
            text = filtered_text

        cursor_pos = self.time_input.cursorPosition()

        if text.count(':') > 1:
            first_colon = text.find(':')
            before = text[:first_colon + 1]
            after = text[first_colon + 1:].replace(':', '')
            text = before + after

        if ':' in text:
            parts = text.split(':')
            if len(parts) > 2:
                text = parts[0] + ':' + parts[1]
                parts = text.split(':')
        else:
            if len(text) >= 2 and text != "0":
                text = text[:2] + ':' + text[2:]
                parts = text.split(':')
            else:
                parts = [text]

        minutes = parts[0]
        if len(minutes) > 2:
            minutes = minutes[-2:]

        if len(parts) > 1:
            seconds = parts[1]
            if len(seconds) > 2:
                seconds = seconds[-2:]

            try:
                sec_int = int(seconds)
                if sec_int > 59:
                    seconds = "59"
                elif sec_int < 0:
                    seconds = "00"
            except:
                seconds = "00"

            text = minutes + ':' + seconds
        else:
            text = minutes

        if text != self.time_input.text():
            self.time_input.blockSignals(True)
            self.time_input.setText(text)

            new_cursor_pos = min(cursor_pos, len(text))
            self.time_input.setCursorPosition(new_cursor_pos)
            self.time_input.blockSignals(False)

        if validate_time_input(text):
            self.last_set_time = text
            self.reset_color_to_normal()

            if self.timer_engine and not self.timer_engine.is_running:
                self.timer_engine.set_time(time_str_to_ms(text))

                if self.timer_engine.mode == TimerMode.COUNTUP:
                    self.timer_label.setText("00:00")
                elif self.timer_engine.mode == TimerMode.COUNTDOWN:
                    self.timer_label.setText(text)
                else:
                    self.timer_label.setText(text)
                    self.secondary_timer_label.setText("00:00")

    def toggle_timer(self):
        """Переключение старт/пауза"""
        if not self.timer_engine.is_running:
            # Останавливаем отсчёт паузы между этапами при старте
            if self.inter_stage_timer.isActive():
                self.inter_stage_timer.stop()
                if self.inter_stage_pause_start:
                    pause_duration = int((time.time() - self.inter_stage_pause_start) * 1000)
                    self.total_inter_stage_pause_ms += pause_duration
                    self.inter_stage_pause_start = None
                self.pause_stats_label.setText("")

            current_time = self.time_input.text()

            if validate_time_input(current_time):
                self.last_set_time = current_time
                self.reset_color_to_normal()

                duration_ms = time_str_to_ms(current_time)

                if not self.timer_engine.isRunning():
                    self.timer_engine.start()

                self.timer_engine.start_timer(duration_ms)

                if self.timer_engine.mode == TimerMode.COUNTUP:
                    self.timer_label.setText("00:00")
                elif self.timer_engine.mode == TimerMode.COUNTDOWN:
                    self.timer_label.setText(current_time)
                else:
                    self.timer_label.setText(current_time)
                    self.secondary_timer_label.setText("00:00")
            else:
                QMessageBox.warning(self, "Ошибка",
                                    "Некорректный формат времени!\nИспользуйте ММ:СС")
        else:
            if self.timer_engine.is_paused:
                # Возобновляем таймер — останавливаем отображение паузы
                self.pause_display_timer.stop()
                self.current_pause_start = None
                self.timer_engine.resume_timer()
            else:
                # Ставим на паузу — запускаем отображение
                self.timer_engine.pause_timer()
                self.current_pause_start = time.time()
                self.pause_display_timer.start(100)  # обновление каждые 0.5 сек

    def toggle_compact(self):
        """Переключение компактного режима"""
        if self.compact_window is None or not self.compact_window.isVisible():
            self.show_compact()
        else:
            self.hide_compact()

    def show_compact(self):
        """Показать компактное окно"""
        if self.compact_window is not None:
            try:
                self.compact_window.close()
            except:
                pass
            self.compact_window = None

        # Закрываем окно настроек, если оно открыто
        if self.settings_window:
            try:
                self.settings_window.parent_window = None
                self.settings_window.close()
            except:
                pass
            self.settings_window = None

        # Закрываем окно статистики, если оно открыто
        if hasattr(self, 'statistics_window') and self.statistics_window:
            try:
                self.statistics_window.close()
            except:
                pass
            self.statistics_window = None

        self.compact_window = CompactWindow()
        self.compact_window.closed.connect(self.on_compact_closed)
        self.compact_window.toggle_full.connect(self.toggle_compact)

        # Основные сигналы
        self.compact_window.toggle_timer.connect(self.toggle_timer)
        self.compact_window.reset_timer.connect(self.on_reset_timer)
        self.compact_window.finish_presentation.connect(self.finish_presentation)
        self.compact_window.show_settings.connect(self.show_settings)
        self.compact_window.show_statistics.connect(self.toggle_statistics)

        # Быстрое время
        self.compact_window.quick_time_3.connect(lambda: self.set_time_from_button("03:00"))
        self.compact_window.quick_time_5.connect(lambda: self.set_time_from_button("05:00"))
        self.compact_window.quick_time_7.connect(lambda: self.set_time_from_button("07:00"))
        self.compact_window.quick_time_10.connect(lambda: self.set_time_from_button("10:00"))

        # Режимы
        self.compact_window.mode_countdown.connect(lambda: self.set_timer_mode(TimerMode.COUNTDOWN))
        self.compact_window.mode_countup.connect(lambda: self.set_timer_mode(TimerMode.COUNTUP))
        self.compact_window.mode_both.connect(lambda: self.set_timer_mode(TimerMode.BOTH))

        # Прозрачность
        self.compact_window.toggle_transparent_mode.connect(self.toggle_transparent_mode)

        # Настройки прозрачности компактного окна
        compact_opacity = self.settings.load_compact_opacity()
        self.compact_window.set_opacity(compact_opacity / 100.0)

        # Восстановление геометрии или установка по умолчанию
        saved_geometry = self.settings.load_compact_window_geometry()
        if saved_geometry:
            self.compact_window.set_geometry_from_saved(saved_geometry)
        else:
            screen = self.compact_window.screen().availableGeometry()
            self.compact_window.setGeometry(
                screen.width() - self.compact_window.default_width - 20,
                50,
                self.compact_window.default_width,
                self.compact_window.default_height
            )

        # Обновляем отображение времени
        if self.timer_engine:
            if self.timer_engine.current_phase == TimerEngine.PHASE_NORMAL:
                bg_color = self.normal_bg_color
                text_color = self.normal_text_color
            elif self.timer_engine.current_phase == TimerEngine.PHASE_WARNING:
                bg_color = self.warning_bg_color
                text_color = "#000000"
            else:
                bg_color = self.overtime_bg_color
                text_color = "#FFFFFF"
        else:
            bg_color = self.normal_bg_color
            text_color = self.normal_text_color

        main_time = self.timer_label.text()

        if self.timer_engine and self.timer_engine.mode == TimerMode.BOTH and not self.secondary_timer_label.isHidden():
            secondary_time = self.secondary_timer_label.text().replace('+', '')
            display_text = f"{main_time} / {secondary_time}"
        else:
            display_text = main_time

        if self.transparent_mode:
            self.compact_window.update_display(display_text, "transparent", bg_color)
        else:
            self.compact_window.update_display(display_text, bg_color, text_color)

        self.compact_window.show()
        self.hide()

    def hide_compact(self):
        """Скрыть компактное окно"""
        if self.compact_window:
            geometry = self.compact_window.get_geometry()
            self.settings.save_compact_window_geometry(
                geometry.x(), geometry.y(), geometry.width(), geometry.height()
            )
            self.compact_window.close()
            self.compact_window = None

        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def on_compact_closed(self):
        """Обработка закрытия компактного окна"""
        if self.compact_window:
            try:
                geometry = self.compact_window.get_geometry()
                self.settings.save_compact_window_geometry(
                    geometry.x(), geometry.y(), geometry.width(), geometry.height()
                )
            except:
                pass
            self.compact_window.deleteLater()
            self.compact_window = None

        self.show()
        self.raise_()
        self.activateWindow()

    def show_settings(self):
        """Открыть / закрыть окно настроек по Ctrl+S"""
        try:
            if hasattr(self, "settings_window") and self.settings_window:
                if self.settings_window.isVisible():
                    self.settings_window.close()
                    self.settings_window = None
                    return
                else:
                    self.settings_window.deleteLater()
                    self.settings_window = None
        except RuntimeError:
            self.settings_window = None

        from ui.settings_window import SettingsWindow
        self.settings_window = SettingsWindow(parent=None)
        self.settings_window.set_parent_window(self)  # ← вызываем метод
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def closeEvent(self, event):
        """Обработка закрытия приложения - закрываем все окна"""
        # Сохраняем настройки главного окна
        self.save_settings()

        # Закрываем все дочерние окна
        if self.settings_window:
            try:
                if hasattr(self.settings_window, 'parent_window'):
                    self.settings_window.parent_window = None
                self.settings_window.close()
                self.settings_window.deleteLater()
            except:
                pass
            self.settings_window = None

        # ✅ ДОБАВИТЬ: Закрываем окно настроек PowerPoint
        if hasattr(self, 'ppt_settings_window') and self.ppt_settings_window:
            try:
                self.ppt_settings_window.close()
                self.ppt_settings_window.deleteLater()
            except:
                pass
            self.ppt_settings_window = None

        if self.compact_window:
            try:
                self.compact_window.close()
                self.compact_window.deleteLater()
            except:
                pass
            self.compact_window = None

        if hasattr(self, 'statistics_window') and self.statistics_window:
            try:
                self.statistics_window.close()
                self.statistics_window.deleteLater()
            except:
                pass
            self.statistics_window = None

        if hasattr(self, 'script_editor') and self.script_editor:
            try:
                self.script_editor.close()
                self.script_editor.deleteLater()
            except:
                pass
            self.script_editor = None

        # Очищаем движок таймера
        if self.timer_engine:
            try:
                self.timer_engine.cleanup()
            except:
                pass

        # Очищаем звуковой менеджер
        if self.sound_manager:
            try:
                self.sound_manager.cleanup()
            except:
                pass

        event.accept()

    def cleanup_resources(self):
        """Очистка ресурсов приложения"""
        # Сохраняем настройки
        try:
            self.save_settings()
        except:
            pass

        # Очищаем движок таймера
        if self.timer_engine:
            try:
                self.timer_engine.cleanup()
            except:
                pass

        # Очищаем звуковой менеджер
        if self.sound_manager:
            try:
                self.sound_manager.cleanup()
            except:
                pass
    def update_timer_display(self, main_time_str: str, secondary_time_str: str = ""):
        """Обновление отображения таймера"""
        self.timer_label.setText(main_time_str)

        if self.timer_engine.mode == TimerMode.BOTH:
            if secondary_time_str:
                self.secondary_timer_label.setText(secondary_time_str)
            self.secondary_timer_label.show()
        else:
            self.secondary_timer_label.hide()

        if self.compact_window and self.compact_window.isVisible():
            if self.timer_engine:
                if self.timer_engine.current_phase == TimerEngine.PHASE_NORMAL:
                    bg_color = self.normal_bg_color
                    text_color = self.normal_text_color
                elif self.timer_engine.current_phase == TimerEngine.PHASE_WARNING:
                    bg_color = self.warning_bg_color
                    text_color = "#000000"
                else:
                    bg_color = self.overtime_bg_color
                    text_color = "#FFFFFF"
            else:
                bg_color = self.normal_bg_color
                text_color = self.normal_text_color

            if self.timer_engine.mode == TimerMode.BOTH and secondary_time_str:
                display_text = f"{main_time_str} / {secondary_time_str}"
            else:
                display_text = main_time_str

            if self.transparent_mode:
                self.compact_window.update_display(display_text, "transparent", bg_color)
            else:
                self.compact_window.update_display(display_text, bg_color, text_color)

    def on_phase_changed(self, phase):
        """Обработка смены фазы таймера"""
        if phase == TimerEngine.PHASE_WARNING:
            self.sound_manager.play_warning()
        elif phase == TimerEngine.PHASE_OVERTIME:
            current_time = self.time_input.text()
            if validate_time_input(current_time):
                self.last_set_time = current_time
            self.sound_manager.play_final()

        if phase == TimerEngine.PHASE_NORMAL:
            bg_color = self.normal_bg_color
            text_color = self.normal_text_color
        elif phase == TimerEngine.PHASE_WARNING:
            bg_color = self.warning_bg_color
            text_color = "#000000"
        else:
            bg_color = self.overtime_bg_color
            text_color = "#FFFFFF"

        # ГЛАВНОЕ ОКНО - ВСЕГДА обычный стиль (игнорируем transparent_mode)
        self.timer_label.setStyleSheet(f"""
            #timerLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 10px;
            }}
        """)

        # КОМПАКТНОЕ ОКНО - работает как раньше
        if self.compact_window and self.compact_window.isVisible():
            main_time = self.timer_label.text()
            if self.timer_engine.mode == TimerMode.BOTH and not self.secondary_timer_label.isHidden():
                secondary_time = self.secondary_timer_label.text().replace('+', '')
                display_text = f"{main_time} / {secondary_time}"
            else:
                display_text = main_time

            if self.transparent_mode:
                self.compact_window.update_display(display_text, "transparent", bg_color)
            else:
                self.compact_window.update_display(display_text, bg_color, text_color)

    def on_time_is_up(self):
        """Обработка окончания времени"""
        self.sound_manager.play_final()

    def on_timer_state_changed(self, state):
        """Обработка изменения состояния таймера"""
        if state == "running":
            self.start_pause_btn.setText("ПАУЗА")
            self.start_pause_btn.setStyleSheet(PAUSE_BUTTON)

        elif state == "paused":
            self.start_pause_btn.setText("ПРОДОЛЖ.")
            self.start_pause_btn.setStyleSheet(RESUME_BUTTON)

        else:
            self.start_pause_btn.setText("СТАРТ")
            self.start_pause_btn.setStyleSheet(START_BUTTON)

    def set_time_from_button(self, time_str):
        """Установка времени из кнопки"""
        self.time_input.setText(time_str)
        self.last_set_time = time_str

        self.reset_color_to_normal()

        if self.timer_engine and not self.timer_engine.is_running:
            self.timer_engine.set_time(time_str_to_ms(time_str))

            if self.timer_engine.mode == TimerMode.COUNTUP:
                self.timer_label.setText("00:00")
            elif self.timer_engine.mode == TimerMode.COUNTDOWN:
                self.timer_label.setText(time_str)
            else:
                self.timer_label.setText(time_str)
                self.secondary_timer_label.setText("00:00")

    def on_reset_timer(self):
        """Сброс таймера (с учётом сценария)"""
        if not self.timer_engine:
            return

        # === Останавливаем таймер отображения текущей паузы ===
        self.pause_display_timer.stop()
        self.current_pause_start = None

        # === РЕЖИМ СЦЕНАРИЯ ===
        if self.current_script:
            # Если таймер не запущен и этап уже был сброшен — сбрасываем весь сценарий
            if not self.timer_engine.is_running and self.stage_already_reset:
                self._reset_full_script()
                return

            # Если таймер не запущен И выступление завершено — сбрасываем весь сценарий
            if not self.timer_engine.is_running and not self.stage_stats_list:
                self._reset_full_script()
                return

            # Иначе — сбрасываем только текущий этап
            self._reset_current_stage()
            return

        # === ОБЫЧНЫЙ РЕЖИМ ===
        current_time = self.time_input.text()

        if validate_time_input(current_time):
            self.last_set_time = current_time
            self.timer_engine.reset_timer()
            self.timer_engine.set_time(time_str_to_ms(current_time))
            self.reset_color_to_normal()
            self.last_pause_stats_message = ""
            self.pause_stats_label.setText("")  # <-- очищаем текст паузы

            if self.timer_engine.mode == TimerMode.COUNTUP:
                self.timer_label.setText("00:00")
            elif self.timer_engine.mode == TimerMode.COUNTDOWN:
                self.timer_label.setText(current_time)
            else:
                self.timer_label.setText(current_time)
                self.secondary_timer_label.setText("00:00")
        else:
            QMessageBox.warning(self, "Ошибка",
                                "Некорректное время для сброса!\nИспользуйте ММ:СС")

    def reset_color_to_normal(self):
        """Сброс цвета таймера на нормальный (зеленый)"""
        # ГЛАВНОЕ ОКНО - ВСЕГДА обычный стиль
        self.timer_label.setStyleSheet(f"""
            #timerLabel {{
                background-color: {self.normal_bg_color};
                color: {self.normal_text_color};
                border-radius: 10px;
            }}
        """)

        # КОМПАКТНОЕ ОКНО - работает как раньше
        if self.compact_window and self.compact_window.isVisible():
            main_time = self.timer_label.text()
            if self.timer_engine and self.timer_engine.mode == TimerMode.BOTH and not self.secondary_timer_label.isHidden():
                secondary_time = self.secondary_timer_label.text().replace('+', '')
                display_text = f"{main_time} / {secondary_time}"
            else:
                display_text = main_time

            if self.transparent_mode:
                self.compact_window.update_display(display_text, "transparent", self.normal_bg_color)
            else:
                self.compact_window.update_display(display_text, self.normal_bg_color, self.normal_text_color)


    def finish_presentation(self):
        """Завершить выступление и сохранить статистику"""
        if self.is_ending_presentation:
            return
        self.is_ending_presentation = True

        try:
            # Сохраняем текущий этап
            if self.timer_engine and self.timer_engine.is_running:
                self._save_current_stage_stats()

            # Останавливаем все таймеры...
            if self.inter_stage_timer.isActive():
                self.inter_stage_timer.stop()
                if self.inter_stage_pause_start:
                    pause_duration = int((time.time() - self.inter_stage_pause_start) * 1000)
                    self.total_inter_stage_pause_ms += pause_duration
                    self.inter_stage_pause_start = None

            if self.pause_display_timer.isActive():
                self.pause_display_timer.stop()
                if self.current_pause_start and self.timer_engine and self.timer_engine.is_paused:
                    pause_duration = int((time.time() - self.current_pause_start) * 1000)
                    self.timer_engine.total_pause_duration_ms += pause_duration
                    self.timer_engine.pause_count += 1
                self.current_pause_start = None

            # Сохраняем статистику
            if self.stage_stats_list:
                total_actual = sum(s['actual_duration_ms'] for s in self.stage_stats_list)
                if total_actual > 0:
                    self._save_script_stats_to_db()
                    print(f"✅ Статистика сохранена: {len(self.stage_stats_list)} этапов, {total_actual // 1000}с")
            elif self.timer_engine:
                stats = self.timer_engine.finish_presentation()
                if stats and stats.get('actual_duration_ms', 0) > 0:
                    self._save_timer_stats_to_db(stats)
                    print(f"✅ Статистика сохранена: {stats['actual_duration_ms'] // 1000}с")

            # Останавливаем движок (но экран НЕ сбрасываем)
            if self.timer_engine:
                self.timer_engine.is_running = False
                self.timer_engine.is_paused = False

            # ЗАПУСКАЕМ ТАЙМЕР ЗАДЕРЖКИ (например, 8 секунд)
            delay_seconds = 8  # можно вынести в настройки
            self.reset_delay_timer.start(delay_seconds * 1000)
            print(f"⏳ Таймер завершён, результат будет показан {delay_seconds} секунд, затем сброс")

            # Перезапускаем PowerPoint мониторинг
            if not self.ppt_controller.isRunning():
                self.start_ppt_monitoring()

        except Exception as e:
            print(f"Ошибка в finish_presentation: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_ending_presentation = False


    def _show_script_statistics(self):
        """Показать статистику для режима сценария"""
        if not self.stage_stats_list:
            return

        # Суммируем статистику
        total_planned_ms = sum(s['planned_duration_ms'] for s in self.stage_stats_list)
        total_actual_ms = sum(s['actual_duration_ms'] for s in self.stage_stats_list)
        total_pauses = sum(s['pause_count'] for s in self.stage_stats_list)
        total_pause_ms = sum(s['pause_duration_ms'] for s in self.stage_stats_list)
        total_overtime_ms = sum(s['overtime_ms'] for s in self.stage_stats_list)

        # Формируем сообщение
        message = f"""📊 СТАТИСТИКА ВЫСТУПЛЕНИЯ

    🕐 ВРЕМЯ
         Запланировано: {self._ms_to_str(total_planned_ms)}
         Фактически: {self._ms_to_str(total_actual_ms)}
         Превышение: {self._ms_to_str(total_overtime_ms)}

    ⏸️ ПАУЗЫ
         Всего пауз: {total_pauses}
         Общее время пауз: {self._ms_to_str(total_pause_ms)}
         Перерыв между этапами: {self._ms_to_str(self.total_inter_stage_pause_ms)}

    📋 ЭТАПЫ"""

        for i, s in enumerate(self.stage_stats_list, 1):
            message += f"""
      {i}. {s['stage_name']}
          Длительность: {self._ms_to_str(s['actual_duration_ms'])} (план {self._ms_to_str(s['planned_duration_ms'])})
          Пауз: {s['pause_count']} ({self._ms_to_str(s['pause_duration_ms'])})"""

        # Сохраняем в БД
        self._save_script_statistics_to_db()

        QMessageBox.information(self, "Выступление завершено", message)

    def _show_timer_statistics(self, stats):
        """Показать статистику для обычного режима"""
        mode_names = {
            'countdown': 'Обратный отсчёт',
            'countup': 'Прямой отсчёт',
            'both': 'Двойной'
        }
        mode_display = mode_names.get(stats['mode'], stats['mode'])

        message = f"""📊 СТАТИСТИКА ВЫСТУПЛЕНИЯ

    🕐 ВРЕМЯ
         Запланировано: {stats['planned_duration_str']}
         Фактически: {stats['actual_duration_str']}
         Превышение: {stats['overtime_str']}

    ⏸️ ПАУЗЫ
         Всего пауз: {stats['pause_count']}
         Общее время пауз: {stats['total_pause_str']}

    📌 Режим: {mode_display}"""

        # Сохраняем в БД
        self._save_timer_statistics_to_db(stats)

        QMessageBox.information(self, "Выступление завершено", message)

    def _show_completion_statistics(self):
        """Показать статистику завершения (сценарий или обычный режим)"""
        if not self.stage_stats_list:
            return

        try:
            # Суммируем статистику только из реальных этапов
            valid_stages = [s for s in self.stage_stats_list if s['actual_duration_ms'] > 0]

            if not valid_stages and len(self.stage_stats_list) > 0:
                # Все этапы нулевые - возможно, сразу завершили
                QMessageBox.information(
                    self,
                    "Выступление завершено",
                    "Выступление не состоялось (нулевая длительность)."
                )
                return

            total_planned_ms = sum(s['planned_duration_ms'] for s in valid_stages)
            total_actual_ms = sum(s['actual_duration_ms'] for s in valid_stages)
            total_pauses = sum(s['pause_count'] for s in valid_stages)
            total_pause_ms = sum(s['pause_duration_ms'] for s in valid_stages)
            total_overtime_ms = sum(s['overtime_ms'] for s in valid_stages)

            # Формируем сообщение
            message = f"""📊 СТАТИСТИКА ВЫСТУПЛЕНИЯ

    🕐 ВРЕМЯ
         Запланировано: {self._format_time_ms(total_planned_ms)}
         Фактически: {self._format_time_ms(total_actual_ms)}
         Превышение: {self._format_time_ms(total_overtime_ms)}

    ⏸️ ПАУЗЫ
         Всего пауз: {total_pauses}
         Общее время пауз: {self._format_time_ms(total_pause_ms)}
         Перерыв между этапами: {self._format_time_ms(self.total_inter_stage_pause_ms)}

    📋 ЭТАПЫ"""

            for i, s in enumerate(valid_stages, 1):
                message += f"""
      {i}. {s['stage_name']}
          Длительность: {self._format_time_ms(s['actual_duration_ms'])} (план {self._format_time_ms(s['planned_duration_ms'])})
          Пауз: {s['pause_count']} ({self._format_time_ms(s['pause_duration_ms'])})"""

            # Сохраняем в БД только если есть реальные данные
            if total_actual_ms > 0:
                self._save_completion_statistics_to_db(valid_stages)

            QMessageBox.information(self, "Выступление завершено", message)

        except Exception as e:
            print(f"Ошибка при показе статистики сценария: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось показать статистику: {e}")

    def _show_timer_completion_statistics(self, stats):
        """Показать статистику для обычного режима"""
        try:
            # Проверяем, есть ли реальное время
            if stats.get('actual_duration_ms', 0) == 0:
                QMessageBox.information(self, "Информация", "Выступление не состоялось (нулевая длительность)")
                return

            mode_names = {
                'countdown': 'Обратный отсчёт',
                'countup': 'Прямой отсчёт',
                'both': 'Двойной'
            }
            mode_display = mode_names.get(stats.get('mode', ''), stats.get('mode', 'Неизвестно'))

            message = f"""📊 СТАТИСТИКА ВЫСТУПЛЕНИЯ

    🕐 ВРЕМЯ
         Запланировано: {stats.get('planned_duration_str', '00:00')}
         Фактически: {stats.get('actual_duration_str', '00:00')}
         Превышение: {stats.get('overtime_str', '00:00')}

    ⏸️ ПАУЗЫ
         Всего пауз: {stats.get('pause_count', 0)}
         Общее время пауз: {stats.get('total_pause_str', '00:00')}

    📌 Режим: {mode_display}"""

            # Сохраняем в БД
            self._save_timer_completion_statistics_to_db(stats)

            QMessageBox.information(self, "Выступление завершено", message)

        except Exception as e:
            print(f"Ошибка при показе статистики таймера: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось показать статистику: {e}")

    def _format_time_ms(self, ms: int) -> str:
        """Безопасное форматирование времени"""
        if ms is None or ms <= 0:
            return "00:00"
        try:
            seconds = abs(ms) // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            sign = "-" if ms < 0 else ""
            return f"{sign}{minutes:02d}:{seconds:02d}"
        except:
            return "00:00"

    def _save_completion_statistics_to_db(self, stages):
        """Сохранить статистику сценария в БД с проверками"""
        if not stages:
            return

        try:
            total_planned_ms = sum(s['planned_duration_ms'] for s in stages)
            total_actual_ms = sum(s['actual_duration_ms'] for s in stages)

            # Проверяем, что есть что сохранять
            if total_actual_ms == 0:
                print("Нет данных для сохранения в БД")
                return

            from datetime import datetime

            stats = {
                'script_id': self.current_script_id,
                'start_timestamp': datetime.now().isoformat(),
                'end_timestamp': datetime.now().isoformat(),
                'mode': self.timer_engine.mode.value if self.timer_engine else 'countdown',
                'warning_threshold_sec': self.timer_engine.warning_threshold // 1000 if self.timer_engine else 60,
                'pause_count': sum(s['pause_count'] for s in stages),
                'total_pause_ms': sum(s['pause_duration_ms'] for s in stages),
                'inter_stage_pause_ms': self.total_inter_stage_pause_ms,
                'planned_duration_ms': total_planned_ms,
                'actual_duration_ms': total_actual_ms,
                'overtime_ms': sum(s['overtime_ms'] for s in stages),
                'stages': stages.copy()
            }

            self.db_manager.add_presentation(stats)
            print(f"✅ Статистика сохранена в БД: {total_actual_ms // 1000} секунд")

        except Exception as e:
            print(f"Ошибка сохранения статистики в БД: {e}")
            import traceback
            traceback.print_exc()

    def _save_timer_completion_statistics_to_db(self, stats):
        """Сохранить статистику обычного режима в БД"""
        try:
            if stats.get('actual_duration_ms', 0) == 0:
                print("Нет данных для сохранения в БД")
                return

            self.db_manager.add_presentation(stats)
            print(f"✅ Статистика сохранена в БД")

        except Exception as e:
            print(f"Ошибка сохранения статистики в БД: {e}")
            import traceback
            traceback.print_exc()
    def _save_script_statistics_to_db(self):
        """Сохранить статистику сценария в БД"""
        if not self.stage_stats_list:
            return

        # Собираем общую статистику
        total_planned_ms = sum(s['planned_duration_ms'] for s in self.stage_stats_list)
        total_actual_ms = sum(s['actual_duration_ms'] for s in self.stage_stats_list)

        stats = {
            'script_id': self.current_script_id,
            'start_timestamp': self.timer_engine.presentation_start_time if self.timer_engine else datetime.now().isoformat(),
            'end_timestamp': datetime.now().isoformat(),
            'mode': self.timer_engine.mode.value if self.timer_engine else 'countdown',
            'warning_threshold_sec': self.timer_engine.warning_threshold // 1000 if self.timer_engine else 60,
            'pause_count': sum(s['pause_count'] for s in self.stage_stats_list),
            'total_pause_ms': sum(s['pause_duration_ms'] for s in self.stage_stats_list),
            'inter_stage_pause_ms': self.total_inter_stage_pause_ms,
            'planned_duration_ms': total_planned_ms,
            'actual_duration_ms': total_actual_ms,
            'overtime_ms': sum(s['overtime_ms'] for s in self.stage_stats_list),
            'stages': self.stage_stats_list.copy()
        }

        self.db_manager.add_presentation(stats)

    def _save_timer_statistics_to_db(self, stats):
        """Сохранить статистику обычного режима в БД"""
        self.db_manager.add_presentation(stats)

    def _reset_presentation_state(self):
        """Сбросить состояние выступления"""
        self.stage_stats_list = []
        self.total_inter_stage_pause_ms = 0
        self.inter_stage_pause_start = None

        if self.timer_engine:
            self.timer_engine.reset_timer()

    def _ms_to_str(self, ms: int) -> str:
        """Конвертирует миллисекунды в строку ММ:СС"""
        if ms <= 0:
            return "00:00"
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


    def save_presentation_stats(self, stats: dict):
        """Сохранение статистики выступления в JSON"""
        from datetime import datetime

        # Не перезаписываем start_timestamp и end_timestamp — они уже правильные
        stats['date'] = datetime.fromisoformat(stats['start_timestamp']).strftime("%Y-%m-%d")
        stats['time'] = datetime.fromisoformat(stats['start_timestamp']).strftime("%H:%M:%S")
        stats['timestamp'] = stats['end_timestamp']  # Для совместимости со старым форматом

        try:
            try:
                with open('presentation_stats.json', 'r', encoding='utf-8') as f:
                    all_stats = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                all_stats = []

            all_stats.append(stats)

            with open('presentation_stats.json', 'w', encoding='utf-8') as f:
                json.dump(all_stats, f, ensure_ascii=False, indent=2)

            print(f"Статистика сохранена: {stats['date']} {stats['time']}")

        except Exception as e:
            print(f"Ошибка сохранения статистики: {e}")

    def changeEvent(self, event):
        """Обработка изменения состояния окна"""
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized() and self.timer_engine and self.timer_engine.is_running:
                self.show_compact()
                event.ignore()
                return

        super().changeEvent(event)


    def toggle_transparent_mode(self):
        """Переключение прозрачного режима (горячая клавиша Ctrl+T)"""
        new_mode = not self.transparent_mode

        self.settings.save_transparent_mode(new_mode)
        self.transparent_mode = new_mode

        # Обновляем отображение в компактном окне (если открыто)
        if self.compact_window and self.compact_window.isVisible():
            if self.timer_engine:
                phase = self.timer_engine.current_phase
                if phase == TimerEngine.PHASE_NORMAL:
                    bg_color = self.normal_bg_color
                    text_color = self.normal_text_color
                elif phase == TimerEngine.PHASE_WARNING:
                    bg_color = self.warning_bg_color
                    text_color = "#000000"
                else:
                    bg_color = self.overtime_bg_color
                    text_color = "#FFFFFF"

                main_time = self.timer_label.text()
                if self.timer_engine.mode == TimerMode.BOTH and not self.secondary_timer_label.isHidden():
                    secondary_time = self.secondary_timer_label.text().replace('+', '')
                    display_text = f"{main_time} / {secondary_time}"
                else:
                    display_text = main_time

                if new_mode:
                    self.compact_window.update_display(display_text, "transparent", bg_color)
                else:
                    self.compact_window.update_display(display_text, bg_color, text_color)

        # Синхронизируем чекбокс в окне настроек, если оно открыто
        if self.settings_window and self.settings_window.isVisible():
            self.settings_window.transparent_checkbox.setChecked(new_mode)

    def set_timer_mode(self, mode):
        """Установка режима таймера"""
        if self.timer_engine:
            self.timer_engine.set_mode(mode)
            self.update_display_mode()

            # Обновляем компактное окно если открыто
            if self.compact_window and self.compact_window.isVisible():
                main_time = self.timer_label.text()
                if mode == TimerMode.BOTH and not self.secondary_timer_label.isHidden():
                    secondary_time = self.secondary_timer_label.text().replace('+', '')
                    display_text = f"{main_time} / {secondary_time}"
                else:
                    display_text = main_time

                if self.timer_engine.current_phase == TimerEngine.PHASE_NORMAL:
                    bg_color = self.normal_bg_color
                    text_color = self.normal_text_color
                elif self.timer_engine.current_phase == TimerEngine.PHASE_WARNING:
                    bg_color = self.warning_bg_color
                    text_color = "#000000"
                else:
                    bg_color = self.overtime_bg_color
                    text_color = "#FFFFFF"

                if self.transparent_mode:
                    self.compact_window.update_display(display_text, "transparent", bg_color)
                else:
                    self.compact_window.update_display(display_text, bg_color, text_color)

    def load_script_from_db(self, script_data: dict):
        """Загрузить сценарий из БД и применить к интерфейсу"""
        self.current_script = PresentationScript(name=script_data['name'])
        self.current_script_id = script_data['id']

        for stage_data in script_data['stages']:
            stage = PresentationStage(
                name=stage_data['name'],
                duration_ms=stage_data['planned_duration_ms']
            )
            self.current_script.add_stage(stage)

        self.current_script.start()
        self.stage_already_reset = False

        # Обновляем заголовок
        current_stage = self.current_script.get_current_stage()
        if current_stage:
            self.title_label.setText(f"{self.current_script.name}  ({current_stage.name})")

        # Устанавливаем время первого этапа
        first_stage = self.current_script.get_current_stage()
        if first_stage:
            time_str = first_stage.get_duration_str()
            self.time_input.setText(time_str)
            if self.timer_engine:
                self.timer_engine.set_time(first_stage.duration_ms)
                self.timer_label.setText(time_str)
                if self.timer_engine.mode == TimerMode.COUNTUP:
                    self.timer_label.setText("00:00")
                elif self.timer_engine.mode == TimerMode.COUNTDOWN:
                    self.timer_label.setText(time_str)
                else:
                    self.timer_label.setText(time_str)
                    self.secondary_timer_label.setText("00:00")

        self._set_script_mode(True)
        self._update_next_stage_button()

        # ДОБАВИТЬ ЭТИ СТРОКИ В КОНЦЕ МЕТОДА:
        # Сигнализируем об изменении сценария
        self.script_changed.emit()

    def clear_script(self):
        """Очистить сценарий — вернуться к обычному режиму"""
        # Останавливаем таймеры
        if self.inter_stage_timer.isActive():
            self.inter_stage_timer.stop()
        if self.pause_display_timer.isActive():
            self.pause_display_timer.stop()

        self.current_pause_start = None
        self.pause_stats_label.setText("")

        # Сохраняем последнее установленное время
        current_time = self.time_input.text()
        if validate_time_input(current_time):
            self.last_set_time = current_time

        # Сбрасываем сценарий
        self.current_script = None
        self.current_script_id = None
        self.stage_already_reset = False
        self.title_label.setText("ТАЙМЕР ВЫСТУПЛЕНИЯ")
        self._set_script_mode(False)

        # Восстанавливаем обычный режим
        self.time_input.setReadOnly(False)
        self.time_input.setText(self.last_set_time)

        if self.timer_engine:
            self.timer_engine.set_time(time_str_to_ms(self.last_set_time))
            if self.timer_engine.mode == TimerMode.COUNTUP:
                self.timer_label.setText("00:00")
            elif self.timer_engine.mode == TimerMode.COUNTDOWN:
                self.timer_label.setText(self.last_set_time)
            else:
                self.timer_label.setText(self.last_set_time)
                self.secondary_timer_label.setText("00:00")

        # ✅ ДОБАВИТЬ ЭТУ СТРОКУ
        self.script_changed.emit()

    def _reset_current_stage(self):
        """Сбросить только текущий этап сценария"""
        if not self.current_script:
            return

        stage = self.current_script.get_current_stage()
        if not stage:
            return

        # Сбрасываем таймер на время текущего этапа
        time_str = stage.get_duration_str()
        self.time_input.setText(time_str)

        if self.timer_engine:
            self.timer_engine.reset_timer()
            self.timer_engine.set_time(stage.duration_ms)

        self.reset_color_to_normal()
        self.last_pause_stats_message = ""

        if self.timer_engine.mode == TimerMode.COUNTUP:
            self.timer_label.setText("00:00")
        elif self.timer_engine.mode == TimerMode.COUNTDOWN:
            self.timer_label.setText(time_str)
        else:
            self.timer_label.setText(time_str)
            self.secondary_timer_label.setText("00:00")

        self.stage_already_reset = True

    def _reset_full_script(self):
        """Сбросить весь сценарий к первому этапу"""
        if not self.current_script:
            return

        # Останавливаем таймер отображения паузы между этапами
        self.inter_stage_timer.stop()
        # Останавливаем таймер отображения текущей паузы
        self.pause_display_timer.stop()
        self.current_pause_start = None
        self.pause_stats_label.setText("")

        # Сбрасываем статистику этапов
        self.stage_stats_list = []
        self.total_inter_stage_pause_ms = 0
        self.inter_stage_pause_start = None

        self.current_script.reset()
        self.current_script.start()
        self.stage_already_reset = False

        first_stage = self.current_script.get_current_stage()
        if first_stage:
            time_str = first_stage.get_duration_str()
            self.time_input.setText(time_str)

            if self.timer_engine:
                self.timer_engine.reset_timer()
                self.timer_engine.set_time(first_stage.duration_ms)

            self.title_label.setText(f"{self.current_script.name}  ({first_stage.name})")
            self.reset_color_to_normal()
            self.last_pause_stats_message = ""

            if self.timer_engine.mode == TimerMode.COUNTUP:
                self.timer_label.setText("00:00")
            elif self.timer_engine.mode == TimerMode.COUNTDOWN:
                self.timer_label.setText(time_str)
            else:
                self.timer_label.setText(time_str)
                self.secondary_timer_label.setText("00:00")

        self._update_next_stage_button()

    def _set_script_mode(self, active: bool):
        """Переключение между режимом сценария и обычным"""
        # Показываем/скрываем кнопки быстрого времени
        for btn in self.quick_buttons:
            btn.setVisible(not active)

        # Показываем/скрываем кнопку "Следующий этап"
        self.next_stage_btn.setVisible(active)

        # Блокируем/разблокируем поле ввода времени
        self.time_input.setReadOnly(active)

        # Сохраняем состояние в настройках
        if active and self.current_script_id:
            self.settings.save_current_script_id(self.current_script_id)
        elif not active:
            self.settings.save_current_script_id(None)


    def on_next_stage(self):
        """Переход к следующему этапу сценария"""
        if not self.current_script:
            return

        # ⚠️ ЗАЩИТА ОТ ПОВТОРНОГО ВХОДА
        if self.current_script.is_finished():
            print("⚠️ Сценарий завершён, пропускаем next_stage")
            return

        # Сохраняем текущую паузу если есть
        if self.pause_display_timer.isActive():
            self.pause_display_timer.stop()
            if self.current_pause_start and self.timer_engine:
                pause_duration = int((time.time() - self.current_pause_start) * 1000)
                self.timer_engine.total_pause_duration_ms += pause_duration
                self.timer_engine.pause_count += 1
            self.current_pause_start = None

        # Сохраняем статистику предыдущего этапа
        self._save_current_stage_stats()

        if self.timer_engine:
            self.timer_engine.reset_timer()

        # Переходим к следующему этапу
        if self.current_script.next_stage():
            stage = self.current_script.get_current_stage()
            if stage:
                self.stage_already_reset = False
                self.title_label.setText(f"{self.current_script.name}  ({stage.name})")
                time_str = stage.get_duration_str()
                self.time_input.setText(time_str)

                if self.timer_engine:
                    self.timer_engine.set_time(stage.duration_ms)

                self.timer_label.setText(time_str)
                if self.timer_engine and self.timer_engine.mode == TimerMode.COUNTUP:
                    self.timer_label.setText("00:00")
                elif self.timer_engine and self.timer_engine.mode == TimerMode.BOTH:
                    self.secondary_timer_label.setText("00:00")

                self.reset_color_to_normal()
                self._update_next_stage_button()

                # Проверяем настройки паузы
                pause_enabled = self.settings.settings.value("ppt/pause_enabled", False, type=bool)

                print(f"📋 Этап: {stage.name} | Пауза между этапами: {'ВКЛ' if pause_enabled else 'ВЫКЛ'}")

                if pause_enabled:
                    pause_duration = self.settings.settings.value("ppt/pause_duration", 30, type=int)
                    self.inter_stage_pause_start = time.time()
                    self.inter_stage_timer.start(100)
                    print(f"⏸️ Пауза {pause_duration} сек перед этапом '{stage.name}'")
                else:
                    QTimer.singleShot(300, self._auto_start_next_stage)
                    print(f"➡️ Автозапуск этапа '{stage.name}'")
        else:
            # Последний этап завершён
            print("🏁 Последний этап завершён")
            self.finish_presentation()

    def _auto_start_next_stage(self):
        """Автоматически запустить таймер для следующего этапа"""
        if self.current_script and not self.timer_engine.is_running:
            print("🚀 Автозапуск следующего этапа")
            self.toggle_timer()

    # Добавить новый метод:
    def _save_current_stage_stats(self):
        """Сохранить статистику текущего этапа ВСЕГДА (даже если 0 секунд)"""
        if not self.current_script or not self.timer_engine:
            return

        stage = self.current_script.get_current_stage()
        if not stage:
            return

        # Если таймер на паузе — фиксируем текущую паузу
        total_pause_ms = self.timer_engine.total_pause_duration_ms
        total_pause_count = self.timer_engine.pause_count

        if self.timer_engine.is_paused and self.current_pause_start:
            try:
                current_pause_duration = int((time.time() - self.current_pause_start) * 1000)
                total_pause_ms += current_pause_duration
                total_pause_count += 1
            except:
                pass

        # Собираем статистику (даже если всё нули)
        actual_ms = self.timer_engine.total_elapsed_ms

        stats = {
            "stage_name": stage.name,
            "planned_duration_ms": self.timer_engine.duration_ms,
            "actual_duration_ms": actual_ms,
            "overtime_ms": max(0, actual_ms - self.timer_engine.duration_ms),
            "pause_count": total_pause_count,
            "pause_duration_ms": total_pause_ms
        }

        self.stage_stats_list.append(stats)

        print(f"✅ Этап сохранён: {stage.name} | "
              f"Факт: {actual_ms // 1000}с | "
              f"План: {self.timer_engine.duration_ms // 1000}с | "
              f"Пауз: {stats['pause_count']}")

    # Добавить новый метод:
    def _save_presentation_with_stages(self, stats: dict):
        """Сохранить выступление с разбивкой по этапам в БД"""
        from datetime import datetime
        import time as time_module

        # Не перезаписываем start_timestamp и end_timestamp — они уже пришли из TimerEngine
        stats['warning_threshold_sec'] = self.timer_engine.warning_threshold // 1000
        stats['script_id'] = self.current_script_id
        stats['inter_stage_pause_ms'] = self.total_inter_stage_pause_ms

        # Добавляем этапы
        stats['stages'] = self.stage_stats_list.copy()

        # Сохраняем в БД с повторными попытками
        max_retries = 5
        for attempt in range(max_retries):
            try:
                presentation_id = self.db_manager.add_presentation(stats)
                print(f"✅ Выступление сохранено в БД, ID: {presentation_id}")
                print(f"   Этапов: {len(self.stage_stats_list)}")
                print(f"   Пауз между этапами: {self.total_inter_stage_pause_ms // 1000}с")
                return presentation_id
            except Exception as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⏳ БД заблокирована, попытка {attempt + 1}/{max_retries}...")
                    time_module.sleep(0.5)
                else:
                    print(f"❌ Ошибка сохранения в БД: {e}")
                    return None


    def _update_next_stage_button(self):
        """Обновить состояние кнопки «След. этап» в зависимости от этапа"""
        if not self.current_script:
            return

        is_last = self.current_script.is_finished()

        self.next_stage_btn.setEnabled(not is_last)

        if is_last:
            self.next_stage_btn.setToolTip(
                "Это последний этап.\nЗавершите выступление кнопкой «✓» в панели управления"
            )
            self.next_stage_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95A5A6;
                    color: #CCCCCC;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 4px;
                }
            """)
        else:
            self.next_stage_btn.setToolTip("Перейти к следующему этапу сценария")
            self.next_stage_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498DB;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 4px;
                }
                QPushButton:hover { background-color: #2980B9; }
                QPushButton:pressed { background-color: #1F6DA0; }
            """)

    def _update_pause_display(self):
        """Обновление отображения текущей паузы"""
        if self.current_pause_start:
            elapsed = int(time.time() - self.current_pause_start)
            minutes = elapsed // 60
            seconds = elapsed % 60
            # Считаем общее количество пауз (текущая + уже завершённые)
            total_count = self.timer_engine.pause_count + 1 if self.timer_engine else 1
            # Общее время пауз (завершённые + текущая)
            total_ms = (self.timer_engine.total_pause_duration_ms if self.timer_engine else 0) + (elapsed * 1000)
            total_min = total_ms // 60000
            total_sec = (total_ms % 60000) // 1000
            self.pause_stats_label.setText(
                f"Пауз: {total_count}  |  Общее время пауз: {total_min:02d}:{total_sec:02d}"
            )


    def toggle_statistics(self):
        """Открыть / закрыть окно статистики"""
        try:
            # Если окно уже существует и видимо — закрываем
            if hasattr(self, 'statistics_window') and self.statistics_window:
                if self.statistics_window.isVisible():
                    self.statistics_window.close()
                    self.statistics_window = None
                    return
        except RuntimeError:
            # Qt уже удалил объект
            self.statistics_window = None

        # Создаём новое окно
        try:
            from ui.statistics_window import StatisticsWindow

            self.statistics_window = StatisticsWindow(
                self.db_manager,
                parent=None
            )
            self.statistics_window.show()
            self.statistics_window.raise_()
            self.statistics_window.activateWindow()
        except Exception as e:
            print(f"Ошибка при открытии статистики: {e}")

    def _show_and_save_script_stats(self):
        """Показать и сохранить статистику сценария (даже если всё нули)"""
        if not self.stage_stats_list:
            # Пустой сценарий - создаем запись что было 0 этапов
            self._save_empty_script_stats()
            QMessageBox.information(self, "Выступление завершено",
                                    "Сценарий загружен, но ни один этап не был завершён.")
            return

        # Суммируем статистику
        total_planned_ms = sum(s['planned_duration_ms'] for s in self.stage_stats_list)
        total_actual_ms = sum(s['actual_duration_ms'] for s in self.stage_stats_list)
        total_pauses = sum(s['pause_count'] for s in self.stage_stats_list)
        total_pause_ms = sum(s['pause_duration_ms'] for s in self.stage_stats_list)
        total_overtime_ms = sum(s['overtime_ms'] for s in self.stage_stats_list)

        # Формируем сообщение
        message = f"""📊 СТАТИСТИКА ВЫСТУПЛЕНИЯ

    🕐 ВРЕМЯ
         Запланировано: {self._format_time_ms(total_planned_ms)}
         Фактически: {self._format_time_ms(total_actual_ms)}
         Превышение: {self._format_time_ms(total_overtime_ms)}

    ⏸️ ПАУЗЫ
         Всего пауз: {total_pauses}
         Общее время пауз: {self._format_time_ms(total_pause_ms)}
         Перерыв между этапами: {self._format_time_ms(self.total_inter_stage_pause_ms)}

    📋 ЭТАПЫ"""

        for i, s in enumerate(self.stage_stats_list, 1):
            message += f"""
      {i}. {s['stage_name']}
          Длительность: {self._format_time_ms(s['actual_duration_ms'])} (план {self._format_time_ms(s['planned_duration_ms'])})
          Пауз: {s['pause_count']} ({self._format_time_ms(s['pause_duration_ms'])})"""

        # Сохраняем ВСЕГДА, даже если нули
        self._save_script_stats_to_db()

        QMessageBox.information(self, "Выступление завершено", message)

    def _show_and_save_timer_stats(self, stats):
        """Показать и сохранить статистику обычного режима (даже если нули)"""
        mode_names = {
            'countdown': 'Обратный отсчёт',
            'countup': 'Прямой отсчёт',
            'both': 'Двойной'
        }
        mode_display = mode_names.get(stats.get('mode', ''), stats.get('mode', 'Неизвестно'))

        message = f"""📊 СТАТИСТИКА ВЫСТУПЛЕНИЯ

    🕐 ВРЕМЯ
         Запланировано: {stats.get('planned_duration_str', '00:00')}
         Фактически: {stats.get('actual_duration_str', '00:00')}
         Превышение: {stats.get('overtime_str', '00:00')}

    ⏸️ ПАУЗЫ
         Всего пауз: {stats.get('pause_count', 0)}
         Общее время пауз: {stats.get('total_pause_str', '00:00')}

    📌 Режим: {mode_display}"""

        # Сохраняем ВСЕГДА
        self._save_timer_stats_to_db(stats)

        QMessageBox.information(self, "Выступление завершено", message)

    def _show_and_save_empty_stats(self):
        """Создаем и сохраняем пустую статистику (когда выступление даже не начиналось)"""
        from datetime import datetime

        empty_stats = {
            'planned_duration_ms': 0,
            'planned_duration_str': '00:00',
            'actual_duration_ms': 0,
            'actual_duration_str': '00:00',
            'overtime_ms': 0,
            'overtime_str': '00:00',
            'pause_count': 0,
            'total_pause_ms': 0,
            'total_pause_str': '00:00',
            'mode': self.timer_engine.mode.value if self.timer_engine else 'countdown',
            'start_timestamp': datetime.now().isoformat(),
            'end_timestamp': datetime.now().isoformat(),
            'script_id': self.current_script_id
        }

        # Добавляем пустые этапы если есть сценарий
        if self.current_script:
            empty_stats['stages'] = []
            for stage in self.current_script.stages:
                empty_stats['stages'].append({
                    "stage_name": stage.name,
                    "planned_duration_ms": stage.duration_ms,
                    "actual_duration_ms": 0,
                    "overtime_ms": 0,
                    "pause_count": 0,
                    "pause_duration_ms": 0
                })

        self.db_manager.add_presentation(empty_stats)

        QMessageBox.information(self, "Выступление завершено",
                                "Выступление не состоялось.\nСтатистика сохранена (нулевая).")

    def _save_script_stats_to_db(self):
        """Сохранить статистику сценария в БД (всегда)"""
        if not self.stage_stats_list and not self.current_script:
            return

        from datetime import datetime

        total_planned_ms = sum(s['planned_duration_ms'] for s in self.stage_stats_list)
        total_actual_ms = sum(s['actual_duration_ms'] for s in self.stage_stats_list)

        stats = {
            'script_id': self.current_script_id,
            'start_timestamp': self.timer_engine.presentation_start_time if self.timer_engine else datetime.now().isoformat(),
            'end_timestamp': datetime.now().isoformat(),
            'mode': self.timer_engine.mode.value if self.timer_engine else 'countdown',
            'warning_threshold_sec': self.timer_engine.warning_threshold // 1000 if self.timer_engine else 60,
            'pause_count': sum(s['pause_count'] for s in self.stage_stats_list),
            'total_pause_ms': sum(s['pause_duration_ms'] for s in self.stage_stats_list),
            'inter_stage_pause_ms': self.total_inter_stage_pause_ms,
            'planned_duration_ms': total_planned_ms,
            'actual_duration_ms': total_actual_ms,
            'overtime_ms': sum(s['overtime_ms'] for s in self.stage_stats_list),
            'stages': self.stage_stats_list.copy()
        }

        try:
            self.db_manager.add_presentation(stats)
            print(
                f"✅ Статистика сценария сохранена: {len(self.stage_stats_list)} этапов, всего {total_actual_ms // 1000}с")
        except Exception as e:
            print(f"Ошибка сохранения в БД: {e}")
            import traceback
            traceback.print_exc()

    def _save_timer_stats_to_db(self, stats):
        """Сохранить статистику обычного режима в БД (всегда)"""
        try:
            self.db_manager.add_presentation(stats)
            print(f"✅ Статистика обычного режима сохранена: {stats.get('actual_duration_ms', 0) // 1000}с")
        except Exception as e:
            print(f"Ошибка сохранения в БД: {e}")
            import traceback
            traceback.print_exc()

    def _format_time_ms(self, ms: int) -> str:
        """Форматирование времени (всегда возвращает строку)"""
        if ms is None:
            return "00:00"
        try:
            seconds = abs(ms) // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            sign = "-" if ms < 0 else ""
            return f"{sign}{minutes:02d}:{seconds:02d}"
        except:
            return "00:00"

    def _reset_after_finish(self):
        """Сброс состояния после завершения"""
        # ✅ ПЕРВАЯ СТРОКА - ОЧИЩАЕМ СПИСОК ЭТАПОВ
        self.stage_stats_list = []

        self.total_inter_stage_pause_ms = 0
        self.inter_stage_pause_start = None
        self.current_pause_start = None

        if self.pause_display_timer.isActive():
            self.pause_display_timer.stop()

        if self.inter_stage_timer.isActive():
            self.inter_stage_timer.stop()

        if self.timer_engine:
            self.timer_engine.reset_timer()

        self.pause_stats_label.setText("")

        if self.current_script:
            self.current_script.reset()
            self.current_script.start()
            self.stage_already_reset = False

            first_stage = self.current_script.get_current_stage()
            if first_stage:
                self.title_label.setText(f"{self.current_script.name}  ({first_stage.name})")
                time_str = first_stage.get_duration_str()
                self.time_input.setText(time_str)

                if self.timer_engine:
                    self.timer_engine.set_time(first_stage.duration_ms)

                if self.timer_engine and self.timer_engine.mode == TimerMode.COUNTUP:
                    self.timer_label.setText("00:00")
                else:
                    self.timer_label.setText(time_str)

                self._set_script_mode(True)
                self._update_next_stage_button()
                self.reset_color_to_normal()
        else:
            self.title_label.setText("ТАЙМЕР ВЫСТУПЛЕНИЯ")
            self._set_script_mode(False)
            self.time_input.setReadOnly(False)
            self.time_input.setText(self.last_set_time)

            if self.timer_engine:
                self.timer_engine.set_time(time_str_to_ms(self.last_set_time))
                if self.timer_engine.mode == TimerMode.COUNTUP:
                    self.timer_label.setText("00:00")
                else:
                    self.timer_label.setText(self.last_set_time)

    def _auto_start_next_stage(self):
        """Автоматически запустить таймер для следующего этапа"""
        if self.current_script and not self.timer_engine.is_running:
            print("🚀 Автозапуск следующего этапа (Вопросы-ответы)")
            self.toggle_timer()

    def open_powerpoint_settings(self):
        """Открыть настройки интеграции с PowerPoint"""
        try:
            # Проверяем, не открыто ли уже окно
            if hasattr(self, 'ppt_settings_window') and self.ppt_settings_window is not None:
                try:
                    if self.ppt_settings_window.isVisible():
                        self.ppt_settings_window.raise_()
                        self.ppt_settings_window.activateWindow()
                        return
                    else:
                        self.ppt_settings_window.close()
                        self.ppt_settings_window = None
                except (RuntimeError, AttributeError):
                    self.ppt_settings_window = None

            # Создаём новое окно
            from ui.powerpoint_settings import PowerPointSettingsWindow
            self.ppt_settings_window = PowerPointSettingsWindow(main_window=self)
            self.ppt_settings_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.ppt_settings_window.show()
            self.ppt_settings_window.raise_()
            self.ppt_settings_window.activateWindow()

        except Exception as e:
            print(f"Ошибка открытия настроек PowerPoint: {e}")
            import traceback
            traceback.print_exc()

    def on_ppt_settings_changed(self):
        """Обработчик изменения настроек PowerPoint"""
        # Здесь можно обновить какие-то параметры в главном окне
        # Например, перезапустить мониторинг если нужно
        print("Настройки PowerPoint обновлены")

    def on_ppt_slide_changed(self, slide: int, total: int):
        """Обработка смены слайда из PowerPoint"""
        # Обновляем статус в окне настроек, если открыто
        if hasattr(self, 'ppt_settings') and self.ppt_settings and self.ppt_settings.isVisible():
            self.ppt_settings.update_status(True, slide, total)

    def on_slide_show_ended(self):
        """Показ слайдов завершен"""
        print("🎬 Показ слайдов завершен")

        auto_finish = self.settings.settings.value("ppt/auto_finish", True, type=bool)

        if auto_finish:
            print("✅ Автозавершение выступления")
            if self.timer_engine and self.timer_engine.is_running:
                self.finish_presentation()
            elif self.stage_stats_list:
                self.finish_presentation()
        else:
            print("⏸️ Автозавершение выключено, таймер продолжает работу")

    # ИСПРАВИТЬ метод on_slide_changed_auto
    def on_slide_changed_auto(self, current: int, total: int):
        """Автоматическая обработка смены слайда с учетом настроек"""

        # ⚠️ НЕ переключаем этапы, если выступление завершается
        if self.is_ending_presentation:
            print("⏸️ Выступление завершается, игнорируем смену слайда")
            return

        # Загружаем настройки
        auto_start = self.settings.settings.value("ppt/auto_start", True, type=bool)
        start_slide = self.settings.settings.value("ppt/start_slide", 2, type=int)

        print(f"📊 Слайд {current}/{total}")

        # Привязка этапов к слайдам
        if self.current_script and not self.is_ending_presentation:
            import json
            mappings_str = self.settings.settings.value("ppt/stage_mappings", "[]")
            try:
                mappings = json.loads(mappings_str)
                for mapping in mappings:
                    first = mapping.get('first_slide', 1)
                    last = mapping.get('last_slide', 1)
                    stage_index = mapping.get('stage_index', -1)

                    if first <= current <= last and stage_index >= 0:
                        current_stage = self.current_script.current_stage_index
                        # ⚠️ ПЕРЕКЛЮЧАЕМСЯ ТОЛЬКО ЕСЛИ ЭТАП РАЗНЫЙ
                        if current_stage != stage_index and not self.current_script.is_finished():
                            print(f"🔄 Слайд {current} -> этап {stage_index + 1}")
                            # Переключаем на нужный этап
                            while self.current_script.current_stage_index < stage_index:
                                self.on_next_stage()
                            break
            except Exception as e:
                print(f"Ошибка загрузки привязок: {e}")

        # Слайд запуска таймера (только если ещё не завершили)
        if current == start_slide and auto_start and not self.is_ending_presentation:
            if not self.timer_engine.is_running:
                if self.current_script:
                    print(f"🚀 Автозапуск сценария")
                    self.toggle_timer()
                else:
                    current_time = self.time_input.text()
                    if validate_time_input(current_time):
                        duration_ms = time_str_to_ms(current_time)
                        self.timer_engine.start_timer(duration_ms)
                        print(f"🚀 Автозапуск таймера")

    def on_slide_show_started(self, total_slides: int):
        """Показ слайдов запущен"""
        print(f"🎬 Показ слайдов запущен ({total_slides} слайдов)")

        # Используем QTimer для отложенного показа окна
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self.show_compact_for_presentation)

    def show_compact_for_presentation(self):
        """Показать компактное окно для презентации"""
        try:
            # Если компактное окно уже существует и видимо - просто поднимаем
            if self.compact_window and self.compact_window.isVisible():
                self.compact_window.raise_()
                return

            # Если компактное окно существует но не видимо - показываем
            if self.compact_window and not self.compact_window.isVisible():
                self.compact_window.show()
                self.compact_window.raise_()
            else:
                # Создаём новое компактное окно
                self.compact_window = CompactWindow()
                self.compact_window.closed.connect(self.on_compact_closed)
                self.compact_window.toggle_full.connect(self.toggle_compact)

                # Основные сигналы
                self.compact_window.toggle_timer.connect(self.toggle_timer)
                self.compact_window.reset_timer.connect(self.on_reset_timer)
                self.compact_window.finish_presentation.connect(self.finish_presentation)
                self.compact_window.show_settings.connect(self.show_settings)
                self.compact_window.show_statistics.connect(self.toggle_statistics)

                # Быстрое время
                self.compact_window.quick_time_3.connect(lambda: self.set_time_from_button("03:00"))
                self.compact_window.quick_time_5.connect(lambda: self.set_time_from_button("05:00"))
                self.compact_window.quick_time_7.connect(lambda: self.set_time_from_button("07:00"))
                self.compact_window.quick_time_10.connect(lambda: self.set_time_from_button("10:00"))

                # Режимы
                self.compact_window.mode_countdown.connect(lambda: self.set_timer_mode(TimerMode.COUNTDOWN))
                self.compact_window.mode_countup.connect(lambda: self.set_timer_mode(TimerMode.COUNTUP))
                self.compact_window.mode_both.connect(lambda: self.set_timer_mode(TimerMode.BOTH))

                # Прозрачность
                self.compact_window.toggle_transparent_mode.connect(self.toggle_transparent_mode)

                # Настройки прозрачности
                compact_opacity = self.settings.load_compact_opacity()
                self.compact_window.set_opacity(compact_opacity / 100.0)

                # Восстановление геометрии или установка по умолчанию
                saved_geometry = self.settings.load_compact_window_geometry()
                if saved_geometry:
                    self.compact_window.set_geometry_from_saved(saved_geometry)
                else:
                    screen = self.compact_window.screen().availableGeometry()
                    self.compact_window.setGeometry(
                        screen.width() - self.compact_window.default_width - 20,
                        50,
                        self.compact_window.default_width,
                        self.compact_window.default_height
                    )

                self.compact_window.show()

            # ✅ УСТАНАВЛИВАЕМ ПРАВИЛЬНЫЙ ЦВЕТ (зелёный фон, белый текст)
            if self.compact_window:
                # Устанавливаем позицию в правый верхний угол
                screen = self.compact_window.screen().availableGeometry()
                self.compact_window.setGeometry(
                    screen.width() - 320,
                    10,
                    300,
                    150
                )
                self.compact_window.raise_()

                # ✅ ВАЖНО: Устанавливаем правильный цвет для компактного окна
                if self.timer_engine:
                    if self.timer_engine.current_phase == TimerEngine.PHASE_NORMAL:
                        bg_color = self.normal_bg_color
                        text_color = self.normal_text_color
                    elif self.timer_engine.current_phase == TimerEngine.PHASE_WARNING:
                        bg_color = self.warning_bg_color
                        text_color = "#000000"
                    else:
                        bg_color = self.overtime_bg_color
                        text_color = "#FFFFFF"
                else:
                    bg_color = self.normal_bg_color
                    text_color = self.normal_text_color

                main_time = self.timer_label.text()
                if self.timer_engine and self.timer_engine.mode == TimerMode.BOTH and not self.secondary_timer_label.isHidden():
                    secondary_time = self.secondary_timer_label.text().replace('+', '')
                    display_text = f"{main_time} / {secondary_time}"
                else:
                    display_text = main_time

                if self.transparent_mode:
                    self.compact_window.update_display(display_text, "transparent", bg_color)
                else:
                    self.compact_window.update_display(display_text, bg_color, text_color)

                print("📱 Компактное окно показано, цвет установлен")
        except Exception as e:
            print(f"Ошибка показа компактного окна: {e}")

    def _auto_start_next_stage(self):
        """Автоматически запустить таймер для следующего этапа"""
        print(
            f"🚀 _auto_start_next_stage | current_script: {self.current_script is not None} | is_running: {self.timer_engine.is_running if self.timer_engine else False}")

        if self.current_script and not self.timer_engine.is_running:
            stage = self.current_script.get_current_stage()
            if stage:
                print(f"🚀 Автозапуск этапа: {stage.name}")
                self.toggle_timer()
            else:
                print("❌ Нет текущего этапа")
        else:
            print("⚠️ Условия не выполнены для автозапуска")
    def start_ppt_monitoring(self):
        """Запустить мониторинг PowerPoint"""
        if not self.ppt_controller.isRunning():
            self.ppt_controller.start()

    def stop_ppt_monitoring(self):
        """Остановить мониторинг PowerPoint"""
        if self.ppt_controller.isRunning():
            self.ppt_controller.stop()

    def on_next_stage_hotkey(self):
        """Горячая клавиша Ctrl+N - переход к следующему этапу"""
        if self.current_script:
            if not self.current_script.is_finished():
                print("⌨️ Ctrl+N: переход к следующему этапу")
                self.on_next_stage()
        else:
            print("⌨️ Ctrl+N: нет активного сценария")

    def on_previous_stage_hotkey(self):
        """Горячая клавиша Ctrl+P - переход к предыдущему этапу"""
        if self.current_script:
            current_index = self.current_script.current_stage_index
            if current_index > 0:
                print(f"⌨️ Ctrl+P: возврат к предыдущему этапу")
                self.current_script.current_stage_index = current_index - 1
                self._reset_full_script()
                if self.timer_engine and not self.timer_engine.is_running:
                    self.toggle_timer()
        else:
            print("⌨️ Ctrl+P: нет активного сценария")

    def on_start_stage_hotkey(self):
        """Горячая клавиша Ctrl+E - запуск/пауза текущего этапа"""
        if self.current_script:
            if self.timer_engine:
                if self.timer_engine.is_running and not self.timer_engine.is_paused:
                    self.timer_engine.pause_timer()
                    print("⌨️ Ctrl+E: пауза")
                else:
                    self.timer_engine.resume_timer() if self.timer_engine.is_paused else self.toggle_timer()
                    print("⌨️ Ctrl+E: запуск")
        else:
            print("⌨️ Ctrl+E: нет сценария, запуск таймера")
            self.toggle_timer()

    def _do_reset_display(self):
        """Сброс отображения таймера после задержки"""
        # Сбрасываем движок
        if self.timer_engine:
            self.timer_engine.reset_timer()

        # Сбрасываем отображение в зависимости от режима
        if self.current_script:
            self.current_script.reset()
            self.current_script.start()
            first_stage = self.current_script.get_current_stage()
            if first_stage:
                time_str = first_stage.get_duration_str()
                self.time_input.setText(time_str)
                if self.timer_engine:
                    self.timer_engine.set_time(first_stage.duration_ms)
                self.timer_label.setText(time_str)
        else:
            self.time_input.setText(self.last_set_time)
            if self.timer_engine:
                self.timer_engine.set_time(time_str_to_ms(self.last_set_time))
                if self.timer_engine.mode == TimerMode.COUNTUP:
                    self.timer_label.setText("00:00")
                else:
                    self.timer_label.setText(self.last_set_time)

        # Восстанавливаем цвета (берём из настроек)
        self.reset_color_to_normal()

        # Обновляем компактное окно
        if self.compact_window and self.compact_window.isVisible():
            main_time = self.timer_label.text()
            if self.timer_engine and self.timer_engine.mode == TimerMode.BOTH:
                secondary_time = self.secondary_timer_label.text().replace('+', '')
                display_text = f"{main_time} / {secondary_time}"
            else:
                display_text = main_time

            # Берём цвета из настроек, а не жёстко задаём
            if self.transparent_mode:
                self.compact_window.update_display(display_text, "transparent", self.normal_bg_color)
            else:
                self.compact_window.update_display(display_text, self.normal_bg_color, self.normal_text_color)