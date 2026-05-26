import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """Точка входа в приложение"""
    app = QApplication(sys.argv)

    app.setApplicationName("Таймер выступления")
    app.setApplicationDisplayName("Таймер выступления")

    window = MainWindow()
    window.show()

    app.aboutToQuit.connect(window.save_settings)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()