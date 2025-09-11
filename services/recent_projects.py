from pathlib import Path
from core.config import ProjectConfigManager
from services.file_handlers import loader
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import QTimer


# services/recent_projects.py

import json, os, platform, shutil, datetime
from typing import List

APP_DIR_NAME = "segmentme"
RECENT_FILE_NAME = "recent.json"
BACKUP_SUFFIX = ".bak"

def _app_support_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / APP_DIR_NAME
    elif platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        return Path.home() / ".config" / APP_DIR_NAME

def get_recent_file() -> Path:
    base = _app_support_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / RECENT_FILE_NAME

def _read_json_safely(p: Path):
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # Ensure it’s a list of strings
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, str)]
        return []
    except Exception:
        # backup corrupt file and reset
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            p.rename(p.with_suffix(p.suffix + f".{ts}{BACKUP_SUFFIX}"))
        except Exception:
            pass
        return []

def _write_json_safely(p: Path, items: List[str]):
    p.write_text(json.dumps(items, indent=2), encoding="utf-8")

def _project_root_from_db(db_path: str) -> Path:
    # db_path -> .../<project>/.segmentme/masks.db
    return Path(db_path).resolve().parent.parent

def load_recent_projects() -> List[str]:
    """
    Returns a *clean* list of existing db paths.
    Also rewrites recent.json to drop missing entries.
    """
    f = get_recent_file()
    items = _read_json_safely(f)
    existing = []
    changed = False
    for p in items:
        if os.path.exists(p):
            existing.append(p)
        else:
            changed = True
    if changed:
        _write_json_safely(f, existing)
    return existing

def all_recent_projects_raw() -> List[str]:
    """
    Raw list (may include non-existing). For UI cleanup routines.
    """
    return _read_json_safely(get_recent_file())

def save_recent_project(db_path: str):
    db_path = str(Path(db_path).resolve())
    items = _read_json_safely(get_recent_file())
    if db_path in items:
        items.remove(db_path)
    items.insert(0, db_path)
    # de-duplicate & cap length if you want (e.g., 20)
    seen, dedup = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    _write_json_safely(get_recent_file(), dedup[:50])

def remove_recent_project(db_path: str):
    db_path = str(Path(db_path).resolve())
    items = _read_json_safely(get_recent_file())
    if db_path in items:
        items.remove(db_path)
        _write_json_safely(get_recent_file(), items)

def delete_project_and_remove_recent(db_path: str) -> bool:
    """
    Deletes the project folder (…/<project>) if it exists and removes the entry.
    Returns True if folder was deleted or didn’t exist; False on failure.
    """
    try:
        root = _project_root_from_db(db_path)
        remove_recent_project(db_path)
        if root.exists():
            shutil.rmtree(root)
        return True
    except Exception:
        return False

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
