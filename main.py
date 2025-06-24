from ui.main_window import MainApp
from ui.dialogs.project_dialog import ProjectStartupDialog
from services.recent_projects import save_recent_project
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

dialog = ProjectStartupDialog()
if dialog.exec() == dialog.Accepted:
    save_recent_project(dialog.selected_project_path)

    # 1. Create the app
    window = MainApp(db_path=dialog.selected_project_path)

    # 2. Immediately initialize project AFTER window creation
    window.initialize_project(dialog.selected_project_path)

    window.show()
    sys.exit(app.exec())
else:
    sys.exit(0)
