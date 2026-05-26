import pygame
from pathlib import Path


class SoundManager:
    """Менеджер звуковых сигналов"""

    def __init__(self):
        pygame.mixer.init()
        self.sounds_loaded = False
        self.sounds = {}
        self.enabled = True

    def load_sounds(self):
        """Загрузка звуковых файлов"""
        try:
            base_path = Path(__file__).parent
            assets_path = base_path / "assets"

            assets_path.mkdir(exist_ok=True)

            warning_path = assets_path / "beep_warning.wav"
            final_path = assets_path / "beep_final.wav"

            if warning_path.exists():
                self.sounds['warning'] = pygame.mixer.Sound(str(warning_path))
            else:
                print(f"Предупреждение: файл {warning_path} не найден")

            if final_path.exists():
                self.sounds['final'] = pygame.mixer.Sound(str(final_path))
            else:
                print(f"Предупреждение: файл {final_path} не найден")

            self.sounds_loaded = True
            return True

        except Exception as e:
            print(f"Ошибка загрузки звуков: {e}")
            self.sounds_loaded = False
            return False

    def play_warning(self):
        """Воспроизвести предупреждающий звук"""
        if self.enabled and self.sounds_loaded and 'warning' in self.sounds:
            try:
                self.sounds['warning'].play()
            except:
                pass

    def play_final(self):
        """Воспроизвести финальный звук"""
        if self.enabled and self.sounds_loaded and 'final' in self.sounds:
            try:
                self.sounds['final'].play()
            except:
                pass

    def set_enabled(self, enabled):
        """Включить/выключить звук"""
        self.enabled = enabled

    def cleanup(self):
        """Очистка ресурсов"""
        pygame.mixer.quit()