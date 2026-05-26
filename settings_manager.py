from PyQt6.QtCore import QSettings, QByteArray, QRect
from timer_engine import TimerMode


class SettingsManager:
    """Менеджер настроек приложения"""

    def __init__(self):
        self.settings = QSettings("PresentationTimer", "SimpleTimerApp")

    # Сохранение и загрузка звука
    def save_sound_enabled(self, enabled: bool):
        self.settings.setValue("sound/enabled", enabled)

    def load_sound_enabled(self) -> bool:
        return self.settings.value("sound/enabled", True, type=bool)

    # Сохранение и загрузка времени предупреждения
    def save_warning_time(self, seconds: int):
        self.settings.setValue("timing/warning_seconds", seconds)

    def load_warning_time(self) -> int:
        return self.settings.value("timing/warning_seconds", 60, type=int)

    # Сохранение и загрузка прозрачности компактного окна
    def save_compact_opacity(self, percent: int):
        """Сохранение прозрачности компактного окна (0-100%)"""
        self.settings.setValue("compact/opacity", percent)

    def load_compact_opacity(self) -> int:
        """Загрузка прозрачности компактного окна (по умолчанию 100%)"""
        return self.settings.value("compact/opacity", 100, type=int)

    # Сохранение и загрузка геометрии компактного окна
    def save_compact_geometry(self, x: int, y: int, width: int, height: int):
        """Сохранение позиции и размера компактного окна"""
        self.settings.setValue("compact/geometry_x", x)
        self.settings.setValue("compact/geometry_y", y)
        self.settings.setValue("compact/geometry_width", width)
        self.settings.setValue("compact/geometry_height", height)

    def load_compact_geometry(self) -> QRect:
        """Загрузка позиции и размера компактного окна"""
        x = self.settings.value("compact/geometry_x", None, type=int)
        y = self.settings.value("compact/geometry_y", None, type=int)
        width = self.settings.value("compact/geometry_width", None, type=int)
        height = self.settings.value("compact/geometry_height", None, type=int)

        if x is not None and y is not None and width is not None and height is not None:
            return QRect(x, y, width, height)
        return None

    # Сохранение и загрузка цветов
    def save_colors(self, normal_color: str, warning_color: str, overtime_color: str):
        self.settings.setValue("colors/normal", normal_color)
        self.settings.setValue("colors/warning", warning_color)
        self.settings.setValue("colors/overtime", overtime_color)

    def load_colors(self):
        normal = self.settings.value("colors/normal", "#2E7D32")
        warning = self.settings.value("colors/warning", "#F9A825")
        overtime = self.settings.value("colors/overtime", "#C62828")
        return normal, warning, overtime

    # Сохранение и загрузка режима таймера
    def save_timer_mode(self, mode: str):
        self.settings.setValue("timer/mode", mode)

    def load_timer_mode(self) -> str:
        return self.settings.value("timer/mode", TimerMode.COUNTDOWN.value, type=str)

    # Сохранение и загрузка геометрии главного окна
    def save_window_geometry(self, geometry: QByteArray):
        self.settings.setValue("window/geometry", geometry)

    def load_window_geometry(self) -> QByteArray:
        return self.settings.value("window/geometry", None, type=QByteArray)

    def save_window_state(self, state: QByteArray):
        self.settings.setValue("window/state", state)

    def load_window_state(self) -> QByteArray:
        return self.settings.value("window/state", None, type=QByteArray)

    # Сохранение и загрузка геометрии окна настроек
    def save_settings_geometry(self, geometry: QByteArray):
        self.settings.setValue("settings/geometry", geometry)

    def load_settings_geometry(self) -> QByteArray:
        return self.settings.value("settings/geometry", None, type=QByteArray)


    # Сохранение и загрузка геометрии компактного окна (полная геометрия)
    def save_compact_window_geometry(self, x: int, y: int, width: int, height: int):
        """Сохранение позиции и размера компактного окна"""
        self.settings.setValue("compact_window/x", x)
        self.settings.setValue("compact_window/y", y)
        self.settings.setValue("compact_window/width", width)
        self.settings.setValue("compact_window/height", height)

    def load_compact_window_geometry(self):
        """Загрузка позиции и размера компактного окна"""
        x = self.settings.value("compact_window/x", None, type=int)
        y = self.settings.value("compact_window/y", None, type=int)
        width = self.settings.value("compact_window/width", None, type=int)
        height = self.settings.value("compact_window/height", None, type=int)

        if x is not None and y is not None and width is not None and height is not None:
            from PyQt6.QtCore import QRect
            return QRect(x, y, width, height)
        return None

    def save_transparent_mode(self, enabled: bool):
        """Сохранение режима прозрачного фона"""
        self.settings.setValue("display/transparent_mode", enabled)

    def load_transparent_mode(self) -> bool:
        """Загрузка режима прозрачного фона"""
        return self.settings.value("display/transparent_mode", False, type=bool)

    def save_current_script_id(self, script_id):
        """Сохранить ID выбранного сценария"""
        if script_id is None:
            self.settings.remove("script/current_id")
        else:
            self.settings.setValue("script/current_id", script_id)

    def load_current_script_id(self):
        """Загрузить ID выбранного сценария"""
        value = self.settings.value("script/current_id", None)
        return int(value) if value else None
