from ui.main_window import MainApp
from ui.dialogs.project_dialog import ProjectStartupDialog
from services.recent_projects import save_recent_project, initialize_project
from services.logger import get_logger

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

logger = get_logger(__name__)

app = QApplication(sys.argv)

if len(sys.argv) > 1 and sys.argv[1].endswith(".SEproj"):
    seproj_file = Path(sys.argv[1]).resolve()
    project_path = seproj_file.parent
    db_path = project_path / ".segmentme" / "masks.db"

    if db_path.exists():
        save_recent_project(str(db_path))
        window = MainApp(db_path=str(db_path))
        initialize_project(window, str(db_path))
        window.show()
        sys.exit(app.exec())
    else:
        logger.error("Cannot open %s: expected project database at %s", seproj_file, db_path)
        sys.exit(1)
else:
    dialog = ProjectStartupDialog()
    if dialog.exec() == dialog.Accepted:
        save_recent_project(dialog.selected_project_path)
        window = MainApp(db_path=dialog.selected_project_path)
        initialize_project(window, dialog.selected_project_path)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)
