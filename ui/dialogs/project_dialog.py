from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox, QInputDialog
from services.recent_projects import load_recent_projects
import shutil
import os

class ProjectStartupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to SegmentME")
        self.setFixedSize(320, 300)

        self.selected_project_path = None
        self.is_new_project = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Start a new or load an existing project:"))

        new_btn = QPushButton("🆕 Create New Project")
        new_btn.clicked.connect(self.create_project)
        layout.addWidget(new_btn)

        load_btn = QPushButton("📂 Load Existing Project")
        load_btn.clicked.connect(self.load_project)
        layout.addWidget(load_btn)

        # Recent section
        layout.addWidget(QLabel("Recent Projects:"))
        for path in load_recent_projects():
            if os.path.exists(path):
                project_name = os.path.basename(os.path.dirname(os.path.dirname(path))) # 👈 Shows folder as project name
                recent_btn = QPushButton(f"🕘 {project_name}")
                recent_btn.setToolTip(path)
                recent_btn.clicked.connect(lambda _, p=path: self.load_recent(p))
                layout.addWidget(recent_btn)


    def create_project(self):
        # Step 1: Let user pick a base folder (e.g., ~/Documents/AquaProjects)
        base_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Project")
        if not base_dir:
            return

        # Step 2: Ask user to name the project
        name, ok = QInputDialog.getText(self, "Project Name", "Enter a name for your new project:")
        if not ok or not name.strip():
            QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")
            return

        project_name = name.strip()
        project_path = os.path.join(base_dir, project_name)

        # Step 3: Create folder and masks.db
        try:
            os.makedirs(project_path, exist_ok=False)
            os.makedirs(os.path.join(project_path, "images"), exist_ok=False)  # ✅ Create images folder
            os.makedirs(os.path.join(project_path, ".segmentme"), exist_ok=False)

        except FileExistsError:
            QMessageBox.warning(self, "Already Exists", f"A project named '{project_name}' already exists in this location.")
            return

        # Step 4: Store project path and exit dialog
        self.selected_project_path = os.path.join(project_path, ".segmentme/masks.db")
        self.is_new_project = True
        self.accept()
         # Step 5: Immediately prompt to import images
        image_files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Images for This Project",
            filter="Images (*.png *.jpg *.jpeg *.bmp *.tif)"
        )
        if image_files:
            images_dir = os.path.join(project_path, "images")
            for f in image_files:
                fname = os.path.basename(f)
                dest = os.path.join(images_dir, fname)
                if not os.path.exists(dest):
                    shutil.copy(f, dest)




    def load_project(self):
        db_path, _ = QFileDialog.getOpenFileName(self, "Select Existing Project DB", filter="SQLite DB (*.db)")
        if db_path and os.path.exists(db_path):
            self.selected_project_path = db_path
            self.is_new_project = False
            self.accept()

    def load_recent(self, path):
        self.selected_project_path = path
        self.is_new_project = False
        self.accept()
