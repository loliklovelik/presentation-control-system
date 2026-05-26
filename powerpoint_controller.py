import time
import pythoncom
import win32com.client
from PyQt6.QtCore import QThread, pyqtSignal


class PowerPointController(QThread):
    """Контроллер PowerPoint"""

    slide_show_started = pyqtSignal(int)
    slide_show_ended = pyqtSignal()
    slide_changed = pyqtSignal(int, int)
    connection_status = pyqtSignal(bool)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.running = False
        self.slide_show_active = False
        self.current_slide = 0
        self.was_connected = False

    def run(self):
        """Основной цикл мониторинга PowerPoint"""
        self.running = True
        pythoncom.CoInitialize()

        while self.running:
            try:
                try:
                    powerpoint = win32com.client.GetActiveObject("PowerPoint.Application")

                    if not self.was_connected:
                        self.was_connected = True
                        self.connection_status.emit(True)
                        print("✅ Подключено к PowerPoint")

                    if powerpoint.Presentations.Count > 0:
                        try:
                            slide_show = powerpoint.SlideShowWindows(1)
                            pres = powerpoint.ActivePresentation
                            current = slide_show.View.Slide.SlideIndex
                            total = pres.Slides.Count

                            print(f"🎯 Слайд: {current}/{total} | Активен показ: {self.slide_show_active}")

                            if not self.slide_show_active:
                                self.slide_show_active = True
                                self.slide_show_started.emit(total)
                                print(f"🎬 Показ слайдов запущен: {total} слайдов")

                            if current != self.current_slide:
                                self.current_slide = current
                                self.slide_changed.emit(current, total)
                                print(f"📊 Смена слайда: {current}/{total}")
                        except Exception as e:
                            if self.slide_show_active:
                                self.slide_show_active = False
                                self.current_slide = 0
                                self.slide_show_ended.emit()
                                print("🎬 Показ слайдов завершен")
                except Exception as e:
                    if self.was_connected:
                        self.was_connected = False
                        self.connection_status.emit(False)
                        print("❌ PowerPoint отключен")
                    time.sleep(2)
                    continue

                time.sleep(0.3)  # Чаще проверяем

            except Exception as e:
                print(f"Ошибка в цикле PowerPoint: {e}")
                time.sleep(2)

    def stop(self):
        """Остановка мониторинга"""
        self.running = False
        self.wait(3000)
        try:
            pythoncom.CoUninitialize()
        except:
            pass