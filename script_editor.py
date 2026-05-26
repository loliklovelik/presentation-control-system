from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel, QSpinBox,
                             QLineEdit, QMessageBox, QHeaderView, QComboBox,
                             QInputDialog)
from PyQt6.QtCore import pyqtSignal, Qt
from presentation_script import PresentationScript, PresentationStage


class ScriptEditor(QWidget):
    """Редактор сценариев выступления (многоэтапный режим)"""

    script_applied = pyqtSignal(object)  # PresentationScript
    script_deleted = pyqtSignal(int)     # ID удалённого сценария

    def __init__(self, db_manager=None, parent=None, edit_script_id=None):
        # ВАЖНО: parent убираем полностью, чтобы окно было независимым
        super().__init__(None)

        self.db_manager = db_manager
        self.edit_script_id = edit_script_id  # None = новый, число = редактирование

        # Размеры окна
        self.setFixedWidth(650)
        self.setMinimumHeight(550)

        # Заголовок
        self.setWindowTitle("Редактор сценария выступления")

        # Обычное независимое окно (НЕ always on top)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowTitleHint
        )

        # Интерфейс
        self.setup_ui()

        # Загрузка шаблонов/сценариев
        self.load_presets()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("📋 СЦЕНАРИЙ ВЫСТУПЛЕНИЯ")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50;")
        layout.addWidget(title)

        # === НАЗВАНИЕ СЦЕНАРИЯ ===
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Название сценария:"))
        self.script_name_input = QLineEdit()
        self.script_name_input.setPlaceholderText("Например: Защита ВКР")
        name_layout.addWidget(self.script_name_input, 1)
        layout.addLayout(name_layout)

        # === ВЫБОР ШАБЛОНА ===
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Шаблон:"))

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("-- Выберите шаблон --", None)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selected)
        preset_layout.addWidget(self.preset_combo, 1)

        layout.addLayout(preset_layout)

        # === ТАБЛИЦА ЭТАПОВ ===
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "№", "Название этапа", "Минуты", "Секунды"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 80)
        layout.addWidget(self.table, 1)

        # === ПАНЕЛЬ ВВОДА ЭТАПА ===
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        input_layout.addWidget(QLabel("Название:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: Доклад")
        input_layout.addWidget(self.name_input, 2)

        input_layout.addWidget(QLabel("Мин:"))
        self.minutes_input = QSpinBox()
        self.minutes_input.setRange(0, 120)
        self.minutes_input.setValue(5)
        self.minutes_input.setSuffix(" мин")
        input_layout.addWidget(self.minutes_input)

        input_layout.addWidget(QLabel("Сек:"))
        self.seconds_input = QSpinBox()
        self.seconds_input.setRange(0, 59)
        self.seconds_input.setSuffix(" сек")
        input_layout.addWidget(self.seconds_input)

        layout.addLayout(input_layout)

        # === КНОПКИ УПРАВЛЕНИЯ ЭТАПАМИ ===
        stage_buttons = QHBoxLayout()

        add_btn = QPushButton("➕ Добавить этап")
        add_btn.clicked.connect(self.add_stage)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        stage_buttons.addWidget(add_btn)

        remove_btn = QPushButton("➖ Удалить этап")
        remove_btn.clicked.connect(self.remove_stage)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        stage_buttons.addWidget(remove_btn)

        move_up_btn = QPushButton("⬆ Вверх")
        move_up_btn.clicked.connect(self.move_stage_up)
        stage_buttons.addWidget(move_up_btn)

        move_down_btn = QPushButton("⬇ Вниз")
        move_down_btn.clicked.connect(self.move_stage_down)
        stage_buttons.addWidget(move_down_btn)

        stage_buttons.addStretch()
        layout.addLayout(stage_buttons)

        # === КНОПКИ УПРАВЛЕНИЯ СЦЕНАРИЕМ ===
        script_buttons = QHBoxLayout()

        load_btn = QPushButton("📂 Загрузить сценарий")
        load_btn.setToolTip("Загрузить существующий сценарий для редактирования")
        load_btn.clicked.connect(self.load_existing_script)
        script_buttons.addWidget(load_btn)

        delete_btn = QPushButton("🗑 Удалить сценарий")
        delete_btn.setToolTip("Удалить текущий сценарий из БД")
        delete_btn.clicked.connect(self.delete_current_script)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        script_buttons.addWidget(delete_btn)

        layout.addLayout(script_buttons)

        # === КНОПКИ ПРИМЕНЕНИЯ/ОТМЕНЫ ===
        action_buttons = QHBoxLayout()
        action_buttons.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.close)
        action_buttons.addWidget(cancel_btn)

        self.apply_btn = QPushButton("✅ Создать сценарий")
        self.apply_btn.clicked.connect(self.apply_script)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        action_buttons.addWidget(self.apply_btn)

        layout.addLayout(action_buttons)

        # === ИНФОРМАЦИОННАЯ СТРОКА ===
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #7F8C8D; font-style: italic;")
        layout.addWidget(self.info_label)

    def load_presets(self):
        """Загрузка шаблонов из БД"""
        if self.db_manager:
            try:
                scripts = self.db_manager.get_all_scripts()
                for script_id, script_name in scripts:
                    if self.edit_script_id and script_id == self.edit_script_id:
                        continue
                    self.preset_combo.addItem(script_name, script_id)
            except Exception as e:
                print(f"Ошибка загрузки шаблонов: {e}")

        if self.edit_script_id:
            self._load_script_data(self.edit_script_id)

    def on_preset_selected(self, index):
        """Обработка выбора пресета из БД"""
        if index <= 0:
            return

        script_id = self.preset_combo.itemData(index)
        if not script_id:
            return

        if self.table.rowCount() > 0:
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Заменить текущие этапы на выбранный шаблон?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.preset_combo.setCurrentIndex(0)
                return

        self._load_script_data(script_id)
        self.preset_combo.setCurrentIndex(0)

    def _load_script_data(self, script_id):
        """Загрузить данные сценария из БД в форму"""
        script_data = self.db_manager.get_script_with_stages(script_id)
        if script_data and script_data.get('stages'):
            self.edit_script_id = script_id
            self.table.setRowCount(0)
            self.script_name_input.setText(script_data['name'])

            for stage in script_data['stages']:
                minutes = stage['planned_duration_ms'] // 60000
                seconds = (stage['planned_duration_ms'] % 60000) // 1000
                self._add_stage_internal(stage['name'], minutes, seconds)

            self._update_info()
            self._update_apply_button()

    def load_existing_script(self):
        """Загрузить существующий сценарий для редактирования"""
        if not self.db_manager:
            return

        scripts = self.db_manager.get_all_scripts()
        if not scripts:
            QMessageBox.information(self, "Информация", "В базе данных нет сценариев.")
            return

        # Список названий для выбора
        # get_all_scripts() теперь возвращает List[Tuple[int, str]] (id, name)
        script_names = [f"{name} (ID: {sid})" for sid, name in scripts]
        script_ids = [sid for sid, name in scripts]

        item, ok = QInputDialog.getItem(
            self, "Загрузить сценарий",
            "Выберите сценарий для редактирования:",
            script_names, 0, False
        )

        if ok and item:
            index = script_names.index(item)
            script_id = script_ids[index]
            self._load_script_data(script_id)

    def delete_current_script(self):
        """Удалить текущий редактируемый сценарий"""
        if not self.edit_script_id:
            QMessageBox.information(self, "Информация",
                                    "Нет загруженного сценария для удаления.\n"
                                    "Загрузите сценарий кнопкой «📂 Загрузить сценарий».")
            return

        # Получаем название для подтверждения
        script_data = self.db_manager.get_script_with_stages(self.edit_script_id)
        script_name = script_data['name'] if script_data else "сценарий"

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить сценарий «{script_name}»?\n\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_script(self.edit_script_id)
            self.script_deleted.emit(self.edit_script_id)

            # Очищаем форму
            self.edit_script_id = None
            self.table.setRowCount(0)
            self.script_name_input.clear()
            self._update_info()
            self._update_apply_button()

            # Обновляем список шаблонов
            self.preset_combo.clear()
            self.preset_combo.addItem("-- Выберите шаблон --", None)
            self.load_presets()

            QMessageBox.information(self, "Успех", f"Сценарий «{script_name}» удалён.")

    def _update_apply_button(self):
        """Обновить текст кнопки Применить в зависимости от режима"""
        if self.edit_script_id:
            self.apply_btn.setText("✅ Обновить сценарий")
        else:
            self.apply_btn.setText("✅ Создать сценарий")

    def add_stage(self):
        """Добавить этап из полей ввода"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название этапа!")
            return

        minutes = self.minutes_input.value()
        seconds = self.seconds_input.value()

        if minutes == 0 and seconds == 0:
            QMessageBox.warning(self, "Ошибка", "Длительность этапа должна быть больше нуля!")
            return

        self._add_stage_internal(name, minutes, seconds)
        self.name_input.clear()
        self.name_input.setFocus()
        self._update_info()

    def _add_stage_internal(self, name: str, minutes: int, seconds: int):
        """Внутренний метод добавления этапа (без проверок)"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        num_item = QTableWidgetItem(str(row + 1))
        num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, num_item)

        self.table.setItem(row, 1, QTableWidgetItem(name))
        self.table.setItem(row, 2, QTableWidgetItem(str(minutes)))
        self.table.setItem(row, 3, QTableWidgetItem(str(seconds)))

    def remove_stage(self):
        """Удалить выбранный этап"""
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._renumber_stages()
            self._update_info()
        else:
            QMessageBox.information(self, "Информация", "Выберите этап для удаления")

    def move_stage_up(self):
        """Переместить этап вверх"""
        row = self.table.currentRow()
        if row > 0:
            self._swap_rows(row, row - 1)
            self.table.selectRow(row - 1)
            self._renumber_stages()

    def move_stage_down(self):
        """Переместить этап вниз"""
        row = self.table.currentRow()
        if row >= 0 and row < self.table.rowCount() - 1:
            self._swap_rows(row, row + 1)
            self.table.selectRow(row + 1)
            self._renumber_stages()

    def _swap_rows(self, row1: int, row2: int):
        """Поменять местами две строки"""
        for col in range(self.table.columnCount()):
            item1 = self.table.takeItem(row1, col)
            item2 = self.table.takeItem(row2, col)
            self.table.setItem(row1, col, item2)
            self.table.setItem(row2, col, item1)

    def _renumber_stages(self):
        """Перенумеровать этапы после удаления/перемещения"""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0):
                self.table.item(row, 0).setText(str(row + 1))

    def _update_info(self):
        """Обновить информационную строку"""
        count = self.table.rowCount()
        if count == 0:
            self.info_label.setText("Нет этапов. Добавьте хотя бы один этап.")
            return

        total_seconds = 0
        for row in range(count):
            try:
                mins_item = self.table.item(row, 2)
                secs_item = self.table.item(row, 3)
                if mins_item and secs_item:
                    mins = int(mins_item.text())
                    secs = int(secs_item.text())
                    total_seconds += mins * 60 + secs
            except:
                pass

        total_min = total_seconds // 60
        total_sec = total_seconds % 60
        self.info_label.setText(
            f"Этапов: {count} | Общая длительность: {total_min:02d}:{total_sec:02d}"
        )

    def apply_script(self):
        """Применить сценарий (создать новый или обновить существующий)"""
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы один этап!")
            return

        script_name = self.script_name_input.text().strip()
        if not script_name:
            QMessageBox.warning(self, "Ошибка", "Введите название сценария!")
            return

        script = PresentationScript(name=script_name)

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 1)
            min_item = self.table.item(row, 2)
            sec_item = self.table.item(row, 3)

            if not name_item:
                continue

            name = name_item.text().strip()
            if not name:
                QMessageBox.warning(self, "Ошибка", f"Этап {row + 1}: название не может быть пустым!")
                return

            try:
                minutes = int(min_item.text()) if min_item else 0
                seconds = int(sec_item.text()) if sec_item else 0
            except ValueError:
                QMessageBox.warning(self, "Ошибка", f"Этап '{name}': некорректное значение времени!")
                return

            if minutes == 0 and seconds == 0:
                QMessageBox.warning(self, "Ошибка", f"Этап '{name}': длительность должна быть больше нуля!")
                return

            duration_ms = (minutes * 60 + seconds) * 1000
            stage = PresentationStage(name, duration_ms)
            script.add_stage(stage)

        # Сохраняем edit_script_id в скрипт для последующей обработки
        script._edit_script_id = self.edit_script_id

        # НЕ сохраняем в БД здесь — это сделает settings_window
        self.script_applied.emit(script)
        self.close()