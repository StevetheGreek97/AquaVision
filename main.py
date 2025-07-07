from ui.main_window import MainApp
from ui.dialogs.project_dialog import ProjectStartupDialog
from services.recent_projects import save_recent_project
import sys
import os
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

if len(sys.argv) > 1 and sys.argv[1].endswith(".SEproj"):
    seprog_path = sys.argv[1]
    project_path = os.path.dirname(seprog_path)  # Remove .SEprog

    db_path = os.path.join(project_path, ".segmentme", "masks.db")
    if os.path.exists(db_path):
        save_recent_project(db_path)
        window = MainApp(db_path=db_path)
        window.initialize_project(db_path)
        window.show()
        sys.exit(app.exec())
    else:
        print(f"❌ Cannot find database at {db_path}")
        sys.exit(1)
else:
    dialog = ProjectStartupDialog()
    if dialog.exec() == dialog.Accepted:
        save_recent_project(dialog.selected_project_path)
        window = MainApp(db_path=dialog.selected_project_path)
        window.initialize_project(dialog.selected_project_path)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)
