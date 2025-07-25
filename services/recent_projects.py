from pathlib import Path
import json
import platform
import os
from core.config import ProjectConfigManager
from services.file_handlers import loader
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import QTimer


def get_recent_file():
    if platform.system() == "Windows":
        base = Path(os.getenv("APPDATA")) / "segmentme"
    elif platform.system() == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support" / "segmentme"
    else:
        base = Path.home() / ".config" / "segmentme"

    base.mkdir(parents=True, exist_ok=True)
    print(f"Recent projects will be stored in: {base / 'recent.json'}")
    return base / "recent.json"


def load_recent_projects():
    recent_file = get_recent_file()
    if recent_file.exists():
        try:
            return json.loads(recent_file.read_text())
        except Exception:
            pass
    return []


def save_recent_project(path):
    path = str(Path(path))  # Normalize path format
    projects = load_recent_projects()
    if path in projects:
        projects.remove(path)
    projects.insert(0, path)
    projects = projects[:5]  # Keep the 5 most recent
    get_recent_file().write_text(json.dumps(projects, indent=2))


def initialize_project(main_window, db_path):
    """
    Initializes project state and UI in the main window.
    """
    project_root = os.path.dirname(os.path.dirname(db_path))
    config = ProjectConfigManager(project_root)

    images_dir = config.get_images_dir()
    if not os.path.exists(images_dir):
        reply = QMessageBox.question(
            main_window, "Images Folder Not Found",
            f"The folder '{images_dir}' does not exist.\nWould you like to locate it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            folder = QFileDialog.getExistingDirectory(main_window, "Locate Images Folder")
            if folder:
                relative = os.path.relpath(folder, project_root)
                config.set_images_dir(relative)
                images_dir = folder
            else:
                return  # User canceled

    image_paths = loader(images_dir)
    if image_paths:
        main_window.project_root = project_root
        main_window.config = config
        main_window.state_manager.set_image_paths(image_paths)
        main_window.slider.set_image_count(len(image_paths))
        main_window.image_display.display_image(main_window.state_manager.current_image_path)
        QTimer.singleShot(0, main_window.image_display.fit_to_view) 
    else:
        QMessageBox.information(main_window, "No Images", "No images found in the selected folder.")
