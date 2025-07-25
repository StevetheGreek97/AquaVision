from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox,
    QLineEdit, QHBoxLayout, QListWidget, QProgressBar
)
from PyQt6.QtCore import Qt
from services.recent_projects import load_recent_projects
import shutil
import os
import platform
import pathlib
import re

class DraggableImageList(QListWidget):
    def __init__(self, accepted_extensions=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.accepted_extensions = accepted_extensions or [".png", ".jpg", ".jpeg", ".bmp", ".tif"]
        self.file_list = []

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = pathlib.Path(url.toLocalFile()).resolve()
            if path.is_file() and path.suffix.lower() in self.accepted_extensions:
                if str(path) not in self.file_list:
                    self.file_list.append(str(path))
                    self.addItem(path.name)

class ProjectStartupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to SegmentME")
        self.setFixedSize(500, 420)

        self.selected_project_path = None
        self.is_new_project = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Start a new or load an existing project:"))

        new_btn = QPushButton("🆕 Create New Project")
        new_btn.clicked.connect(self.create_project)
        layout.addWidget(new_btn)

        layout.addWidget(QLabel("Recent Projects:"))
        for path in load_recent_projects():
            if os.path.exists(path):
                project_name = os.path.basename(os.path.dirname(os.path.dirname(path)))
                recent_btn = QPushButton(f"🕘 {project_name}")
                recent_btn.setToolTip(path)
                recent_btn.clicked.connect(lambda _, p=path: self.load_recent(p))
                layout.addWidget(recent_btn)

    def default_desktop_path(self):
        system_platform = platform.system()
        if system_platform == "Windows":
            return os.path.join(os.environ.get("USERPROFILE", str(pathlib.Path.home())), "Desktop")
        elif system_platform == "Darwin":
            return str(pathlib.Path.home() / "Desktop")
        else:
            return str(pathlib.Path.home() / "Desktop")

    def create_project(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Project")
        dialog.setMinimumWidth(480)

        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Save Project To:"))
        path_layout = QHBoxLayout()
        path_input = QLineEdit(self.default_desktop_path())
        browse_btn = QPushButton("📂")
        browse_btn.clicked.connect(lambda: self.select_folder(path_input))
        path_layout.addWidget(path_input)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        layout.addWidget(QLabel("Project Name (alphanumeric only):"))
        name_input = QLineEdit('MyCoolProject')
        layout.addWidget(name_input)

        layout.addWidget(QLabel("Import Images (drag & drop or browse folder):"))
        img_layout = QHBoxLayout()
        import_btn = QPushButton("📁")
        img_list = DraggableImageList()
        img_layout.addWidget(import_btn)
        layout.addLayout(img_layout)
        layout.addWidget(img_list)

        progress_bar = QProgressBar()
        layout.addWidget(progress_bar)

        def import_images():
            files, _ = QFileDialog.getOpenFileNames(
                dialog,
                "Select Images",
                self.default_desktop_path(),
                "Images (*.png *.jpg *.jpeg *.bmp *.tif)"
            )
            for file_path in files:
                path = pathlib.Path(file_path).resolve()
                if path.is_file() and path.suffix.lower() in img_list.accepted_extensions:
                    if str(path) not in img_list.file_list:
                        img_list.file_list.append(str(path))
                        img_list.addItem(path.name)

        import_btn.clicked.connect(import_images)

        create_btn = QPushButton("Create Project")

        def finalize():
            base_dir = pathlib.Path(path_input.text()).expanduser().resolve()
            name = name_input.text().strip()

            if not name:
                QMessageBox.warning(dialog, "Missing Name", "Please enter a project name.")
                return

            if not re.match(r'^[a-zA-Z0-9_-]+$', name):
                QMessageBox.warning(dialog, "Invalid Name", "Project name must only contain letters, numbers, underscores or hyphens.")
                return

            project_path = base_dir / name
            if project_path.exists():
                QMessageBox.warning(dialog, "Exists", "This project folder already exists.")
                return

            try:
                (project_path / "images").mkdir(parents=True)
                (project_path / ".segmentme").mkdir()

                for i, f in enumerate(img_list.file_list):
                    dest = project_path / "images" / pathlib.Path(f).name
                    shutil.copy(f, dest)
                    progress_bar.setValue(int((i + 1) / len(img_list.file_list) * 100))

                with open(project_path / f"{name}.SEproj", "w") as f:
                    f.write("SegmentME Project File")

                self.selected_project_path = str(project_path / ".segmentme" / "masks.db")
                self.is_new_project = True
                dialog.accept()
                self.accept()

            except Exception as e:
                QMessageBox.critical(dialog, "Error", str(e))

        create_btn.clicked.connect(finalize)
        layout.addWidget(create_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def select_folder(self, line_edit):
        start_dir = str(pathlib.Path.home() / "Desktop")
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", start_dir)
        if folder:
            line_edit.setText(folder)

    def load_recent(self, path):
        self.selected_project_path = path
        self.is_new_project = False
        self.accept()
