from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QHeaderView, QMessageBox, QFileDialog, QGroupBox,
    QComboBox, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


class StatisticsWindow(QWidget):
    """Окно статистики и аналитики выступлений"""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Статистика выступлений")

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )

        # Инициализируем атрибуты для метрик
        self.total_count_value = None
        self.avg_duration_value = None
        self.total_pauses_value = None
        self.overtime_rate_value = None

        # Инициализируем canvas'ы (убрали timeline)
        self.duration_chart = None
        self.mode_chart = None
        self.duration_ax = None
        self.mode_ax = None

        # Для интерактивного дашборда
        self.dashboard_canvas = None
        self.dashboard_ax = None

        self.setup_ui()

        self.showMaximized()

        QTimer.singleShot(100, self.load_data)

    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)

        # Заголовок
        title = QLabel("📊 СТАТИСТИКА И АНАЛИТИКА")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2C3E50; padding: 10px;")
        layout.addWidget(title)

        # Панель фильтров
        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("Период:"))

        self.period_combo = QComboBox()
        self.period_combo.addItems(["Все время", "Последние 7 дней", "Последние 30 дней", "Этот месяц"])
        self.period_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.period_combo)

        filter_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(self.refresh_btn)

        layout.addWidget(filter_group)

        # Вкладки
        self.tab_widget = QTabWidget()

        # Вкладка: Общая статистика
        self.stats_tab = QWidget()
        self.setup_stats_tab()
        self.tab_widget.addTab(self.stats_tab, "📈 Общая статистика")

        # Вкладка: Список выступлений
        self.list_tab = QWidget()
        self.setup_list_tab()
        self.tab_widget.addTab(self.list_tab, "📋 Список выступлений")

        # Вкладка: Интерактивный дашборд
        self.dashboard_tab = QWidget()
        self.setup_dashboard_tab()
        self.tab_widget.addTab(self.dashboard_tab, "📊 Интерактивный дашборд")

        layout.addWidget(self.tab_widget, 1)

        # Кнопки экспорта
        export_layout = QHBoxLayout()
        export_layout.addStretch()

        self.export_json_btn = QPushButton("📄 Экспорт в JSON")
        self.export_json_btn.clicked.connect(self.export_to_json)
        export_layout.addWidget(self.export_json_btn)

        self.export_csv_btn = QPushButton("📊 Экспорт в CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        export_layout.addWidget(self.export_csv_btn)

        self.export_pdf_btn = QPushButton("📕 Экспорт в PDF")  # ← ДОБАВИТЬ
        self.export_pdf_btn.clicked.connect(self.export_to_pdf)  # ← ДОБАВИТЬ
        export_layout.addWidget(self.export_pdf_btn)  # ← ДОБАВИТЬ

        layout.addLayout(export_layout)

        # Стиль
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #BDC3C7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QTableWidget {
                gridline-color: #BDC3C7;
                alternate-background-color: #F8F9FA;
            }
            QHeaderView::section {
                background-color: #ECF0F1;
                padding: 5px;
                border: 1px solid #BDC3C7;
            }
            QComboBox {
                padding: 3px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                background-color: white;
            }
        """)

    def setup_stats_tab(self):
        """Настройка вкладки общей статистики"""
        layout = QVBoxLayout(self.stats_tab)

        # Карточки с метриками
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(10)

        self._create_metric_card(metrics_layout,  "📊 Всего выступлений", "0", "total_count")
        self._create_metric_card(metrics_layout,  "⏱️ Средняя длительность", "0 мин", "avg_duration")
        self._create_metric_card(metrics_layout,  "⏸️ Всего пауз", "0", "total_pauses")
        self._create_metric_card(metrics_layout,  "⚠️ Превышений", "0%", "overtime_rate")

        layout.addLayout(metrics_layout)

        # Два графика в одном ряду (убрали динамику)
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(15)

        # График 1: Распределение длительности
        self.duration_chart = FigureCanvas(Figure(figsize=(7, 6)))
        self.duration_ax = self.duration_chart.figure.add_subplot(111)
        charts_layout.addWidget(self.duration_chart)

        # График 2: Режимы таймера (круговая диаграмма)
        self.mode_chart = FigureCanvas(Figure(figsize=(7, 6)))
        self.mode_ax = self.mode_chart.figure.add_subplot(111)
        charts_layout.addWidget(self.mode_chart)

        layout.addLayout(charts_layout)

    def _create_metric_card(self, parent_layout, title, value, attr_name):
        """Создать компактную карточку с метрикой (без иконки)"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)  # Уменьшаем расстояние между элементами
        layout.setContentsMargins(10, 5, 10, 5)  # Уменьшаем отступы

        # Надпись
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 19, QFont.Weight.Normal))
        title_label.setStyleSheet("color: #2C3E50;")

        # Значение (цифра)
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        value_label.setStyleSheet("color: #2C3E50;")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        parent_layout.addWidget(card)

        # Сохраняем ссылку на виджет со значением
        setattr(self, f"{attr_name}_value", value_label)

    def setup_list_tab(self):
        """Настройка вкладки со списком выступлений"""
        layout = QVBoxLayout(self.list_tab)

        # Панель фильтров для таблицы
        filter_panel = QHBoxLayout()

        filter_panel.addWidget(QLabel("Фильтры:"))

        # Фильтр по режиму
        filter_panel.addWidget(QLabel("Режим:"))
        self.mode_filter = QComboBox()
        self.mode_filter.addItems(["Все", "Обратный", "Прямой", "Двойной"])
        self.mode_filter.currentTextChanged.connect(self.apply_table_filters)
        filter_panel.addWidget(self.mode_filter)

        # Фильтр по превышению
        filter_panel.addWidget(QLabel("Превышение:"))
        self.overtime_filter = QComboBox()
        self.overtime_filter.addItems(["Все", "Без превышения", "С превышением"])
        self.overtime_filter.currentTextChanged.connect(self.apply_table_filters)
        filter_panel.addWidget(self.overtime_filter)

        # Фильтр по паузам
        filter_panel.addWidget(QLabel("Паузы:"))
        self.pause_filter = QComboBox()
        self.pause_filter.addItems(["Все", "Без пауз", "С паузами"])
        self.pause_filter.currentTextChanged.connect(self.apply_table_filters)
        filter_panel.addWidget(self.pause_filter)

        filter_panel.addStretch()

        # Кнопка сброса фильтров
        self.clear_filters_btn = QPushButton("Сбросить фильтры")
        self.clear_filters_btn.clicked.connect(self.clear_table_filters)
        filter_panel.addWidget(self.clear_filters_btn)

        layout.addLayout(filter_panel)

        # Таблица
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # ← ДОБАВИТЬ ЭТУ СТРОКУ

        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Дата", "Время", "Режим",
            "Длительность", "Паузы", "Превышение", "Между этапами"
        ])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSortIndicatorShown(True)

        layout.addWidget(self.table)

        # Кнопка просмотра деталей
        detail_btn = QPushButton("📖 Показать детали выступления")
        detail_btn.clicked.connect(self.show_presentation_details)
        layout.addWidget(detail_btn)

        # Хранилище всех данных для фильтрации
        self.all_presentations_data = []

    def setup_dashboard_tab(self):
        """Настройка вкладки интерактивного дашборда"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        dashboard_layout = QVBoxLayout(scroll_content)

        # Панель выбора параметров
        controls_group = QGroupBox("Настройки графика")
        controls_layout = QGridLayout(controls_group)

        controls_layout.addWidget(QLabel("Тип графика:"), 0, 0)
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems([
            "Гистограмма",
            "Линейный график",
            "Столбчатая диаграмма",
            "Точечная диаграмма",
            "Круговая диаграмма"
        ])
        self.chart_type_combo.currentTextChanged.connect(self.update_dashboard)
        controls_layout.addWidget(self.chart_type_combo, 0, 1)

        controls_layout.addWidget(QLabel("Ось X (данные):"), 1, 0)
        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItems([
            "Длительность (мин)",
            "Количество пауз",
            "Превышение (сек)"
        ])
        self.x_axis_combo.currentTextChanged.connect(self.update_dashboard)
        controls_layout.addWidget(self.x_axis_combo, 1, 1)

        controls_layout.addWidget(QLabel("Ось Y (для сравнения):"), 2, 0)
        self.y_axis_combo = QComboBox()
        self.y_axis_combo.addItems([
            "Не используется",
            "Длительность (мин)",
            "Количество пауз",
            "Превышение (сек)"
        ])
        self.y_axis_combo.currentTextChanged.connect(self.update_dashboard)
        controls_layout.addWidget(self.y_axis_combo, 2, 1)

        controls_layout.addWidget(QLabel("Фильтр по режиму:"), 3, 0)
        self.dash_mode_filter = QComboBox()
        self.dash_mode_filter.addItems(["Все", "Обратный отсчёт", "Прямой отсчёт", "Двойной режим"])
        self.dash_mode_filter.currentTextChanged.connect(self.update_dashboard)
        controls_layout.addWidget(self.dash_mode_filter, 3, 1)

        self.update_dash_btn = QPushButton("🔄 Построить график")
        self.update_dash_btn.clicked.connect(self.update_dashboard)
        controls_layout.addWidget(self.update_dash_btn, 4, 0, 1, 2)

        dashboard_layout.addWidget(controls_group)

        # Холст для графика
        self.dashboard_canvas = FigureCanvas(Figure(figsize=(10, 6)))
        self.dashboard_ax = self.dashboard_canvas.figure.add_subplot(111)
        dashboard_layout.addWidget(self.dashboard_canvas)

        # Статистическая информация
        stats_group = QGroupBox("Статистика по выбранным данным")
        stats_layout = QVBoxLayout(stats_group)
        self.dashboard_stats_label = QLabel("Выберите параметры и нажмите 'Построить график'")
        self.dashboard_stats_label.setWordWrap(True)
        self.dashboard_stats_label.setStyleSheet("color: #2C3E50; font-size: 12px;")
        stats_layout.addWidget(self.dashboard_stats_label)
        dashboard_layout.addWidget(stats_group)

        scroll.setWidget(scroll_content)

        main_layout = QVBoxLayout(self.dashboard_tab)
        main_layout.addWidget(scroll)

    def load_data(self):
        """Загрузка и обновление всех данных"""
        try:
            presentations = self.db_manager.get_all_presentations(limit=500)

            # Применяем фильтр по дате
            filtered = self.apply_filter(presentations)

            # Сохраняем все данные
            self.all_presentations_data = filtered

            # Обновляем метрики
            self.update_metrics(filtered)

            # Обновляем графики
            self.update_charts(filtered)

            # Обновляем таблицу
            self.update_table(filtered)

            # Сбрасываем фильтры таблицы
            self.clear_table_filters()

            # Обновляем интерактивный дашборд
            self.update_dashboard()

        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            import traceback
            traceback.print_exc()

    def apply_filter(self, presentations):
        """Применить фильтр по дате"""
        if self.period_combo.currentIndex() == 0:  # Все время
            return presentations

        today = datetime.now().date()

        if self.period_combo.currentIndex() == 1:  # Последние 7 дней
            start_date = today - timedelta(days=7)
        elif self.period_combo.currentIndex() == 2:  # Последние 30 дней
            start_date = today - timedelta(days=30)
        else:  # Этот месяц
            start_date = today.replace(day=1)

        filtered = []
        for p in presentations:
            try:
                p_date = datetime.fromisoformat(p['start_time']).date()
                if p_date >= start_date:
                    filtered.append(p)
            except:
                filtered.append(p)

        return filtered

    def update_metrics(self, presentations):
        """Обновление метрик"""
        total = len(presentations)

        if not hasattr(self, 'total_count_value') or self.total_count_value is None:
            return

        if total == 0:
            self.total_count_value.setText("0")
            self.avg_duration_value.setText("0 мин")
            self.total_pauses_value.setText("0")
            self.overtime_rate_value.setText("0%")
            return

        # Средняя длительность
        total_duration = sum(p.get('actual_duration_ms', 0) for p in presentations) / 1000 / 60
        avg_duration = total_duration / total

        # Всего пауз
        total_pauses = sum(p.get('total_pause_count', 0) for p in presentations)

        # Процент превышений
        overtime_count = sum(1 for p in presentations if p.get('overtime_ms', 0) > 0)
        overtime_rate = (overtime_count / total) * 100

        self.total_count_value.setText(str(total))
        self.avg_duration_value.setText(f"{avg_duration:.1f} мин")
        self.total_pauses_value.setText(str(total_pauses))
        self.overtime_rate_value.setText(f"{overtime_rate:.1f}%")

    def update_charts(self, presentations):
        """Обновление графиков (только гистограмма и круговая)"""
        try:
            if not presentations or self.duration_ax is None:
                if self.duration_ax:
                    self._clear_chart(self.duration_ax, "Нет данных")
                    self._clear_chart(self.mode_ax, "Нет данных")
                return

            # График 1: Гистограмма длительности
            self.duration_ax.clear()
            durations = [p.get('actual_duration_ms', 0) / 1000 / 60 for p in presentations]
            if durations:
                bins = min(10, len(set(durations))) if len(set(durations)) > 1 else 1
                self.duration_ax.hist(durations, bins=bins, color='#3498DB', edgecolor='white', alpha=0.7)
            self.duration_ax.set_xlabel('Длительность (минуты)')
            self.duration_ax.set_ylabel('Количество выступлений')
            self.duration_ax.set_title('Распределение длительности выступлений')
            self.duration_ax.grid(True, alpha=0.3)
            self.duration_chart.draw()

            # График 2: Режимы таймера (круговая диаграмма)
            self.mode_ax.clear()
            modes = {}
            for p in presentations:
                mode = p.get('timer_mode', 'unknown')
                modes[mode] = modes.get(mode, 0) + 1

            if modes:
                mode_names = {
                    'countdown': 'Обратный отсчёт',
                    'countup': 'Прямой отсчёт',
                    'both': 'Двойной режим'
                }
                labels = [mode_names.get(m, m) for m in modes.keys()]
                values = list(modes.values())
                colors = ['#2ECC71', '#3498DB', '#9B59B6']
                self.mode_ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors[:len(labels)])
                self.mode_ax.set_title('Используемые режимы таймера')
            self.mode_chart.draw()

        except Exception as e:
            print(f"Ошибка обновления графиков: {e}")

    def update_dashboard(self):
        """Обновление интерактивного дашборда"""
        try:
            if not self.all_presentations_data:
                if self.dashboard_ax:
                    self._clear_chart(self.dashboard_ax, "Нет данных для отображения")
                    self.dashboard_canvas.draw()
                    self.dashboard_stats_label.setText("Нет данных для анализа")
                return

            # Применяем фильтр по режиму
            mode_filter = self.dash_mode_filter.currentText()
            data = self.all_presentations_data.copy()

            if mode_filter != "Все":
                mode_map = {
                    "Обратный отсчёт": "countdown",
                    "Прямой отсчёт": "countup",
                    "Двойной режим": "both"
                }
                target_mode = mode_map.get(mode_filter)
                if target_mode:
                    data = [p for p in data if p.get('timer_mode') == target_mode]

            if not data:
                self._clear_chart(self.dashboard_ax, "Нет данных для выбранного фильтра")
                self.dashboard_canvas.draw()
                self.dashboard_stats_label.setText("Нет данных для выбранного фильтра")
                return

            # Подготовка данных для осей
            x_data = []
            y_data = []

            # Получаем данные для оси X
            x_choice = self.x_axis_combo.currentText()
            if x_choice == "Длительность (мин)":
                x_data = [p.get('actual_duration_ms', 0) / 1000 / 60 for p in data]
            elif x_choice == "Количество пауз":
                x_data = [p.get('total_pause_count', 0) for p in data]
            elif x_choice == "Превышение (сек)":
                x_data = [p.get('overtime_ms', 0) / 1000 for p in data]

            # Получаем данные для оси Y (если нужно)
            y_choice = self.y_axis_combo.currentText()
            use_y = y_choice != "Не используется"
            if use_y:
                if y_choice == "Длительность (мин)":
                    y_data = [p.get('actual_duration_ms', 0) / 1000 / 60 for p in data]
                elif y_choice == "Количество пауз":
                    y_data = [p.get('total_pause_count', 0) for p in data]
                elif y_choice == "Превышение (сек)":
                    y_data = [p.get('overtime_ms', 0) / 1000 for p in data]

            # Очищаем и строим график
            self.dashboard_ax.clear()
            chart_type = self.chart_type_combo.currentText()

            if chart_type == "Гистограмма":
                self.dashboard_ax.hist(x_data, bins=min(20, len(set(x_data))), color='#3498DB', edgecolor='white',
                                       alpha=0.7)
                self.dashboard_ax.set_xlabel(self.x_axis_combo.currentText())
                self.dashboard_ax.set_ylabel('Частота')
                self.dashboard_ax.set_title(f'Распределение: {self.x_axis_combo.currentText()}')
                self.dashboard_ax.grid(True, alpha=0.3)

                stats_text = self._calculate_statistics(x_data, self.x_axis_combo.currentText())
                self.dashboard_stats_label.setText(stats_text)

            elif chart_type == "Линейный график":
                indices = list(range(1, len(x_data) + 1))
                self.dashboard_ax.plot(indices, x_data, color='#E74C3C', marker='o', linewidth=2, markersize=4)
                self.dashboard_ax.set_xlabel('Номер выступления (по порядку)')
                self.dashboard_ax.set_ylabel(self.x_axis_combo.currentText())
                self.dashboard_ax.set_title(f'Тренд: {self.x_axis_combo.currentText()} по выступлениям')
                self.dashboard_ax.grid(True, alpha=0.3)

                stats_text = self._calculate_statistics(x_data, self.x_axis_combo.currentText())
                self.dashboard_stats_label.setText(stats_text)

            elif chart_type == "Столбчатая диаграмма":
                indices = list(range(1, len(x_data) + 1))
                if len(x_data) > 50:
                    indices = indices[:50]
                    x_data_display = x_data[:50]
                else:
                    x_data_display = x_data
                self.dashboard_ax.bar(indices, x_data_display, color='#27AE60', alpha=0.7)
                self.dashboard_ax.set_xlabel('Номер выступления (по порядку)')
                self.dashboard_ax.set_ylabel(self.x_axis_combo.currentText())
                self.dashboard_ax.set_title(f'Значения: {self.x_axis_combo.currentText()} по выступлениям')
                self.dashboard_ax.grid(True, alpha=0.3, axis='y')

                stats_text = self._calculate_statistics(x_data, self.x_axis_combo.currentText())
                self.dashboard_stats_label.setText(stats_text)

            elif chart_type == "Точечная диаграмма":
                if use_y and len(y_data) > 0:
                    self.dashboard_ax.scatter(x_data, y_data, color='#9B59B6', alpha=0.6, s=50)
                    self.dashboard_ax.set_xlabel(self.x_axis_combo.currentText())
                    self.dashboard_ax.set_ylabel(y_choice)
                    self.dashboard_ax.set_title(f'Корреляция: {self.x_axis_combo.currentText()} vs {y_choice}')
                    self.dashboard_ax.grid(True, alpha=0.3)

                    stats_text = self._calculate_correlation(x_data, y_data, self.x_axis_combo.currentText(), y_choice)
                    self.dashboard_stats_label.setText(stats_text)
                else:
                    indices = list(range(1, len(x_data) + 1))
                    self.dashboard_ax.scatter(indices, x_data, color='#9B59B6', alpha=0.6, s=50)
                    self.dashboard_ax.set_xlabel('Номер выступления (по порядку)')
                    self.dashboard_ax.set_ylabel(self.x_axis_combo.currentText())
                    self.dashboard_ax.set_title(f'Распределение: {self.x_axis_combo.currentText()} по выступлениям')
                    self.dashboard_ax.grid(True, alpha=0.3)

                    stats_text = self._calculate_statistics(x_data, self.x_axis_combo.currentText())
                    self.dashboard_stats_label.setText(stats_text)

            elif chart_type == "Круговая диаграмма":
                if len(x_data) > 0:
                    # Создаем категории на основе данных
                    if x_choice == "Длительность (мин)":
                        bins = [0, 2, 5, 10, 20, float('inf')]
                        labels = ['0-2 мин', '2-5 мин', '5-10 мин', '10-20 мин', '20+ мин']
                    elif x_choice == "Количество пауз":
                        bins = [0, 1, 3, 6, 10, float('inf')]
                        labels = ['0 пауз', '1-2 паузы', '3-5 пауз', '6-10 пауз', '10+ пауз']
                    elif x_choice == "Превышение (сек)":
                        bins = [0, 1, 30, 60, 120, float('inf')]
                        labels = ['нет', 'до 30 сек', '30-60 сек', '1-2 мин', '2+ мин']
                    else:
                        bins = []
                        labels = []

                    import numpy as np
                    digitized = np.digitize(x_data, bins)
                    counts = []
                    for i in range(1, len(bins) + 1):
                        count = np.sum(digitized == i)
                        if count > 0:
                            counts.append(count)

                    display_labels = []
                    for i, count in enumerate(counts):
                        if i < len(labels):
                            display_labels.append(labels[i])
                        else:
                            display_labels.append(f"Группа {i + 1}")

                    if counts:
                        colors = ['#3498DB', '#2ECC71', '#F39C12', '#E74C3C', '#9B59B6', '#1ABC9C']
                        self.dashboard_ax.pie(counts, labels=display_labels, autopct='%1.1f%%',
                                              colors=colors[:len(counts)], startangle=90)
                        self.dashboard_ax.set_title(f'Распределение: {self.x_axis_combo.currentText()}')

                        stats_text = self._calculate_statistics(x_data, self.x_axis_combo.currentText())
                        self.dashboard_stats_label.setText(stats_text)
                    else:
                        self.dashboard_ax.text(0.5, 0.5, "Недостаточно данных", ha='center', va='center')
                        self.dashboard_stats_label.setText("Недостаточно данных для построения диаграммы")

            self.dashboard_canvas.draw()

        except Exception as e:
            print(f"Ошибка обновления дашборда: {e}")
            import traceback
            traceback.print_exc()
            if self.dashboard_ax:
                self._clear_chart(self.dashboard_ax, f"Ошибка: {e}")
                self.dashboard_canvas.draw()
                self.dashboard_stats_label.setText(f"Ошибка построения графика: {e}")

    def _calculate_statistics(self, data, data_name):
        """Расчёт статистики для данных"""
        if not data:
            return "Нет данных"

        import numpy as np
        data_arr = np.array(data)

        stats = f"""📊 СТАТИСТИКА ДЛЯ ПОКАЗАТЕЛЯ: {data_name}

📌 Количество значений: {len(data_arr)}
📌 Среднее значение: {np.mean(data_arr):.2f}
📌 Медиана: {np.median(data_arr):.2f}
📌 Минимум: {np.min(data_arr):.2f}
📌 Максимум: {np.max(data_arr):.2f}
📌 Стандартное отклонение: {np.std(data_arr):.2f}"""
        return stats

    def _calculate_correlation(self, x_data, y_data, x_name, y_name):
        """Расчёт корреляции между двумя наборами данных"""
        if not x_data or not y_data or len(x_data) != len(y_data):
            return "Недостаточно данных для расчёта корреляции"

        import numpy as np
        x_arr = np.array(x_data)
        y_arr = np.array(y_data)

        corr = np.corrcoef(x_arr, y_arr)[0, 1]

        if corr > 0.7:
            interpretation = "Сильная положительная корреляция"
        elif corr > 0.3:
            interpretation = "Слабая положительная корреляция"
        elif corr < -0.7:
            interpretation = "Сильная отрицательная корреляция"
        elif corr < -0.3:
            interpretation = "Слабая отрицательная корреляция"
        else:
            interpretation = "Корреляция отсутствует"

        stats = f"""📊 КОРРЕЛЯЦИОННЫЙ АНАЛИЗ

📌 X: {x_name}
📌 Y: {y_name}

📈 Коэффициент корреляции Пирсона: {corr:.3f}
📌 Интерпретация: {interpretation}

💡 Коэффициент корреляции показывает связь между переменными:
   • > 0 — прямая связь (рост X ведёт к росту Y)
   • < 0 — обратная связь (рост X ведёт к снижению Y)
   • |r| > 0.7 — сильная связь
   • |r| < 0.3 — слабая связь"""
        return stats

    def _clear_chart(self, ax, message):
        """Очистить график и показать сообщение"""
        ax.clear()
        ax.text(0.5, 0.5, message, ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.set_xticks([])
        ax.set_yticks([])

    def apply_table_filters(self):
        """Применить фильтры к таблице"""
        if not self.all_presentations_data:
            return

        filtered = self.all_presentations_data.copy()

        mode_filter_text = self.mode_filter.currentText()
        if mode_filter_text != "Все":
            mode_map = {
                "Обратный": "countdown",
                "Прямой": "countup",
                "Двойной": "both"
            }
            target_mode = mode_map.get(mode_filter_text)
            if target_mode:
                filtered = [p for p in filtered if p.get('timer_mode') == target_mode]

        overtime_filter_text = self.overtime_filter.currentText()
        if overtime_filter_text == "Без превышения":
            filtered = [p for p in filtered if p.get('overtime_ms', 0) == 0]
        elif overtime_filter_text == "С превышением":
            filtered = [p for p in filtered if p.get('overtime_ms', 0) > 0]

        pause_filter_text = self.pause_filter.currentText()
        if pause_filter_text == "Без пауз":
            filtered = [p for p in filtered if p.get('total_pause_count', 0) == 0]
        elif pause_filter_text == "С паузами":
            filtered = [p for p in filtered if p.get('total_pause_count', 0) > 0]

        self.update_table(filtered)

    def clear_table_filters(self):
        """Сбросить все фильтры"""
        self.mode_filter.setCurrentIndex(0)
        self.overtime_filter.setCurrentIndex(0)
        self.pause_filter.setCurrentIndex(0)
        if self.all_presentations_data:
            self.update_table(self.all_presentations_data)

    def update_table(self, presentations):
        """Обновление таблицы выступлений"""
        self.table.setRowCount(len(presentations))
        self.table.setColumnCount(8)  # добавили колонку
        self.table.setHorizontalHeaderLabels([
            "ID", "Дата", "Время", "Режим",
            "Длительность", "Паузы", "Превышение", "Между этапами"
        ])

        for row, p in enumerate(presentations):
            id_item = QTableWidgetItem(str(p.get('id', '')))
            id_item.setData(Qt.ItemDataRole.UserRole, p.get('id', 0))
            self.table.setItem(row, 0, id_item)

            try:
                dt = datetime.fromisoformat(p.get('start_time', ''))
                self.table.setItem(row, 1, QTableWidgetItem(dt.strftime('%Y-%m-%d')))
                self.table.setItem(row, 2, QTableWidgetItem(dt.strftime('%H:%M:%S')))
            except:
                self.table.setItem(row, 1, QTableWidgetItem(''))
                self.table.setItem(row, 2, QTableWidgetItem(''))

            mode = p.get('timer_mode', '')
            mode_display = {
                'countdown': 'Обратный',
                'countup': 'Прямой',
                'both': 'Двойной'
            }.get(mode, mode)
            mode_item = QTableWidgetItem(mode_display)
            mode_item.setData(Qt.ItemDataRole.UserRole, mode)
            self.table.setItem(row, 3, mode_item)

            duration_ms = p.get('actual_duration_ms', 0)
            minutes = duration_ms // 60000
            seconds = (duration_ms % 60000) // 1000
            self.table.setItem(row, 4, QTableWidgetItem(f"{minutes:02d}:{seconds:02d}"))

            pause_count = p.get('total_pause_count', 0)
            pause_item = QTableWidgetItem(str(pause_count))
            pause_item.setData(Qt.ItemDataRole.UserRole, pause_count)
            self.table.setItem(row, 5, pause_item)

            overtime_ms = p.get('overtime_ms', 0)
            if overtime_ms > 0:
                o_minutes = overtime_ms // 60000
                o_seconds = (overtime_ms % 60000) // 1000
                overtime_item = QTableWidgetItem(f"+{o_minutes:02d}:{o_seconds:02d}")
                overtime_item.setData(Qt.ItemDataRole.UserRole, overtime_ms)
            else:
                overtime_item = QTableWidgetItem("-")
                overtime_item.setData(Qt.ItemDataRole.UserRole, 0)
            self.table.setItem(row, 6, overtime_item)

            # Паузы между этапами
            inter_ms = p.get('inter_stage_pause_ms', 0)
            if inter_ms > 0:
                i_min = inter_ms // 60000
                i_sec = (inter_ms % 60000) // 1000
                self.table.setItem(row, 7, QTableWidgetItem(f"{i_min:02d}:{i_sec:02d}"))
            else:
                self.table.setItem(row, 7, QTableWidgetItem("-"))

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def show_presentation_details(self):
        """Показать детали выступления из таблицы"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите выступление из таблицы")
            return

        pres_id = int(self.table.item(current_row, 0).text())
        presentation = self.db_manager.get_presentation_stats(pres_id)

        if presentation:
            details = self._format_presentation_details(presentation, pres_id)
            QMessageBox.information(self, f"Детали выступления #{pres_id}", details)

    def _format_presentation_details(self, presentation, pres_id):
        """Форматирование деталей выступления простым текстом"""
        start_time = presentation.get('start_time', 'N/A')
        if start_time != 'N/A':
            start_time = start_time.replace('T', ' ')[:19]

        timer_mode = presentation.get('timer_mode', 'N/A')
        mode_names = {
            'countdown': 'Обратный отсчёт',
            'countup': 'Прямой отсчёт',
            'both': 'Двойной режим'
        }
        mode_display = mode_names.get(timer_mode, timer_mode)

        details = f"""📊 ВЫСТУПЛЕНИЕ #{pres_id}

📅 Дата и время: {start_time}
🎯 Режим таймера: {mode_display}

⏱️ ВРЕМЯ:
   • Запланировано: {self._ms_to_str(presentation.get('planned_duration_ms', 0))}
   • Фактически: {self._ms_to_str(presentation.get('actual_duration_ms', 0))}
   • Превышение: {self._ms_to_str(presentation.get('overtime_ms', 0))}

⏸️ ПАУЗЫ:
   • Количество пауз: {presentation.get('total_pause_count', 0)}
   • Общее время: {self._ms_to_str(presentation.get('total_pause_duration_ms', 0))}"""

        # Паузы между этапами
        inter_stage_ms = presentation.get('inter_stage_pause_ms', 0)
        if inter_stage_ms > 0:
            details += f"\n   • Между этапами: {self._ms_to_str(inter_stage_ms)}"


        # Этапы выступления
        if presentation.get('stages'):
            details += f"""

📋 ЭТАПЫ ВЫСТУПЛЕНИЯ:"""
            for i, stage in enumerate(presentation['stages'], 1):
                stage_name = stage.get('stage_name', f'Этап {i}')
                planned = self._ms_to_str(stage.get('planned_duration_ms', 0))
                actual = self._ms_to_str(stage.get('actual_duration_ms', 0))
                overtime = stage.get('overtime_ms', 0)
                pause_count = stage.get('pause_count', 0)
                pause_dur = self._ms_to_str(stage.get('pause_duration_ms', 0))

                details += f"\n   {i}. {stage_name}: {actual} (план: {planned})"
                if overtime > 0:
                    details += f" ⚠️ +{self._ms_to_str(overtime)}"
                if pause_count > 0:
                    details += f"\n      ⏸️ Пауз в этапе: {pause_count} ({pause_dur})"

        return details

    def _ms_to_str(self, ms):
        """Конвертация миллисекунд в строку ММ:СС"""
        if not ms:
            return "00:00"
        seconds = abs(ms) // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        sign = "-" if ms < 0 else ""
        return f"{sign}{minutes:02d}:{seconds:02d}"

    def on_filter_changed(self):
        """Обработка изменения фильтра"""
        self.load_data()

    def export_to_json(self):
        """Экспорт данных в JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить JSON",
            f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json)"
        )

        if file_path:
            path = self.db_manager.export_to_json(file_path)
            QMessageBox.information(self, "Экспорт", f"Данные экспортированы в:\n{path}")

    def export_to_csv(self):
        """Экспорт таблицы в CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить CSV",
            f"presentations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV files (*.csv)"
        )

        if file_path:
            import csv
            presentations = self.db_manager.get_all_presentations(limit=500)
            filtered = self.apply_filter(presentations)

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                if filtered:
                    writer = csv.DictWriter(f, fieldnames=filtered[0].keys())
                    writer.writeheader()
                    writer.writerows(filtered)

            QMessageBox.information(self, "Экспорт", f"CSV файл сохранён:\n{file_path}")

    def export_to_pdf(self):
        """Экспорт данных в PDF (с графиками и цветами)"""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from datetime import datetime
        import os
        import io
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить PDF",
            f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF files (*.pdf)"
        )

        if not file_path:
            return

        try:
            # Регистрируем шрифты
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
            ]

            chosen_font = None

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('CustomFont', font_path))
                        chosen_font = 'CustomFont'
                        break
                    except:
                        continue

            if not chosen_font:
                chosen_font = 'Helvetica'

            # Получаем данные
            presentations = self.db_manager.get_all_presentations(limit=500)
            filtered = self.apply_filter(presentations)

            # Ширина страницы
            page_width = A4[0] - 30 * mm

            # Цвета
            color_dark = colors.HexColor('#2C3E50')
            color_gray = colors.HexColor('#ECF0F1')
            color_gray_border = colors.HexColor('#BDC3C7')

            # Создаём документ
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=15 * mm,
                leftMargin=15 * mm,
                topMargin=15 * mm,
                bottomMargin=15 * mm
            )

            # Отступ для текста
            left_indent = 0

            # Стили
            style_large = ParagraphStyle(
                'Large',
                fontName=chosen_font,
                fontSize=16,
                leading=20,
                textColor=colors.black,
                spaceAfter=2,
                alignment=TA_CENTER
            )

            style_medium = ParagraphStyle(
                'Medium',
                fontName=chosen_font,
                fontSize=14,
                leading=18,
                textColor=colors.black,
                spaceAfter=1,
                spaceBefore=8,
                alignment=TA_LEFT,
                leftIndent=left_indent
            )

            style_small = ParagraphStyle(
                'Small',
                fontName=chosen_font,
                fontSize=12,
                leading=16,
                textColor=colors.black,
                spaceAfter=0,
                spaceBefore=0,
                leftIndent=left_indent + 10,
                firstLineIndent=0
            )

            style_chart_title = ParagraphStyle(
                'ChartTitle',
                fontName=chosen_font,
                fontSize=14,
                leading=18,
                textColor=colors.black,
                spaceAfter=1,
                spaceBefore=8,
                alignment=TA_CENTER,
                leftIndent=0
            )

            elements = []

            # === СТРАНИЦА 1 ===

            elements.append(Paragraph("Статистика выступлений", style_large))
            elements.append(Paragraph(
                f"(сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')})",
                ParagraphStyle('Subtitle',
                               fontName=chosen_font,
                               fontSize=9,
                               leading=13,
                               textColor=colors.black,
                               alignment=TA_CENTER,
                               leftIndent=0
                               )
            ))

            total = len(filtered)
            if total > 0:
                elements.append(Paragraph("Общая статистика", style_medium))

                total_duration_ms = sum(p.get('actual_duration_ms', 0) for p in filtered)
                total_duration_min = total_duration_ms / 1000 / 60
                avg_duration = total_duration_min / total if total > 0 else 0
                total_pauses = sum(p.get('total_pause_count', 0) for p in filtered)
                overtime_count = sum(1 for p in filtered if p.get('overtime_ms', 0) > 0)
                overtime_rate = (overtime_count / total * 100) if total > 0 else 0

                stats_lines = [
                    f"— Выступлений: {total}",
                    f"— Средняя длительность: {avg_duration:.1f} мин",
                    f"— Всего пауз: {total_pauses}",
                    f"— С превышением: {overtime_rate:.0f}%"
                ]
                for line in stats_lines:
                    elements.append(Paragraph(line, style_small))

                elements.append(Paragraph("Список выступлений", style_medium))
                elements.append(Spacer(1, 2 * mm))

                # Таблица — сдвинута правее на 10px
                table_data = [[
                    "Дата", "Время", "Режим", "Длительность", "Паузы", "Превышение"
                ]]

                for p in filtered[:50]:
                    try:
                        dt = datetime.fromisoformat(p.get('start_time', ''))
                        date_str = dt.strftime('%d.%m.%Y')
                        time_str = dt.strftime('%H:%M')
                    except:
                        date_str = '-'
                        time_str = '-'

                    mode = p.get('timer_mode', '')
                    mode_names = {
                        'countdown': 'Обратный',
                        'countup': 'Прямой',
                        'both': 'Двойной'
                    }
                    mode_display = mode_names.get(mode, mode)

                    duration_ms = p.get('actual_duration_ms', 0)
                    minutes = duration_ms // 60000
                    seconds = (duration_ms % 60000) // 1000
                    duration_str = f"{minutes}:{seconds:02d}"

                    pause_count = p.get('total_pause_count', 0)

                    overtime_ms = p.get('overtime_ms', 0)
                    if overtime_ms > 0:
                        o_min = overtime_ms // 60000
                        o_sec = (overtime_ms % 60000) // 1000
                        overtime_str = f"+{o_min}:{o_sec:02d}"
                    else:
                        overtime_str = "-"

                    table_data.append([
                        date_str, time_str, mode_display,
                        duration_str, str(pause_count), overtime_str
                    ])

                col_width = page_width / 6
                col_widths = [col_width] * 6

                pres_table = Table(table_data, colWidths=col_widths)

                table_style = TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), chosen_font),
                    ('FONTSIZE', (0, 0), (-1, -1), 12),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), color_dark),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, color_gray]),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 0.5, color_gray_border),
                    ('BOX', (0, 0), (-1, -1), 1, color_dark),
                ])
                pres_table.setStyle(table_style)
                elements.append(pres_table)

                # === РАЗРЫВ СТРАНИЦЫ ===
                elements.append(PageBreak())

                # === СТРАНИЦА 2: ГРАФИКИ ===

                elements.append(Spacer(1, 10 * mm))

                elements.append(Paragraph("Распределение длительности выступлений", style_chart_title))
                elements.append(Spacer(1, 3 * mm))

                # Гистограмма
                durations = [p.get('actual_duration_ms', 0) / 1000 / 60 for p in filtered]

                if durations:
                    fig1, ax1 = plt.subplots(figsize=(10, 4.5))
                    bins = min(15, len(set(durations))) if len(set(durations)) > 1 else 1

                    ax1.hist(
                        durations, bins=bins,
                        color='#2C3E50', edgecolor='white',
                        alpha=0.9, orientation='vertical'
                    )

                    ax1.set_xlabel('Длительность (минуты)')
                    ax1.set_ylabel('Количество выступлений')
                    ax1.set_facecolor('white')
                    fig1.patch.set_facecolor('white')
                    ax1.spines['top'].set_visible(False)
                    ax1.spines['right'].set_visible(False)
                    ax1.grid(True, alpha=0.3, axis='y')

                    img_buffer = io.BytesIO()
                    fig1.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
                    img_buffer.seek(0)
                    plt.close(fig1)

                    img = Image(img_buffer, width=page_width, height=85 * mm)
                    elements.append(img)

                elements.append(Spacer(1, 8 * mm))

                elements.append(Paragraph("Используемые режимы таймера", style_chart_title))
                elements.append(Spacer(1, 3 * mm))

                # Круговая диаграмма
                modes = {}
                for p in filtered:
                    mode = p.get('timer_mode', 'unknown')
                    modes[mode] = modes.get(mode, 0) + 1

                if modes:
                    fig2, ax2 = plt.subplots(figsize=(8, 8))
                    mode_names = {
                        'countdown': 'Обратный отсчёт',
                        'countup': 'Прямой отсчёт',
                        'both': 'Двойной режим'
                    }
                    labels = [mode_names.get(m, m) for m in modes.keys()]
                    values = list(modes.values())

                    color_map = {
                        'countup': '#2C3E50',
                        'countdown': '#0000FF',
                        'both': '#85C1E9'
                    }
                    colors_pie = [color_map.get(m, '#95A5A6') for m in modes.keys()]

                    wedges, texts, autotexts = ax2.pie(
                        values, labels=labels, autopct='%1.1f%%',
                        colors=colors_pie, startangle=90,
                        wedgeprops=dict(width=0.35, edgecolor='white'),
                        pctdistance=0.82  # Ещё ближе к внешнему краю
                    )

                    for text in texts:
                        text.set_fontsize(14)
                        text.set_fontweight('bold')
                    for autotext in autotexts:
                        autotext.set_fontsize(13)
                        autotext.set_fontweight('bold')
                        autotext.set_color('white')

                    ax2.set_aspect('equal')
                    fig2.patch.set_facecolor('white')

                    img_buffer2 = io.BytesIO()
                    fig2.savefig(img_buffer2, format='png', dpi=150, bbox_inches='tight', facecolor='white')
                    img_buffer2.seek(0)
                    plt.close(fig2)

                    img2 = Image(img_buffer2, width=150 * mm, height=110 * mm)
                    img_table = Table([[img2]], colWidths=[page_width])
                    img_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ]))
                    elements.append(img_table)

            else:
                elements.append(Paragraph("Нет данных для отображения",
                                          ParagraphStyle('Empty',
                                                         fontName=chosen_font,
                                                         fontSize=12,
                                                         textColor=colors.black,
                                                         leftIndent=0
                                                         )
                                          ))

            # Генерируем PDF
            doc.build(elements)
            QMessageBox.information(self, "Экспорт", f"PDF файл сохранен:\n{file_path}")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при создании PDF:\n{str(e)}")
            print(f"Ошибка экспорта в PDF: {e}")
            import traceback
            traceback.print_exc()