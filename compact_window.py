from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QResizeEvent, QFontMetrics
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QTimer
from PyQt6.QtGui import QMouseEvent


class CompactWindow(QWidget):
    """Компактное окно таймера поверх всех окон - изменяемый размер"""

    closed = pyqtSignal()
    toggle_full = pyqtSignal()
    toggle_timer = pyqtSignal()
    reset_timer = pyqtSignal()
    finish_presentation = pyqtSignal()
    show_settings = pyqtSignal()
    show_statistics = pyqtSignal()
    quick_time_3 = pyqtSignal()
    quick_time_5 = pyqtSignal()
    quick_time_7 = pyqtSignal()
    quick_time_10 = pyqtSignal()
    mode_countdown = pyqtSignal()
    mode_countup = pyqtSignal()
    mode_both = pyqtSignal()
    toggle_transparent_mode = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.drag_position = None
        self.current_opacity = 1.0
        self.current_bg_color = "#2E7D32"
        self.current_text_color = "#FFFFFF"
        self.current_mode = "single"
        self.current_main_text = "05:00"
        self.current_secondary_text = ""
        self.transparent_mode = False

        self.default_width = 300
        self.default_height = 180
        self.min_width = 180
        self.min_height = 100
        self.max_width = 2000
        self.max_height = 1200

        # Масштабирование колёсиком мыши
        self.scale = 1.0
        self.min_scale = 0.3
        self.max_scale = 3.0

        # Сохраняем исходный размер окна
        self.original_width = self.default_width
        self.original_height = self.default_height

        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        """Настройка интерфейса компактного окна"""
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(self.min_width, self.min_height)
        self.resize(self.default_width, self.default_height)

        self.container = QWidget(self)
        self.container.setObjectName("container")

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        self.time_label = QLabel("05:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setWordWrap(False)
        self.time_label.setObjectName("time_label")

        self.secondary_time_label = QLabel("")
        self.secondary_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.secondary_time_label.setWordWrap(False)
        self.secondary_time_label.setObjectName("secondary_time_label")
        self.secondary_time_label.hide()

        layout.addWidget(self.time_label, 1)
        layout.addWidget(self.secondary_time_label, 1)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container)
        main_layout.setContentsMargins(5, 5, 5, 5)

        self.setMouseTracking(True)

        self.resizing = False
        self.resize_edge = None
        self.resize_start_pos = None
        self.resize_start_geometry = None
        self.resize_margin = 10

    def get_resize_edge(self, pos):
        """Определяет, за какой край/угол потянули мышкой"""
        x, y = pos.x(), pos.y()
        width, height = self.width(), self.height()
        margin = self.resize_margin

        if x <= margin and y <= margin:
            return "top-left"
        if x >= width - margin and y <= margin:
            return "top-right"
        if x <= margin and y >= height - margin:
            return "bottom-left"
        if x >= width - margin and y >= height - margin:
            return "bottom-right"
        if x <= margin:
            return "left"
        if x >= width - margin:
            return "right"
        if y <= margin:
            return "top"
        if y >= height - margin:
            return "bottom"
        return None

    def update_cursor(self, pos):
        """Обновляет курсор в зависимости от позиции"""
        edge = self.get_resize_edge(pos)
        cursors = {
            "top-left": Qt.CursorShape.SizeFDiagCursor,
            "bottom-right": Qt.CursorShape.SizeFDiagCursor,
            "top-right": Qt.CursorShape.SizeBDiagCursor,
            "bottom-left": Qt.CursorShape.SizeBDiagCursor,
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
        }
        if edge in cursors:
            self.setCursor(cursors[edge])
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def setup_shortcuts(self):
        """Настройка горячих клавиш в компактном окне"""
        # Ctrl+Space - Старт/Пауза
        shortcut_space = QShortcut(QKeySequence("Ctrl+Space"), self)
        shortcut_space.activated.connect(self.toggle_timer.emit)

        # Ctrl+R - Сброс
        shortcut_reset = QShortcut(QKeySequence("Ctrl+R"), self)
        shortcut_reset.activated.connect(self.reset_timer.emit)

        # Ctrl+H - Выход из компактного режима
        shortcut_toggle_full = QShortcut(QKeySequence("Ctrl+H"), self)
        shortcut_toggle_full.activated.connect(self.toggle_full.emit)

        # Ctrl+F - Завершить выступление
        shortcut_finish = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_finish.activated.connect(self.finish_presentation.emit)

        # Ctrl+S - Настройки
        shortcut_settings = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_settings.activated.connect(self.show_settings.emit)

        # Ctrl+1..4 - Быстрое время
        shortcut_time_3 = QShortcut(QKeySequence("Ctrl+1"), self)
        shortcut_time_3.activated.connect(self.quick_time_3.emit)

        shortcut_time_5 = QShortcut(QKeySequence("Ctrl+2"), self)
        shortcut_time_5.activated.connect(self.quick_time_5.emit)

        shortcut_time_7 = QShortcut(QKeySequence("Ctrl+3"), self)
        shortcut_time_7.activated.connect(self.quick_time_7.emit)

        shortcut_time_10 = QShortcut(QKeySequence("Ctrl+4"), self)
        shortcut_time_10.activated.connect(self.quick_time_10.emit)

        # Ctrl+D/U/B - Режимы таймера
        shortcut_mode_down = QShortcut(QKeySequence("Ctrl+D"), self)
        shortcut_mode_down.activated.connect(self.mode_countdown.emit)

        shortcut_mode_up = QShortcut(QKeySequence("Ctrl+U"), self)
        shortcut_mode_up.activated.connect(self.mode_countup.emit)

        shortcut_mode_both = QShortcut(QKeySequence("Ctrl+B"), self)
        shortcut_mode_both.activated.connect(self.mode_both.emit)

        shortcut_transparent = QShortcut(QKeySequence("Ctrl+T"), self)
        shortcut_transparent.activated.connect(self.toggle_transparent_mode)

        shortcut_statistics = QShortcut(QKeySequence("Ctrl+G"), self)
        shortcut_statistics.activated.connect(self.show_statistics.emit)

    def update_display(self, time_str: str, bg_color: str, text_color: str):
        """Обновление отображения"""
        self.current_bg_color = bg_color
        self.current_text_color = text_color
        self.transparent_mode = (bg_color == "transparent")

        if " / " in time_str:
            self.current_mode = "both"
            parts = time_str.split(" / ")
            self.current_main_text = parts[0].strip()
            self.current_secondary_text = parts[1].strip().replace('+', '')

            # Устанавливаем текст в QLabel
            self.time_label.setText(self.current_main_text)
            self.secondary_time_label.setText(self.current_secondary_text)
            self.secondary_time_label.show()
        else:
            self.current_mode = "single"
            # ВАЖНО: сохраняем ПОЛНЫЙ текст, включая + и -
            self.current_main_text = time_str
            self.current_secondary_text = ""

            # Устанавливаем текст в QLabel
            self.time_label.setText(self.current_main_text)
            self.secondary_time_label.hide()

        self.update_styles()
        # ВАЖНО: вызываем пересчет шрифта ПОСЛЕ обновления текста
        self.calculate_and_set_font_size()
        # Принудительно обновляем геометрию
        self.updateGeometry()

    def update_styles(self):
        """Обновляет стили"""
        if self.transparent_mode:
            self.container.setStyleSheet("""
                #container {
                    background-color: transparent;
                    border: none;
                }
            """)

            self.time_label.setStyleSheet(f"""
                #time_label {{
                    color: {self.current_text_color};
                    background-color: transparent;
                    font-weight: bold;
                    border: none;
                }}
            """)

            self.secondary_time_label.setStyleSheet(f"""
                #secondary_time_label {{
                    color: {self.current_text_color};
                    background-color: transparent;
                    font-weight: normal;
                    border: none;
                }}
            """)
        else:
            self.container.setStyleSheet(f"""
                #container {{
                    background-color: {self.current_bg_color};
                    border-radius: 10px;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                }}
            """)

            self.time_label.setStyleSheet(f"""
                #time_label {{
                    color: {self.current_text_color};
                    background-color: transparent;
                    font-weight: bold;
                    border: none;
                }}
            """)

            self.secondary_time_label.setStyleSheet(f"""
                #secondary_time_label {{
                    color: {self.current_text_color};
                    background-color: transparent;
                    font-weight: normal;
                    border: none;
                }}
            """)

    def calculate_and_set_font_size(self):
        """Рассчитывает оптимальный размер шрифта, используя наихудший сценарий"""
        if self.width() <= 0 or self.height() <= 0:
            return

        available_width = self.container.width() - 30
        available_height = self.container.height() - 30

        if available_width <= 0 or available_height <= 0:
            return

        def get_worst_case_text(text):
            """
            Заменяет все цифры на '0' (самую широкую цифру в Arial),
            чтобы получить максимально возможную ширину текста.
            Знаки + и - оставляет как есть.
            """
            result = []
            for char in text:
                if char.isdigit():
                    result.append('0')  # '0' обычно самая широкая цифра
                else:
                    result.append(char)
            return ''.join(result)

        if self.current_mode == "both":
            available_height_per_label = available_height / 2

            # Используем "худший" текст для расчета
            main_text = get_worst_case_text(self.current_main_text if self.current_main_text else "00:00")
            secondary_text = get_worst_case_text(
                self.current_secondary_text if self.current_secondary_text else "00:00")

            main_font_size = self.find_best_font_size(
                main_text, available_width, available_height_per_label, is_bold=True
            )

            secondary_font_size = self.find_best_font_size(
                secondary_text, available_width, available_height_per_label, is_bold=False
            )

            main_font_size = max(12, main_font_size)
            secondary_font_size = max(10, secondary_font_size)

            main_font = QFont("Arial", main_font_size, QFont.Weight.Bold)
            secondary_font = QFont("Arial", secondary_font_size, QFont.Weight.Normal)

            self.time_label.setFont(main_font)
            self.secondary_time_label.setFont(secondary_font)

        else:
            # Используем "худший" текст для расчета
            real_text = self.current_main_text if self.current_main_text else "00:00"
            worst_case = get_worst_case_text(real_text)

            font_size = self.find_best_font_size(
                worst_case, available_width, available_height, is_bold=True
            )

            font_size = max(14, font_size)
            main_font = QFont("Arial", font_size, QFont.Weight.Bold)
            self.time_label.setFont(main_font)

    def find_best_font_size(self, text: str, max_width: int, max_height: int, is_bold: bool = True) -> int:
        """Находит максимальный размер шрифта"""
        if not text:
            return 10

        for size in range(120, 5, -2):
            font = QFont("Arial", size, QFont.Weight.Bold if is_bold else QFont.Weight.Normal)
            metrics = QFontMetrics(font)
            text_rect = metrics.boundingRect(text)

            if text_rect.width() <= max_width and text_rect.height() <= max_height:
                return size

        return 10

    def set_opacity(self, opacity: float):
        """Установка прозрачности окна"""
        self.current_opacity = max(0.0, min(1.0, opacity))
        self.setWindowOpacity(self.current_opacity)

    def resizeEvent(self, event: QResizeEvent):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)
        self.container.setGeometry(0, 0, self.width(), self.height())
        self.calculate_and_set_font_size()

    def wheelEvent(self, event):
        """Масштабирование колёсиком мыши"""
        delta = event.angleDelta().y()

        if delta > 0:
            self.scale = min(self.scale + 0.1, self.max_scale)
        else:
            self.scale = max(self.scale - 0.1, self.min_scale)

        new_width = int(self.original_width * self.scale)
        new_height = int(self.original_height * self.scale)

        new_width = max(self.min_width, min(new_width, self.max_width))
        new_height = max(self.min_height, min(new_height, self.max_height))

        old_center = self.geometry().center()

        self.resize(new_width, new_height)

        new_geometry = self.geometry()
        new_geometry.moveCenter(old_center)
        self.setGeometry(new_geometry)

        self.calculate_and_set_font_size()

    def scale_up(self):
        """Увеличить масштаб"""
        self.scale = min(self.scale + 0.1, self.max_scale)
        new_width = int(self.original_width * self.scale)
        new_height = int(self.original_height * self.scale)

        new_width = max(self.min_width, min(new_width, self.max_width))
        new_height = max(self.min_height, min(new_height, self.max_height))

        self.resize(new_width, new_height)
        self.calculate_and_set_font_size()

    def scale_down(self):
        """Уменьшить масштаб"""
        self.scale = max(self.scale - 0.1, self.min_scale)
        new_width = int(self.original_width * self.scale)
        new_height = int(self.original_height * self.scale)

        new_width = max(self.min_width, min(new_width, self.max_width))
        new_height = max(self.min_height, min(new_height, self.max_height))

        self.resize(new_width, new_height)
        self.calculate_and_set_font_size()

    def mousePressEvent(self, event: QMouseEvent):
        """Обработка нажатия мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self.resize_edge = self.get_resize_edge(pos)

            if self.resize_edge:
                self.resizing = True
                self.resize_start_pos = event.globalPosition().toPoint()
                self.resize_start_geometry = self.geometry()
                event.accept()
            else:
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Обработка перемещения мыши"""
        pos = event.position().toPoint()

        if not self.resizing and not self.dragging:
            self.update_cursor(pos)

        if self.resizing and self.resize_start_pos and self.resize_start_geometry:
            self.resize_window(event.globalPosition().toPoint())
            event.accept()
        elif self.dragging and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def resize_window(self, global_pos):
        """Изменяет размер окна"""
        delta = global_pos - self.resize_start_pos
        new_geometry = QRect(self.resize_start_geometry)

        if "left" in self.resize_edge:
            new_width = self.resize_start_geometry.width() - delta.x()
            new_width = max(self.min_width, min(new_width, self.max_width))
            new_geometry.setLeft(self.resize_start_geometry.right() - new_width)

        if "right" in self.resize_edge:
            new_width = self.resize_start_geometry.width() + delta.x()
            new_width = max(self.min_width, min(new_width, self.max_width))
            new_geometry.setWidth(new_width)

        if "top" in self.resize_edge:
            new_height = self.resize_start_geometry.height() - delta.y()
            new_height = max(self.min_height, min(new_height, self.max_height))
            new_geometry.setTop(self.resize_start_geometry.bottom() - new_height)

        if "bottom" in self.resize_edge:
            new_height = self.resize_start_geometry.height() + delta.y()
            new_height = max(self.min_height, min(new_height, self.max_height))
            new_geometry.setHeight(new_height)

        self.setGeometry(new_geometry)

        if self.original_width > 0:
            self.scale = self.width() / self.original_width
            self.scale = max(self.min_scale, min(self.scale, self.max_scale))

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Обработка отпускания мыши"""
        self.dragging = False
        self.resizing = False
        self.resize_edge = None
        self.resize_start_pos = None
        self.resize_start_geometry = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Двойной клик для переключения в обычный режим"""
        self.toggle_full.emit()

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.closed.emit()
        event.accept()

    def get_geometry(self):
        """Возвращает текущую геометрию окна для сохранения"""
        return self.geometry()

    def set_geometry_from_saved(self, rect):
        """Восстанавливает сохраненную геометрию"""
        if rect and rect.width() >= self.min_width and rect.height() >= self.min_height:
            width = min(max(rect.width(), self.min_width), self.max_width)
            height = min(max(rect.height(), self.min_height), self.max_height)
            self.setGeometry(rect.x(), rect.y(), width, height)

            self.original_width = width
            self.original_height = height
            self.scale = 1.0

            QTimer.singleShot(50, self.calculate_and_set_font_size)
        else:
            screen = self.screen().availableGeometry()
            self.setGeometry(
                screen.width() - self.default_width - 20,
                50,
                self.default_width,
                self.default_height
            )
            self.original_width = self.default_width
            self.original_height = self.default_height
            self.scale = 1.0