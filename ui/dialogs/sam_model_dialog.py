from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QRadioButton, QButtonGroup,
    QDialogButtonBox, QGroupBox
)

from core.tools import sam_registry
from services.logger import get_logger

logger = get_logger(__name__)


class SamModelDialog(QDialog):
    """
    Lets the user pick which SAM model variant the sidebar's SAM tool runs.

    Variants whose checkpoint is not in sam2_configs/ are shown greyed out
    with their download URL in the tooltip.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SAM Model")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Model used by the SAM tool:"))

        self.button_group = QButtonGroup(self)
        current_key = sam_registry.get_selected_key()

        # Group variants by family/generation for a tidy list
        groups = [
            ("SAM2", lambda k: k.startswith("sam2_")),
            ("SAM2.1", lambda k: k.startswith("sam2.1_")),
            ("SAM3", lambda k: k == "sam3"),
        ]
        for title, belongs in groups:
            box = QGroupBox(title, self)
            box_layout = QVBoxLayout(box)
            for variant in sam_registry.SAM_VARIANTS.values():
                if not belongs(variant.key):
                    continue
                radio = QRadioButton(f"{variant.label} — {variant.description}", box)
                radio.setProperty("variant_key", variant.key)
                if sam_registry.is_available(variant):
                    radio.setToolTip(str(sam_registry.checkpoint_path(variant)))
                else:
                    radio.setText(radio.text() + "  (not downloaded)")
                    radio.setEnabled(False)
                    radio.setToolTip(
                        f"Download from {variant.download_url} and place the "
                        "checkpoint in the sam2_configs folder."
                    )
                if variant.key == current_key:
                    radio.setChecked(True)
                self.button_group.addButton(radio)
                box_layout.addWidget(radio)
            layout.addWidget(box)

        hint = QLabel(
            "Greyed-out models are not downloaded yet — hover one to see "
            "where to get its checkpoint.", self
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(Mid); font-size: 11px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_key(self):
        """The key of the chosen variant, or None if nothing is checked."""
        checked = self.button_group.checkedButton()
        return checked.property("variant_key") if checked else None
