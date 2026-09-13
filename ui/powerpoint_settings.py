from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QGroupBox, QCheckBox, QSpinBox,
                             QScrollArea, QMessageBox, QFrame, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal


class PowerPointSettingsWindow(QWidget):
    """Окно настройки интеграции с PowerPoint"""

    settings_changed = pyqtSignal()

    def __init__(self, main_window=None):
        super().__init__(None)
        self.main_window = main_window

        self.setWindowTitle("Настройка связи с PowerPoint")
        self.setMinimumSize(500, 550)
        self.setFixedWidth(550)

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )

        self.stage_widgets = []
        self.setup_ui()
        self.load_settings()
        self.update_stages_display()

        # Подключаем сигнал обновления сценария
        if self.main_window:
            self.main_window.script_changed.connect(self.update_stages_display)

    def setup_ui(self):
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

        # Заголовок
        title_label = QLabel("СВЯЗЬ С POWERPOINT")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: #2C3E50;
            font-size: 20px;
            font-weight: bold;
            background-color: transparent;
        """)
        layout.addWidget(title_label)

        # Информация о сценарии
        script_group = QGroupBox("Сценарий")
        script_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #BDC3C7;
                border-radius: 8px;
                margin-top: 13px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        script_layout = QHBoxLayout(script_group)
        script_layout.setContentsMargins(15, 10, 15, 10)
        script_layout.addWidget(QLabel("Выбран:"))
        self.script_label = QLabel("Не выбран")
        self.script_label.setStyleSheet("font-weight: bold; color: #27AE60;")
        script_layout.addWidget(self.script_label)
        self.stages_count_label = QLabel("")
        script_layout.addWidget(self.stages_count_label)
        script_layout.addStretch()
        layout.addWidget(script_group)

        # Основные настройки
        main_group = QGroupBox("Основные настройки")
        main_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #BDC3C7;
                border-radius: 8px;
                margin-top: 13px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        main_layout_v = QVBoxLayout(main_group)
        main_layout_v.setContentsMargins(15, 10, 15, 10)
        main_layout_v.setSpacing(8)

        self.monitoring_check = QCheckBox("🔄 Отслеживать показ слайдов PowerPoint")
        self.monitoring_check.setChecked(True)
        self.monitoring_check.setStyleSheet("font-size: 13px; spacing: 8px;")
        main_layout_v.addWidget(self.monitoring_check)

        self.compact_check = QCheckBox("📱 Показывать компактное окно при показе")
        self.compact_check.setChecked(True)
        self.compact_check.setStyleSheet("font-size: 13px; spacing: 8px;")
        main_layout_v.addWidget(self.compact_check)

        self.auto_finish_check = QCheckBox("✅ Завершать выступление при выходе из показа (Esc)")
        self.auto_finish_check.setChecked(True)
        self.auto_finish_check.setStyleSheet("font-size: 13px; spacing: 8px;")
        main_layout_v.addWidget(self.auto_finish_check)

        # Режим запуска
        start_layout = QHBoxLayout()
        start_layout.setSpacing(10)
        start_layout.addWidget(QLabel("Запускать таймер на слайде №:"))
        self.start_slide_spin = QSpinBox()
        self.start_slide_spin.setRange(1, 999)
        self.start_slide_spin.setValue(2)
        self.start_slide_spin.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                background: white;
                min-width: 70px;
            }
        """)
        start_layout.addWidget(self.start_slide_spin)
        start_layout.addStretch()
        main_layout_v.addLayout(start_layout)

        layout.addWidget(main_group)

        # ===== СЕКЦИЯ ДЛЯ СЦЕНАРИЕВ (скрыта по умолчанию) =====
        self.script_section = QWidget()
        self.script_section.setVisible(False)
        script_section_layout = QVBoxLayout(self.script_section)
        script_section_layout.setContentsMargins(0, 0, 0, 0)
        script_section_layout.setSpacing(15)

        # Привязка этапов к слайдам
        self.stages_group = QGroupBox("Привязка этапов к слайдам")
        self.stages_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #BDC3C7;
                border-radius: 8px;
                margin-top: 13px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        self.stages_layout = QVBoxLayout(self.stages_group)
        self.stages_layout.setContentsMargins(15, 10, 15, 10)
        self.stages_layout.setSpacing(8)
        script_section_layout.addWidget(self.stages_group)

        # Кнопка автораспределения
        auto_btn = QPushButton("🤖 Автораспределить слайды поровну")
        auto_btn.clicked.connect(self.auto_distribute_slides)
        auto_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        script_section_layout.addWidget(auto_btn)

        # Перерывы между этапами
        pause_group = QGroupBox("Перерывы между этапами")
        pause_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #BDC3C7;
                border-radius: 8px;
                margin-top: 13px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        pause_layout = QVBoxLayout(pause_group)
        pause_layout.setContentsMargins(15, 10, 15, 10)
        pause_layout.setSpacing(8)

        self.pause_enabled_check = QCheckBox("⏸️ Делать паузу между этапами")
        self.pause_enabled_check.setChecked(False)
        self.pause_enabled_check.toggled.connect(self.toggle_pause_settings)
        self.pause_enabled_check.setStyleSheet("font-size: 13px; spacing: 8px;")
        self.pause_enabled_check.setToolTip(
            "Включено: между этапами будет пауза с обратным отсчётом\n"
            "Выключено: сразу переход к следующему этапу"
        )
        pause_layout.addWidget(self.pause_enabled_check)

        pause_settings_layout = QHBoxLayout()
        pause_settings_layout.setSpacing(10)
        pause_settings_layout.addWidget(QLabel("Длительность паузы:"))
        self.pause_duration_spin = QSpinBox()
        self.pause_duration_spin.setRange(5, 300)
        self.pause_duration_spin.setValue(30)
        self.pause_duration_spin.setSuffix(" сек")
        self.pause_duration_spin.setEnabled(False)
        self.pause_duration_spin.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                background: white;
                min-width: 70px;
            }
        """)
        pause_settings_layout.addWidget(self.pause_duration_spin)
        pause_settings_layout.addStretch()
        pause_layout.addLayout(pause_settings_layout)

        script_section_layout.addWidget(pause_group)

        layout.addWidget(self.script_section)

        layout.addStretch()

        # Кнопка сохранения
        save_btn = QPushButton("💾 Сохранить настройки")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        layout.addWidget(save_btn)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Общий стиль окна
        self.setStyleSheet("""
            QWidget {
                background-color: #ECF0F1;
                color: #2C3E50;
                font-family: "Segoe UI", "Roboto", sans-serif;
                font-size: 13px;
            }
            QLabel {
                font-size: 13px;
            }
            QCheckBox, QRadioButton {
                font-size: 13px;
                spacing: 5px;
            }
            QPushButton {
                font-size: 13px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                background-color: #F0F0F0;
                padding: 5px;
            }
            QScrollArea {
                border: none;
                background-color: #ECF0F1;
            }
        """)

    def toggle_pause_settings(self, enabled):
        """Включение/выключение настроек паузы"""
        self.pause_duration_spin.setEnabled(enabled)

    def update_stages_display(self):
        """Обновить отображение этапов из сценария - полностью динамически"""
        # Очищаем старые виджеты
        for w in self.stage_widgets:
            self.stages_layout.removeWidget(w)
            w.deleteLater()
        self.stage_widgets.clear()

        # Проверяем, есть ли сценарий
        has_script = self.main_window and self.main_window.current_script

        if not has_script:
            self.script_label.setText("Не выбран")
            self.stages_count_label.setText("")
            self.script_section.setVisible(False)
            return

        # Есть сценарий - показываем секцию
        self.script_section.setVisible(True)

        script = self.main_window.current_script
        self.script_label.setText(script.name)
        self.stages_count_label.setText(f"({len(script.stages)} этапов)")

        # Создаем настройки для каждого этапа
        for i, stage in enumerate(script.stages):
            stage_frame = QFrame()
            stage_frame.setStyleSheet("""
                QFrame {
                    background: white;
                    border: 1px solid #BDC3C7;
                    border-radius: 5px;
                    padding: 8px;
                    margin: 2px;
                }
            """)
            stage_layout = QVBoxLayout(stage_frame)
            stage_layout.setSpacing(5)

            # Название этапа
            header = QHBoxLayout()
            name_label = QLabel(f"📌 Этап {i + 1}: {stage.name}")
            name_label.setStyleSheet("font-weight: bold; color: #2C3E50; font-size: 12px;")
            header.addWidget(name_label)

            duration_label = QLabel(f"({stage.get_duration_str()})")
            duration_label.setStyleSheet("color: #7F8C8D; font-size: 11px;")
            header.addWidget(duration_label)
            header.addStretch()
            stage_layout.addLayout(header)

            # Привязка к слайдам
            slide_row = QHBoxLayout()
            slide_row.setSpacing(5)
            slide_row.addWidget(QLabel("Слайды:"))

            first_slide = QSpinBox()
            first_slide.setRange(1, 999)
            first_slide.setValue(i * 3 + 2)
            first_slide.setPrefix("с ")
            first_slide.setMinimumWidth(80)
            slide_row.addWidget(first_slide)

            slide_row.addWidget(QLabel("по"))

            last_slide = QSpinBox()
            last_slide.setRange(1, 999)
            last_slide.setValue(i * 3 + 4)
            last_slide.setPrefix("по ")
            last_slide.setMinimumWidth(80)
            slide_row.addWidget(last_slide)

            slide_row.addStretch()
            stage_layout.addLayout(slide_row)

            self.stages_layout.addWidget(stage_frame)
            self.stage_widgets.append(stage_frame)

        # Загружаем сохранённые привязки
        self.load_stage_mappings()

    def load_stage_mappings(self):
        """Загрузить сохранённые привязки слайдов"""
        if not self.main_window:
            return

        import json
        settings = self.main_window.settings.settings
        mappings_str = settings.value("ppt/stage_mappings", "[]")

        try:
            mappings = json.loads(mappings_str)
            for mapping in mappings:
                stage_index = mapping.get('stage_index')
                if stage_index is not None and stage_index < len(self.stage_widgets):
                    spinboxes = self.stage_widgets[stage_index].findChildren(QSpinBox)
                    if len(spinboxes) >= 2:
                        spinboxes[0].setValue(mapping.get('first_slide', 1))
                        spinboxes[1].setValue(mapping.get('last_slide', 1))
        except:
            pass

    def auto_distribute_slides(self):
        """Автоматически распределить слайды между этапами"""
        if not self.main_window or not self.main_window.current_script:
            return

        total_slides, ok = QInputDialog.getInt(
            self,
            "Автораспределение",
            "Общее количество слайдов в презентации:",
            min=1, max=999, value=10
        )

        if not ok:
            return

        script = self.main_window.current_script
        num_stages = len(script.stages)

        if num_stages == 0:
            return

        slides_per_stage = total_slides // num_stages
        remainder = total_slides % num_stages

        current_slide = 1

        for i, w in enumerate(self.stage_widgets):
            spinboxes = w.findChildren(QSpinBox)
            if len(spinboxes) >= 2:
                stage_slides = slides_per_stage + (1 if i < remainder else 0)
                if stage_slides == 0:
                    stage_slides = 1

                first = current_slide
                last = min(current_slide + stage_slides - 1, total_slides)

                spinboxes[0].setValue(first)
                spinboxes[1].setValue(last)

                current_slide = last + 1

        QMessageBox.information(self, "Готово", f"Слайды распределены между {num_stages} этапами")

    def load_settings(self):
        """Загрузка сохраненных настроек"""
        if self.main_window:
            settings = self.main_window.settings.settings

            self.monitoring_check.setChecked(settings.value("ppt/monitoring", True, type=bool))
            self.compact_check.setChecked(settings.value("ppt/compact", True, type=bool))
            self.auto_finish_check.setChecked(settings.value("ppt/auto_finish", True, type=bool))
            self.start_slide_spin.setValue(settings.value("ppt/start_slide", 2, type=int))
            self.pause_enabled_check.setChecked(settings.value("ppt/pause_enabled", False, type=bool))
            self.pause_duration_spin.setValue(settings.value("ppt/pause_duration", 30, type=int))

    def save_settings(self):
        if not self.main_window:
            return

        settings = self.main_window.settings.settings

        # Сохраняем основные настройки
        settings.setValue("ppt/monitoring", self.monitoring_check.isChecked())
        settings.setValue("ppt/compact", self.compact_check.isChecked())
        settings.setValue("ppt/auto_finish", self.auto_finish_check.isChecked())
        settings.setValue("ppt/start_slide", self.start_slide_spin.value())
        settings.setValue("ppt/pause_enabled", self.pause_enabled_check.isChecked())
        settings.setValue("ppt/pause_duration", self.pause_duration_spin.value())

        # ✅ Сохраняем привязки этапов
        stage_mappings = []
        for i, w in enumerate(self.stage_widgets):
            spinboxes = w.findChildren(QSpinBox)
            if len(spinboxes) >= 2:
                stage_mappings.append({
                    'stage_index': i,
                    'first_slide': spinboxes[0].value(),
                    'last_slide': spinboxes[1].value()
                })

        import json
        settings.setValue("ppt/stage_mappings", json.dumps(stage_mappings))

        QMessageBox.information(self, "Успех", "Настройки сохранены!")

    def closeEvent(self, event):
        """Закрытие окна"""
        # Оповещаем главное окно, что окно закрыто
        if self.main_window:
            self.main_window.ppt_settings_window = None
        event.accept()