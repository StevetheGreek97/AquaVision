from PyQt6.QtWidgets import QApplication
import sys
from ui.main_window import MainApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())
