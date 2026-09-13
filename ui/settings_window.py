from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout,
                             QPushButton, QLabel, QCheckBox, QSpinBox,
                             QGroupBox, QColorDialog, QRadioButton, QButtonGroup,
                             QSizePolicy, QSlider, QHBoxLayout, QComboBox,
                             QMessageBox, QScrollArea)
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QColor

from timer_engine import TimerMode
from ui.settings_style import SETTINGS_WINDOW_STYLE, TITLE_LABEL_STYLE, COLOR_LABEL_STYLE, COLOR_BUTTON_STYLE
from script_editor import ScriptEditor


class SettingsWindow(QWidget):
    """Окно расширенных настроек - с прокруткой"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.parent_window = None  # будет установлен позже
        self.base_width = 480
        self.base_height = 730

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )

        self.setup_ui()
        # НЕ вызываем load_settings() и restore_geometry() здесь

    def set_parent_window(self, main_window):
        """Установить ссылку на главное окно и загрузить данные"""
        self.parent_window = main_window
        self.load_settings()
        self.restore_geometry()

    def setup_ui(self):
        """Настройка интерфейса окна настроек"""
        self.setWindowTitle("Настройки таймера")

        self.setMinimumSize(self.base_width, self.base_height)
        self.resize(self.base_width, self.base_height)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #ECF0F1;
            }
        """)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        title_label = QLabel("НАСТРОЙКИ")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(TITLE_LABEL_STYLE)
        layout.addWidget(title_label)

        # === ГРУППА ВЫБОРА СЦЕНАРИЯ ===
        script_group = QGroupBox("Сценарий выступления")
        script_layout = QVBoxLayout()
        script_layout.setContentsMargins(10, 0, 10, 10)
        script_layout.setSpacing(8)

        script_label = QLabel("Выберите сценарий:")
        script_layout.addWidget(script_label)

        self.script_combo = QComboBox()
        self.script_combo.setMinimumHeight(28)
        self.script_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
            }
            QComboBox QAbstractItemView {
                background-color: white;
            }
        """)
        self.script_combo.currentIndexChanged.connect(self.on_script_selected)
        script_layout.addWidget(self.script_combo)

        script_group.setLayout(script_layout)
        layout.addWidget(script_group)

        # === ГРУППА РЕЖИМА ТАЙМЕРА ===
        mode_group = QGroupBox("Режим таймера")
        mode_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        mode_layout = QVBoxLayout()
        mode_layout.setContentsMargins(10, 0, 10, 10)

        self.mode_button_group = QButtonGroup()

        self.countdown_radio = QRadioButton("Обратный отсчет (от установленного до 0)")
        self.countup_radio = QRadioButton("Прямой отсчет (от 0 до установленного)")
        self.both_radio = QRadioButton("Двойной таймер (прямой и обратный)")

        self.mode_button_group.addButton(self.countdown_radio, 0)
        self.mode_button_group.addButton(self.countup_radio, 1)
        self.mode_button_group.addButton(self.both_radio, 2)

        self.countdown_radio.toggled.connect(self.on_mode_changed)
        self.countup_radio.toggled.connect(self.on_mode_changed)
        self.both_radio.toggled.connect(self.on_mode_changed)

        mode_layout.addWidget(self.countdown_radio)
        mode_layout.addWidget(self.countup_radio)
        mode_layout.addWidget(self.both_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # === ГРУППА ЗВУКА ===
        sound_group = QGroupBox("Звуковые сигналы")
        sound_layout = QVBoxLayout()
        sound_layout.setContentsMargins(10, 0, 10, 10)

        self.sound_checkbox = QCheckBox("Включить звуковые сигналы")
        self.sound_checkbox.setChecked(True)
        self.sound_checkbox.stateChanged.connect(self.on_sound_changed)

        sound_layout.addWidget(self.sound_checkbox)
        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)

        # === ГРУППА ВРЕМЕНИ ПРЕДУПРЕЖДЕНИЯ ===
        warning_group = QGroupBox("Предупреждение")
        warning_layout = QVBoxLayout()
        warning_layout.setContentsMargins(10, 0, 10, 10)

        warning_layout.addWidget(QLabel("Уведомлять за (секунд до конца):"))

        self.warning_spinbox = QSpinBox()
        self.warning_spinbox.setRange(0, 999)
        self.warning_spinbox.setValue(60)
        self.warning_spinbox.setSuffix(" сек")
        self.warning_spinbox.valueChanged.connect(self.on_warning_time_changed)

        warning_layout.addWidget(self.warning_spinbox)
        warning_group.setLayout(warning_layout)
        layout.addWidget(warning_group)

        # === ГРУППА ПРОЗРАЧНОСТИ КОМПАКТНОГО ОКНА ===
        opacity_group = QGroupBox("Компактный режим")
        opacity_layout = QVBoxLayout()
        opacity_layout.setContentsMargins(10, 0, 10, 10)

        opacity_layout.addWidget(QLabel("Прозрачность окна:"))

        opacity_slider_layout = QGridLayout()

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)

        self.opacity_label = QLabel("100%")
        self.opacity_label.setMinimumWidth(40)
        self.opacity_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        opacity_slider_layout.addWidget(self.opacity_slider, 0, 0)
        opacity_slider_layout.addWidget(self.opacity_label, 0, 1)

        opacity_layout.addLayout(opacity_slider_layout)

        opacity_group.setLayout(opacity_layout)
        layout.addWidget(opacity_group)

        # === ГРУППА ПРОЗРАЧНОГО ФОНА ===
        transparent_group = QGroupBox("Прозрачный режим")
        transparent_layout = QVBoxLayout()
        transparent_layout.setContentsMargins(10, 0, 10, 10)

        self.transparent_checkbox = QCheckBox("Прозрачный фон (только цифры)")
        self.transparent_checkbox.setToolTip(
            "При включении фон становится прозрачным, остаются только цифры с обводкой")
        self.transparent_checkbox.stateChanged.connect(self.on_transparent_changed)

        transparent_layout.addWidget(self.transparent_checkbox)
        transparent_group.setLayout(transparent_layout)
        layout.addWidget(transparent_group)

        # === ГРУППА ЦВЕТОВ ===
        colors_group = QGroupBox("Цвета отображения")
        colors_layout = QVBoxLayout()
        colors_layout.setContentsMargins(10, 5, 10, 10)
        colors_layout.setSpacing(10)

        self.colors_info = [
            ("normal", "Нормальное время", "#2E7D32"),
            ("warning", "Предупреждение", "#F9A825"),
            ("overtime", "Время вышло", "#C62828")
        ]

        for color_type, text, default_color in self.colors_info:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(15)

            color_label = QLabel(text)
            color_label.setStyleSheet(COLOR_LABEL_STYLE)

            row_layout.addWidget(color_label)
            row_layout.addStretch()

            color_btn = QPushButton()
            color_btn.setFixedSize(50, 30)
            color_btn.setObjectName(f"color_btn_{color_type}")
            color_btn.clicked.connect(lambda checked, ct=color_type: self.choose_color(ct))

            setattr(self, f"{color_type}_color_btn", color_btn)
            row_layout.addWidget(color_btn)
            colors_layout.addLayout(row_layout)

        colors_group.setLayout(colors_layout)
        layout.addWidget(colors_group)

        # === КНОПКА СТАТИСТИКИ ===
        stats_btn = QPushButton("📊 Открыть статистику выступлений")
        stats_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        stats_btn.clicked.connect(self.open_statistics)
        layout.addWidget(stats_btn)

        # === КНОПКА POWERPOINT ===
        ppt_btn = QPushButton("🎯 Интеграция с PowerPoint")
        ppt_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        ppt_btn.clicked.connect(self.open_powerpoint_settings)
        layout.addWidget(ppt_btn)

        layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        self.setStyleSheet(SETTINGS_WINDOW_STYLE)

    def load_scripts_list(self):
        """Загрузка списка сценариев из БД"""
        if not self.parent_window:
            return
        self.script_combo.blockSignals(True)
        self.script_combo.clear()

        self.script_combo.addItem("🔓 Без сценария (обычный режим)", None)

        if self.parent_window.db_manager:
            try:
                scripts = self.parent_window.db_manager.get_all_scripts()
                for script_id, script_name in scripts:
                    self.script_combo.addItem(f"📋 {script_name}", script_id)
            except Exception as e:
                print(f"Ошибка загрузки сценариев из БД: {e}")

        self.script_combo.insertSeparator(self.script_combo.count())
        self.script_combo.addItem("➕ Редактор сценариев...", -1)

        saved_script_id = self.parent_window.settings.load_current_script_id() if self.parent_window else None
        if saved_script_id:
            for i in range(self.script_combo.count()):
                data = self.script_combo.itemData(i)
                if data and data == saved_script_id:
                    self.script_combo.setCurrentIndex(i)
                    break

        self.script_combo.blockSignals(False)

    def on_script_selected(self, index):
        """Обработка выбора сценария"""
        if index < 0 or not self.parent_window:
            return

        script_id = self.script_combo.itemData(index)

        if script_id == -1:
            self.script_combo.setCurrentIndex(0)
            self.open_script_editor()
            return

        if script_id is None:
            if self.parent_window:
                self.parent_window.clear_script()
                self.parent_window.settings.save_current_script_id(None)
            return

        if self.parent_window and self.parent_window.db_manager:
            script_data = self.parent_window.db_manager.get_script_with_stages(script_id)
            if script_data:
                self.parent_window.load_script_from_db(script_data)
                self.parent_window.settings.save_current_script_id(script_id)

    def open_script_editor(self, edit_script_id=None):
        """Открыть редактор сценариев"""
        self.editor = ScriptEditor(
            db_manager=self.parent_window.db_manager if self.parent_window else None,
            parent=None,
            edit_script_id=edit_script_id
        )
        self.editor.script_applied.connect(self.on_script_from_editor)
        self.editor.script_deleted.connect(self.on_script_deleted)
        self.editor.show()

    def on_script_deleted(self, script_id):
        """Обработка удаления сценария из редактора"""
        if self.parent_window:
            current_id = self.parent_window.settings.load_current_script_id()
            if current_id == script_id:
                self.parent_window.clear_script()
                self.parent_window.settings.save_current_script_id(None)

        self.load_scripts_list()

    def on_script_from_editor(self, script):
        """Сценарий загружен из редактора"""
        if self.parent_window:
            edit_id = getattr(script, '_edit_script_id', None)

            if edit_id:
                self.parent_window.db_manager.delete_script(edit_id)
                script_id = self.parent_window.db_manager.add_script(script.name)
            else:
                script_id = self.parent_window.db_manager.add_script(script.name)

            for i, stage in enumerate(script.stages):
                self.parent_window.db_manager.add_script_stage(
                    script_id, stage.name, stage.duration_ms, i
                )

            script_data = self.parent_window.db_manager.get_script_with_stages(script_id)
            if script_data:
                self.parent_window.load_script_from_db(script_data)
                self.parent_window.settings.save_current_script_id(script_id)

        self.load_scripts_list()

    def restore_geometry(self):
        """Восстановление сохраненной геометрии окна"""
        if self.parent_window:
            geometry = self.parent_window.settings.load_settings_geometry()
            if geometry and isinstance(geometry, QByteArray) and not geometry.isEmpty():
                self.restoreGeometry(geometry)
            else:
                screen = self.screen().availableGeometry()
                self.move(
                    screen.width() // 2 - self.width() // 2,
                    screen.height() // 2 - self.height() // 2
                )

    def on_mode_changed(self):
        """Обработка изменения режима таймера"""
        if self.parent_window and self.parent_window.timer_engine:
            if self.countdown_radio.isChecked():
                self.parent_window.timer_engine.set_mode(TimerMode.COUNTDOWN)
            elif self.countup_radio.isChecked():
                self.parent_window.timer_engine.set_mode(TimerMode.COUNTUP)
            else:
                self.parent_window.timer_engine.set_mode(TimerMode.BOTH)

            self.parent_window.update_display_mode()

    def load_settings(self):
        """Загрузка настроек"""
        if not self.parent_window:
            return
        sound_enabled = self.parent_window.settings.load_sound_enabled()
        self.sound_checkbox.setChecked(sound_enabled)

        warning_time = self.parent_window.settings.load_warning_time()
        self.warning_spinbox.setValue(warning_time)

        compact_opacity = self.parent_window.settings.load_compact_opacity()
        self.opacity_slider.setValue(compact_opacity)
        self.opacity_label.setText(f"{compact_opacity}%")

        mode_str = self.parent_window.settings.load_timer_mode()

        self.countdown_radio.blockSignals(True)
        self.countup_radio.blockSignals(True)
        self.both_radio.blockSignals(True)

        if mode_str == TimerMode.COUNTUP.value:
            self.countup_radio.setChecked(True)
        elif mode_str == TimerMode.BOTH.value:
            self.both_radio.setChecked(True)
        else:
            self.countdown_radio.setChecked(True)

        self.countdown_radio.blockSignals(False)
        self.countup_radio.blockSignals(False)
        self.both_radio.blockSignals(False)

        transparent = self.parent_window.settings.load_transparent_mode()
        self.transparent_checkbox.setChecked(transparent)

        normal_color, warning_color, overtime_color = self.parent_window.settings.load_colors()

        self.normal_color_btn.setStyleSheet(COLOR_BUTTON_STYLE.format(color=normal_color))
        self.warning_color_btn.setStyleSheet(COLOR_BUTTON_STYLE.format(color=warning_color))
        self.overtime_color_btn.setStyleSheet(COLOR_BUTTON_STYLE.format(color=overtime_color))

        self.load_scripts_list()

    def choose_color(self, color_type):
        """Выбор цвета"""
        btn = getattr(self, f"{color_type}_color_btn")
        current_color = QColor(btn.styleSheet().split("background-color: ")[1].split(";")[0])

        color = QColorDialog.getColor(current_color, self, f"Выберите цвет для {color_type}")

        if color.isValid():
            btn.setStyleSheet(COLOR_BUTTON_STYLE.format(color=color.name()))
            self.apply_color_changes()

    def apply_color_changes(self):
        """Применение изменений цветов"""
        if self.parent_window:
            normal_color = self._extract_color(self.normal_color_btn)
            warning_color = self._extract_color(self.warning_color_btn)
            overtime_color = self._extract_color(self.overtime_color_btn)

            self.parent_window.normal_bg_color = normal_color
            self.parent_window.warning_bg_color = warning_color
            self.parent_window.overtime_bg_color = overtime_color

            if self.parent_window.timer_engine and not self.parent_window.timer_engine.is_running:
                self.parent_window.reset_color_to_normal()

    def _extract_color(self, btn: QPushButton) -> str:
        """Извлечение цвета из стиля кнопки"""
        style = btn.styleSheet()
        if "background-color:" in style:
            return style.split("background-color:")[1].split(";")[0].strip()
        return "#2E7D32"

    def on_sound_changed(self, state):
        """Обработка изменения настройки звука"""
        enabled = state == Qt.CheckState.Checked.value
        if self.parent_window:
            self.parent_window.sound_manager.set_enabled(enabled)

    def on_warning_time_changed(self, value):
        """Обработка изменения времени предупреждения"""
        if self.parent_window and self.parent_window.timer_engine:
            self.parent_window.timer_engine.warning_threshold = value * 1000

    def on_opacity_changed(self, value):
        """Обработка изменения прозрачности компактного окна"""
        self.opacity_label.setText(f"{value}%")
        if self.parent_window:
            self.parent_window.settings.save_compact_opacity(value)
            if self.parent_window.compact_window and self.parent_window.compact_window.isVisible():
                self.parent_window.compact_window.set_opacity(value / 100.0)

    def apply_and_save_settings(self):
        """Применяем и сохраняем настройки"""
        if not self.parent_window:
            return

        try:
            self.parent_window.settings.save_sound_enabled(self.sound_checkbox.isChecked())
            self.parent_window.sound_manager.set_enabled(self.sound_checkbox.isChecked())

            warning_time = self.warning_spinbox.value()
            self.parent_window.settings.save_warning_time(warning_time)
            if self.parent_window.timer_engine:
                self.parent_window.timer_engine.warning_threshold = warning_time * 1000

            compact_opacity = self.opacity_slider.value()
            self.parent_window.settings.save_compact_opacity(compact_opacity)

            if self.countdown_radio.isChecked():
                mode_str = TimerMode.COUNTDOWN.value
            elif self.countup_radio.isChecked():
                mode_str = TimerMode.COUNTUP.value
            else:
                mode_str = TimerMode.BOTH.value
            self.parent_window.settings.save_timer_mode(mode_str)

            normal_color = self._extract_color(self.normal_color_btn)
            warning_color = self._extract_color(self.warning_color_btn)
            overtime_color = self._extract_color(self.overtime_color_btn)

            self.parent_window.settings.save_colors(normal_color, warning_color, overtime_color)

            self.parent_window.normal_bg_color = normal_color
            self.parent_window.warning_bg_color = warning_color
            self.parent_window.overtime_bg_color = overtime_color

            if self.parent_window.timer_engine and not self.parent_window.timer_engine.is_running:
                self.parent_window.reset_color_to_normal()
        except (RuntimeError, AttributeError):
            pass

    def closeEvent(self, event):
        self.apply_and_save_settings()
        if self.parent_window:
            self.parent_window.settings_window = None
        self.hide()
        event.accept()

    def on_transparent_changed(self, state):
        """Обработка изменения прозрачного режима"""
        if self.parent_window:
            transparent = state == Qt.CheckState.Checked.value
            self.parent_window.transparent_mode = transparent
            self.parent_window.settings.save_transparent_mode(transparent)

            if self.parent_window.timer_engine and not self.parent_window.timer_engine.is_running:
                self.parent_window.reset_color_to_normal()
            elif self.parent_window.timer_engine and self.parent_window.timer_engine.is_running:
                phase = self.parent_window.timer_engine.current_phase
                self.parent_window.on_phase_changed(phase)

    def open_statistics(self):
        """Открыть окно статистики"""
        try:
            from ui.statistics_window import StatisticsWindow

            if self.parent_window and hasattr(self.parent_window, 'db_manager'):
                self.statistics_window = StatisticsWindow(
                    self.parent_window.db_manager,
                    parent=None
                )
                self.statistics_window.show()
                self.statistics_window.raise_()
                self.statistics_window.activateWindow()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось открыть статистику")
        except Exception as e:
            print(f"Ошибка при открытии статистики: {e}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка: {e}")

    def open_powerpoint_settings(self):
        """Открыть настройки PowerPoint"""
        if self.parent_window:
            self.parent_window.open_powerpoint_settings()

