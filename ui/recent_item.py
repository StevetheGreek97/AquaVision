# ui/widgets/recent_item.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt

class RecentItemWidget(QWidget):
    def __init__(self, project_name: str, db_path: str, on_open, on_delete, parent=None):
        super().__init__(parent)
        self.db_path = db_path

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)

        title = QLabel(project_name)
        title.setStyleSheet("font-weight:600;")
        title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        open_btn = QPushButton("Open")
        del_btn  = QPushButton("Delete")
        open_btn.setObjectName("action")
        del_btn.setObjectName("action")


        # Let the buttons be wide enough for text (padding is 14px left/right)
        for b in (open_btn, del_btn):
            b.setMinimumWidth(90)                  # <<< was 20
            b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        open_btn.clicked.connect(lambda: on_open(self.db_path))
        del_btn.clicked.connect(lambda: on_delete(self.db_path))

        text_box = QWidget()
        tl = QHBoxLayout(text_box)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(20)
        tl.addWidget(title)

        lay.addWidget(text_box, 1)   # <<< give text area stretch so buttons don’t get squeezed
        lay.addWidget(open_btn, 0)
        lay.addWidget(del_btn, 0)
        self.setMinimumHeight(50)

