from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QFileDialog, QMessageBox, QLineEdit, QProgressBar,
    QAbstractItemView, QStyle
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from services.recent_projects import load_recent_projects
import shutil, os, re, pathlib, platform

# ---------- Helpers: theme-aware stylesheet ----------

def _rgba(c: QColor, a: int = 255) -> str:
    return f"rgba({c.red()},{c.green()},{c.blue()},{a})"

def _is_dark(widget) -> bool:
    bg = widget.palette().color(QPalette.ColorRole.Window)
    return bg.lightness() < 128

def _build_stylesheet(widget) -> str:
    pal = widget.palette()
    dark = _is_dark(widget)

    bg    = pal.color(QPalette.ColorRole.Window)
    fg    = pal.color(QPalette.ColorRole.WindowText)
    base  = pal.color(QPalette.ColorRole.Base)

    # Carefully chosen neutrals for both modes
    card      = QColor(28, 28, 30) if dark else QColor(255, 255, 255)
    border    = QColor(60, 60, 65) if dark else QColor(225, 225, 230)
    hairline  = QColor(48, 48, 52) if dark else QColor(240, 240, 245)
    hover     = QColor(40, 40, 44) if dark else QColor(246, 246, 248)
    muted     = QColor(170, 170, 175) if dark else QColor(105, 105, 110)
    # Accessible accent with good contrast in both modes
    accent    = QColor(99, 163, 255) if dark else QColor(33, 108, 214)
    accent_fg = QColor(0, 0, 0) if dark else QColor(255, 255, 255)

    return f"""
    /* Container */
    QDialog {{
        background: {bg.name()};
        color: {fg.name()};
    }}

    /* Titles */
    QLabel#title {{
        font-size: 22px; font-weight: 600; letter-spacing: 0.2px;
    }}
    QLabel#subtitle {{
        color: {muted.name()}; margin-top: 2px;
    }}
    QLabel#section {{
        margin-top: 14px; margin-bottom: 6px;
        font-weight: 600; color: {muted.name()};
        letter-spacing: 0.3px; font-size: 11.5pt;
    }}

    /* Buttons */
    QPushButton {{
        background: {card.name()};
        border: 1px solid {border.name()};
        border-radius: 12px;
        padding: 10px 14px;
        text-align: left;
    }}
    QPushButton:hover {{ border-color: {accent.name()}; background: {_rgba(hover, 255)}; }}
    QPushButton:pressed {{ transform: translateY(1px); }}
    QPushButton#primary {{
        background: {accent.name()}; color: {accent_fg.name()};
        border: 1px solid {accent.name()};
    }}
    QPushButton#primary:hover {{ background: {_rgba(accent, 230)}; }}

    /* Recent list */
    QListWidget {{
        border: 1px solid {border.name()};
        border-radius: 12px;
        background: {card.name()};
        padding: 6px;
    }}
    QListWidget::item {{
        border-radius: 8px; padding: 10px;
        margin: 2px;
    }}
    QListWidget::item:hover {{
        background: {_rgba(hover, 255)};
    }}
    QListWidget::item:selected {{
        background: {_rgba(accent, 36)}; color: {fg.name()};
        border: 1px solid {accent.name()};
    }}

    /* Inputs in sub-dialog */
    QLineEdit {{
        border: 1px solid {border.name()};
        border-radius: 10px;
        padding: 8px 10px;
        background: {base.name()};
    }}
    QProgressBar {{
        border: 1px solid {border.name()};
        border-radius: 10px;
        text-align: center;
        height: 12px;
    }}
    QProgressBar::chunk {{
        background-color: {accent.name()};
        border-radius: 10px;
    }}
    """

# ---------- Optional: drag-and-drop image list for the create dialog ----------

class DraggableImageList(QListWidget):
    def __init__(self, accepted_extensions=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.accepted_extensions = accepted_extensions or [".png", ".jpg", ".jpeg", ".bmp", ".tif"]
        self.file_list = []
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

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

# ---------- Create Project sub-dialog ----------

class CreateProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Project")
        self.setMinimumWidth(520)
        self.setStyleSheet(_build_stylesheet(self))

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(10)

        # Location
        v.addWidget(QLabel("Save Project To:"))
        row1 = QHBoxLayout()
        self.path_input = QLineEdit(self._default_desktop_path())
        browse_btn = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), " Browse")
        browse_btn.clicked.connect(self._select_folder)
        row1.addWidget(self.path_input)
        row1.addWidget(browse_btn)
        v.addLayout(row1)

        # Name
        v.addWidget(QLabel("Project Name (letters, numbers, _ or -):"))
        self.name_input = QLineEdit("MyCoolProject")
        v.addWidget(self.name_input)

        # Import (optional)
        v.addWidget(QLabel("Import Images (optional)"))
        row2 = QHBoxLayout()
        import_btn = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), " Add Images…")
        row2.addWidget(import_btn)
        row2.addStretch(1)
        v.addLayout(row2)

        self.img_list = DraggableImageList()
        self.img_list.setMinimumHeight(120)
        v.addWidget(self.img_list)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        v.addWidget(self.progress)

        # Actions
        action_row = QHBoxLayout()
        action_row.addStretch(1)
        create_btn = QPushButton("Create Project")
        create_btn.setObjectName("primary")
        action_row.addWidget(create_btn)
        v.addLayout(action_row)

        # Wire
        import_btn.clicked.connect(self._import_images)
        create_btn.clicked.connect(self._finalize)

        self.selected_project_db = None  # will be set on success

    def _default_desktop_path(self):
        system_platform = platform.system()
        if system_platform == "Windows":
            return os.path.join(os.environ.get("USERPROFILE", str(pathlib.Path.home())), "Desktop")
        return str(pathlib.Path.home() / "Desktop")

    def _select_folder(self):
        start_dir = self._default_desktop_path()
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", start_dir)
        if folder:
            self.path_input.setText(folder)

    def _import_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            self._default_desktop_path(),
            "Images (*.png *.jpg *.jpeg *.bmp *.tif)"
        )
        for f in files:
            p = pathlib.Path(f).resolve()
            if p.is_file() and p.suffix.lower() in self.img_list.accepted_extensions:
                if str(p) not in self.img_list.file_list:
                    self.img_list.file_list.append(str(p))
                    self.img_list.addItem(p.name)

    def _finalize(self):
        base_dir = pathlib.Path(self.path_input.text()).expanduser().resolve()
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a project name.")
            return

        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            QMessageBox.warning(self, "Invalid Name", "Use letters, numbers, underscores or hyphens.")
            return

        project_path = base_dir / name
        if project_path.exists():
            QMessageBox.warning(self, "Exists", "This project folder already exists.")
            return

        try:
            (project_path / "images").mkdir(parents=True)
            (project_path / ".segmentme").mkdir(parents=True)

            for i, f in enumerate(self.img_list.file_list):
                dest = project_path / "images" / pathlib.Path(f).name
                shutil.copy(f, dest)
                self.progress.setValue(int((i + 1) / max(1, len(self.img_list.file_list)) * 100))

            # lightweight marker file
            with open(project_path / f"{name}.SEproj", "w") as fh:
                fh.write("SegmentME Project File")

            self.selected_project_db = str(project_path / ".segmentme" / "masks.db")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

# ---------- Minimal, elegant Start Dialog ----------

class ProjectStartupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SegmentME")
        self.setMinimumSize(560, 420)
        self.setModal(True)

        self.selected_project_path = None
        self.is_new_project = None

        self.setStyleSheet(_build_stylesheet(self))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(14)

        # Header
        title = QLabel("SegmentME")
        title.setObjectName("title")
        subtitle = QLabel("Start a new project or open a recent one")
        subtitle.setObjectName("subtitle")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        # Primary actions
        actions = QHBoxLayout()
        actions.setSpacing(10)

        new_btn = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "  New Project")
        new_btn.setObjectName("primary")
        new_btn.clicked.connect(self._create_project)



        actions.addWidget(new_btn, 1)
 
        outer.addLayout(actions)

        # Recents
        rec_label = QLabel("Recent")
        rec_label.setObjectName("section")
        outer.addWidget(rec_label)

        self.recent = QListWidget()
        self.recent.setUniformItemSizes(True)
        self.recent.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recent.itemActivated.connect(self._open_recent_item)
        outer.addWidget(self.recent, 1)

        self._populate_recents()

    # ------- Actions -------

    def _populate_recents(self):
        self.recent.clear()
        for path in load_recent_projects():
            if not os.path.exists(path):
                continue
            project_name = os.path.basename(os.path.dirname(os.path.dirname(path)))
            item = QListWidgetItem(project_name)              # show only the name
            item.setData(Qt.ItemDataRole.UserRole, path)      # keep path hidden for opening
            self.recent.addItem(item)


    def _create_project(self):
        dlg = CreateProjectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.selected_project_path = dlg.selected_project_db
            self.is_new_project = True
            self.accept()


   

    def _open_recent_item(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        self.selected_project_path = path
        self.is_new_project = False
        self.accept()
