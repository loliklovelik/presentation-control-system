import time
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from enum import Enum
from datetime import datetime
from utils import ms_to_time_str


class TimerMode(Enum):
    """Режимы работы таймера"""
    COUNTDOWN = "countdown"  # Обратный отсчет (от установленного до 0)
    COUNTUP = "countup"  # Прямой отсчет (от 0 до установленного)
    BOTH = "both"  # Двойной таймер (и прямой, и обратный)


class TimerEngine(QThread):
    """Движок таймера, работающий в отдельном потоке"""

    time_updated = pyqtSignal(str, str)  # Сигнал с обновленным временем (основное, дополнительное)
    phase_changed = pyqtSignal(str)  # Сигнал о смене фазы
    time_is_up = pyqtSignal()  # Сигнал об окончании времени
    timer_state_changed = pyqtSignal(str)  # Сигнал о состоянии таймера
    pause_stats_updated = pyqtSignal(int, int)  # Сигнал со статистикой пауз
    overtime_updated = pyqtSignal(int)  # Сигнал с превышением времени в секундах
    presentation_finished = pyqtSignal(dict)  # Сигнал с полной статистикой при завершении

    # Константы фаз
    PHASE_NORMAL = "normal"
    PHASE_WARNING = "warning"
    PHASE_OVERTIME = "overtime"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration_ms = 300000  # 5 минут по умолчанию
        self.remaining_ms = 300000
        self.elapsed_ms = 0  # Прошедшее время для прямого отсчета
        self.overtime_ms = 0  # Время превышения
        self.is_running = False
        self.is_paused = False
        self.warning_threshold = 60000  # 1 минута для предупреждения
        self.current_phase = self.PHASE_NORMAL

        # Используем обычные переменные для потокобезопасности
        self.start_time = 0  # Время запуска в миллисекундах
        self.pause_start_time = 0  # Время начала паузы
        self.pause_accumulated = 0  # Накопленное время пауз
        self.overtime_start_time = 0  # Время начала превышения

        # Время старта выступления (ISO формат) ← ДОБАВИТЬ
        self.presentation_start_time = None  # ← ДОБАВИТЬ

        # Новые поля для режимов
        self.mode = TimerMode.COUNTDOWN

        # Статистика пауз
        self.pause_count = 0
        self.total_pause_duration_ms = 0

        # Статистика выступления
        self.total_elapsed_ms = 0  # Общее время выступления (включая превышение)

        # Мьютекс для потокобезопасности
        self.mutex = QMutex()

    def run(self):
        """Основной цикл таймера"""
        while not self.isInterruptionRequested():
            # Используем локальные копии для работы в цикле
            local_is_running = False
            local_is_paused = False
            local_start_time = 0
            local_pause_accumulated = 0
            local_duration_ms = 0
            local_mode = None
            local_warning_threshold = 0

            with QMutexLocker(self.mutex):
                local_is_running = self.is_running
                local_is_paused = self.is_paused
                local_start_time = self.start_time
                local_pause_accumulated = self.pause_accumulated
                local_duration_ms = self.duration_ms
                local_mode = self.mode
                local_warning_threshold = self.warning_threshold

            if local_is_running and not local_is_paused:
                current_time = int(time.time() * 1000)

                # Вычисляем прошедшее время
                elapsed = current_time - local_start_time - local_pause_accumulated

                with QMutexLocker(self.mutex):
                    self.total_elapsed_ms = elapsed

                    # Прямой таймер всегда считает полное время (не ограничиваем)
                    self.elapsed_ms = elapsed

                    # Обновляем remaining_ms для обратного отсчета
                    self.remaining_ms = max(0, self.duration_ms - elapsed)

                    # Вычисляем превышение времени
                    if elapsed > self.duration_ms:
                        self.overtime_ms = elapsed - self.duration_ms
                        # Отправляем сигнал с превышением примерно раз в секунду
                        if int(self.overtime_ms) % 1000 < 50:
                            self.overtime_updated.emit(self.overtime_ms // 1000)
                    else:
                        self.overtime_ms = 0

                    # Определяем текущую фазу
                    new_phase = self.current_phase

                    if self.mode == TimerMode.COUNTUP:
                        time_left = self.duration_ms - elapsed
                        if time_left <= 0:
                            new_phase = self.PHASE_OVERTIME
                            if not self.overtime_start_time:
                                self.overtime_start_time = current_time
                                self.time_is_up.emit()
                        elif time_left <= self.warning_threshold:
                            new_phase = self.PHASE_WARNING
                        else:
                            new_phase = self.PHASE_NORMAL

                    elif self.mode in [TimerMode.COUNTDOWN, TimerMode.BOTH]:
                        if self.remaining_ms == 0:
                            new_phase = self.PHASE_OVERTIME
                            if not self.overtime_start_time:
                                self.overtime_start_time = current_time
                                self.time_is_up.emit()
                        elif self.remaining_ms <= self.warning_threshold:
                            new_phase = self.PHASE_WARNING
                        else:
                            new_phase = self.PHASE_NORMAL

                    # Если фаза изменилась
                    if new_phase != self.current_phase:
                        self.current_phase = new_phase
                        self.phase_changed.emit(new_phase)

                    # Отправляем обновленное время
                    main_time_str = self.get_main_time_str()
                    secondary_time_str = self.get_secondary_time_str()
                    self.time_updated.emit(main_time_str, secondary_time_str)

            time.sleep(0.05)  # 50ms обновление

    def get_main_time_str(self) -> str:
        """Получить основное время для отображения"""
        if self.mode == TimerMode.COUNTUP:
            if self.current_phase == self.PHASE_OVERTIME:
                return f"+{ms_to_time_str(self.overtime_ms)}"
            else:
                return ms_to_time_str(self.elapsed_ms)
        elif self.current_phase == self.PHASE_OVERTIME and self.mode in [TimerMode.COUNTDOWN, TimerMode.BOTH]:
            return f"-{ms_to_time_str(self.overtime_ms)}"
        else:
            return ms_to_time_str(self.remaining_ms)

    def get_secondary_time_str(self) -> str:
        """Получить дополнительное время для отображения (для режима BOTH)"""
        if self.mode == TimerMode.BOTH:
            # Всегда показываем полное прошедшее время
            return ms_to_time_str(self.elapsed_ms)
        return ""

    # Удаляем метод ms_to_time_str - он больше не нужен

    def start_timer(self, duration_ms=None):
        """Запуск таймера"""
        if not self.isRunning():
            self.start()

        with QMutexLocker(self.mutex):
            if duration_ms is not None:
                self.duration_ms = duration_ms

            self.remaining_ms = self.duration_ms
            self.elapsed_ms = 0
            self.overtime_ms = 0
            self.is_running = True
            self.is_paused = False
            self.current_phase = self.PHASE_NORMAL

            # Инициализируем временные метки
            self.start_time = int(time.time() * 1000)
            self.pause_start_time = 0
            self.pause_accumulated = 0
            self.overtime_start_time = 0
            self.total_elapsed_ms = 0

            # Сохраняем время старта выступления ← ДОБАВИТЬ
            self.presentation_start_time = datetime.now().isoformat()  # ← ДОБАВИТЬ

            # Сбрасываем статистику пауз при новом запуске
            self.pause_count = 0
            self.total_pause_duration_ms = 0
            self.pause_stats_updated.emit(0, 0)

            self.timer_state_changed.emit("running")

    def pause_timer(self):
        """Пауза таймера"""
        with QMutexLocker(self.mutex):
            if self.is_running and not self.is_paused:
                self.is_paused = True
                self.pause_start_time = int(time.time() * 1000)
                self.timer_state_changed.emit("paused")

    def resume_timer(self):
        """Продолжение таймера"""
        with QMutexLocker(self.mutex):
            if self.is_running and self.is_paused:
                self.is_paused = False

                # Вычисляем длительность паузы
                current_time = int(time.time() * 1000)
                pause_duration = current_time - self.pause_start_time

                # Добавляем к накопленному времени пауз
                self.pause_accumulated += pause_duration

                # Обновляем статистику
                self.pause_count += 1
                self.total_pause_duration_ms += pause_duration

                # Отправляем обновленную статистику
                total_pause_seconds = self.total_pause_duration_ms // 1000
                self.pause_stats_updated.emit(self.pause_count, total_pause_seconds)

                self.timer_state_changed.emit("running")


    def finish_presentation(self):
        """Завершить выступление и получить статистику"""
        with QMutexLocker(self.mutex):
            if self.is_running:
                current_time = int(time.time() * 1000)

                if self.is_paused:
                    # Нужно добавить длительность текущей паузы к паузам, если мы завершаем прямо на паузе
                    current_pause_duration = current_time - self.pause_start_time
                    self.total_pause_duration_ms += current_pause_duration
                    final_elapsed = self.pause_start_time - self.start_time - self.pause_accumulated
                else:
                    final_elapsed = current_time - self.start_time - self.pause_accumulated

                self.total_elapsed_ms = final_elapsed

                # Останавливаем таймер
                self.is_running = False
                self.is_paused = False

                # Формируем статистику
                stats = {
                    "planned_duration_ms": self.duration_ms,
                    "planned_duration_str": ms_to_time_str(self.duration_ms),
                    "actual_duration_ms": final_elapsed,
                    "actual_duration_str": ms_to_time_str(final_elapsed),
                    "overtime_ms": max(0, final_elapsed - self.duration_ms),
                    "overtime_str": ms_to_time_str(max(0, final_elapsed - self.duration_ms)),
                    "pause_count": self.pause_count,
                    "total_pause_ms": self.total_pause_duration_ms,
                    "total_pause_str": ms_to_time_str(self.total_pause_duration_ms),
                    "total_with_pauses_ms": final_elapsed + self.total_pause_duration_ms,
                    "total_with_pauses_str": ms_to_time_str(final_elapsed + self.total_pause_duration_ms),
                    "mode": self.mode.value,
                    "start_timestamp": self.presentation_start_time,  # ← ИСПРАВИТЬ
                    "end_timestamp": datetime.now().isoformat(),  # ← ИСПРАВИТЬ
                }

                self.timer_state_changed.emit("stopped")

                # Отправляем сигнал со статистикой
                self.presentation_finished.emit(stats)

                return stats

        return None

    def reset_timer(self):
        """Сброс таймера"""
        with QMutexLocker(self.mutex):
            self.is_running = False
            self.is_paused = False
            self.current_phase = self.PHASE_NORMAL
            self.remaining_ms = self.duration_ms
            self.elapsed_ms = 0
            self.overtime_ms = 0

            # Сбрасываем временные метки
            self.start_time = 0
            self.pause_start_time = 0
            self.pause_accumulated = 0
            self.overtime_start_time = 0
            self.total_elapsed_ms = 0

            # Сбрасываем статистику пауз
            self.pause_count = 0
            self.total_pause_duration_ms = 0
            self.pause_stats_updated.emit(0, 0)

            main_time_str = self.get_main_time_str()
            secondary_time_str = self.get_secondary_time_str()
            self.time_updated.emit(main_time_str, secondary_time_str)
            self.phase_changed.emit(self.PHASE_NORMAL)
            self.timer_state_changed.emit("stopped")

    def set_time(self, ms):
        """Установка нового времени"""
        with QMutexLocker(self.mutex):
            self.duration_ms = ms
            if not self.is_running:
                self.remaining_ms = ms
                self.elapsed_ms = 0
                self.overtime_ms = 0
                main_time_str = self.get_main_time_str()
                secondary_time_str = self.get_secondary_time_str()
                self.time_updated.emit(main_time_str, secondary_time_str)

    def set_mode(self, mode: TimerMode):
        """Установка режима таймера"""
        with QMutexLocker(self.mutex):
            self.mode = mode
            if not self.is_running:
                main_time_str = self.get_main_time_str()
                secondary_time_str = self.get_secondary_time_str()
                self.time_updated.emit(main_time_str, secondary_time_str)

    def get_phase_color(self):
        """Возвращает цвет для текущей фазы"""
        if self.current_phase == self.PHASE_NORMAL:
            return "#2E7D32", "#FFFFFF"
        elif self.current_phase == self.PHASE_WARNING:
            return "#F9A825", "#000000"
        else:
            return "#C62828", "#FFFFFF"

    def cleanup(self):
        """Очистка ресурсов"""
        self.is_running = False
        self.requestInterruption()
        self.wait(1000)