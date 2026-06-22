import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QDoubleSpinBox,
    QPushButton, QFileDialog, QComboBox, QSpinBox, QDialogButtonBox,
    QHBoxLayout, QCheckBox
)


class InferenceDialog(QDialog):
    def __init__(self, model_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Inference")
        self.setMinimumWidth(420)
        self.model_dir = model_dir
        self.custom_model_path = None

        root = QVBoxLayout(self)
        root.setSpacing(14)

        # --- Model group -----------------------------------------------------
        model_box = QGroupBox("Model")
        model_form = QFormLayout()
        model_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.model_selector = QComboBox()
        self.model_selector.setToolTip("Choose a YOLO model (.pt).")
        self.model_selector.currentTextChanged.connect(self.handle_model_selection)
        self.populate_models()

        browse_hint = QLabel("Or choose a custom .pt file from disk.")
        browse_hint.setStyleSheet("color: #666; font-size: 11px;")
        browse_layout = QVBoxLayout()
        browse_layout.setSpacing(4)
        browse_layout.addWidget(self.model_selector)
        browse_layout.addWidget(browse_hint)

        model_form.addRow("Select model:", browse_layout)
        model_box.setLayout(model_form)
        root.addWidget(model_box)

        # --- Parameters group ------------------------------------------------
        params_box = QGroupBox("Parameters")
        params_form = QFormLayout()
        params_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Confidence
        self.conf_spinbox = QDoubleSpinBox()
        self.conf_spinbox.setRange(0.0, 1.0)
        self.conf_spinbox.setSingleStep(0.05)
        self.conf_spinbox.setDecimals(2)
        self.conf_spinbox.setValue(0.25)
        self.conf_spinbox.setToolTip("Detection confidence threshold (0–1).")
        params_form.addRow("Confidence:", self.conf_spinbox)


        # Image dimensions
        dims_row = QHBoxLayout()
        dims_row.setSpacing(8)

        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(16, 32768)
        self.width_spinbox.setValue(1024)
        self.width_spinbox.setSuffix(" px")
        self.width_spinbox.setToolTip("Input image width in pixels.")

        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(16, 32768)
        self.height_spinbox.setValue(1024)
        self.height_spinbox.setSuffix(" px")
        self.height_spinbox.setToolTip("Input image height in pixels.")

        self.lock_aspect = QCheckBox("Lock aspect ratio")
        self.lock_aspect.setChecked(False)
        self.lock_aspect.setToolTip("Keep height proportional when width changes.")

        # when locked, adjust height on width changes
        self._aspect_ratio = self.height_spinbox.value() / max(1, self.width_spinbox.value())

        def update_ratio():
            # store ratio when user edits both fields while unlocked
            w = max(1, self.width_spinbox.value())
            h = self.height_spinbox.value()
            self._aspect_ratio = h / w

        def on_width_changed():
            if self.lock_aspect.isChecked():
                w = self.width_spinbox.value()
                self.height_spinbox.blockSignals(True)
                self.height_spinbox.setValue(int(round(w * self._aspect_ratio)))
                self.height_spinbox.blockSignals(False)

        self.width_spinbox.valueChanged.connect(on_width_changed)
        self.width_spinbox.editingFinished.connect(update_ratio)
        self.height_spinbox.editingFinished.connect(update_ratio)

        dims_row.addWidget(self.width_spinbox, 1)
        dims_row.addWidget(self.height_spinbox, 1)

        dims_col = QVBoxLayout()
        dims_col.addLayout(dims_row)
        dims_col.addWidget(self.lock_aspect)

        params_form.addRow("Image size:", dims_col)


        # --- HiReS toggle ----------------------------------------------------
        self.hires_checkbox = QCheckBox("HiReS (HiResolution Segmentation)")
        self.hires_checkbox.setToolTip("If checked, use HiReS with chunking, overlap and extra thresholds.")
        self.hires_checkbox.toggled.connect(self.on_hires_toggled)
        params_form.addRow(self.hires_checkbox)

        # --- HiReS settings (initially hidden) -------------------------------
        self.hires_box = QGroupBox("HiReS Settings")
        hires_form = QFormLayout()
        self.hires_box.setLayout(hires_form)




        # chunk_size = (1024, 1024)
        chunk_row = QHBoxLayout()
        self.chunk_width_spinbox = QSpinBox()
        self.chunk_width_spinbox.setRange(64, 32768)
        self.chunk_width_spinbox.setValue(1024)
        self.chunk_width_spinbox.setSuffix(" px")


        self.chunk_height_spinbox = QSpinBox()
        self.chunk_height_spinbox.setRange(64, 32768)
        self.chunk_height_spinbox.setValue(1024)
        self.chunk_height_spinbox.setSuffix(" px")

        # overlap = 300
        self.overlap_spinbox = QSpinBox()
        self.overlap_spinbox.setRange(0, 5000)
        self.overlap_spinbox.setValue(300)
        self.overlap_spinbox.setSuffix(" px")
        hires_form.addRow("Overlap:", self.overlap_spinbox)

        chunk_row.addWidget(self.chunk_width_spinbox)
        chunk_row.addWidget(self.chunk_height_spinbox)
        hires_form.addRow("Chunk size (W×H):", chunk_row)


        # iou_thresh = 0.7
        self.iou_spinbox = QDoubleSpinBox()
        self.iou_spinbox.setRange(0.0, 1.0)
        self.iou_spinbox.setDecimals(2)
        self.iou_spinbox.setSingleStep(0.05)
        self.iou_spinbox.setValue(0.70)
        hires_form.addRow("IoU threshold:", self.iou_spinbox)

        # hidden by default
        self.hires_box.setVisible(False)
        params_form.addRow(self.hires_box)

        params_box.setLayout(params_form)
        root.addWidget(params_box)

        # --- Buttons ---------------------------------------------------------
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Run")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        # Focus the model selector first for smooth UX
        self.model_selector.setFocus()

    # ------------------------ helpers ---------------------------------------
    def populate_models(self):
        models = [f for f in os.listdir(self.model_dir) if f.lower().endswith(".pt")]
        models.sort()
        self.model_selector.clear()
        self.model_selector.addItems(models)
        self.model_selector.addItem("📁 Browse for custom model...")

    def handle_model_selection(self, selected_text):
        if selected_text == "📁 Browse for custom model...":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Custom Model", "", "PyTorch Model (*.pt)"
            )
            # If selected, insert at top and select it; else revert to first item
            if file_path:
                self.custom_model_path = file_path
                base = os.path.basename(file_path)
                if self.model_selector.findText(base) == -1:
                    self.model_selector.insertItem(0, base)
                self.model_selector.setCurrentIndex(0)
            else:
                self.model_selector.setCurrentIndex(0)
                self.custom_model_path = None

    def on_hires_toggled(self, checked: bool):
        """Show/hide HiReS settings when the checkbox is toggled."""
        self.hires_box.setVisible(checked)


    # ------------------------ getters ---------------------------------------
    def get_selected_model(self):
        if self.custom_model_path and self.model_selector.currentIndex() == 0:
            return self.custom_model_path
        return os.path.join(self.model_dir, self.model_selector.currentText())

    def get_threshold(self):
        return float(self.conf_spinbox.value())

    def get_image_dimensions(self):
        """Returns (width, height) as ints."""
        return int(self.width_spinbox.value()), int(self.height_spinbox.value())
    
    def get_chunk_dimensions(self):
        """Returns (width, height) as ints."""
        return (int(self.chunk_width_spinbox.value()), int(self.chunk_height_spinbox.value()))

    def is_hires_enabled(self):
        return self.hires_checkbox.isChecked()

    def get_hires_params(self):
        """
        Return a dict with HiReS parameters if enabled, else None.

        This is shaped so you can do:

            hp = dialog.get_hires_params()
            if hp:
                cfg = Settings(
                    conf=hp["conf"],
                    imgsz=hp["imgsz"],
                    device=hp["device"],
                    chunk_size=hp["chunk_size"],
                    overlap=hp["overlap"],
                    edge_threshold=hp["edge_threshold"],
                    iou_thresh=hp["iou_thresh"],
                )
                Pipeline(cfg).run(
                    input_path=raw_image_path,
                    model_path=model_path,
                    output_dir=hp["output_dir"],
                    workers=hp["workers"],
                )
        """
        if not self.is_hires_enabled():
            return None


        return {
            "conf": self.get_threshold(),
            'iou': self.iou_spinbox.value(),
            "overlap": int(self.overlap_spinbox.value()),
            'chunk': self.get_chunk_dimensions(),
            'imgsz': self.get_image_dimensions()

        }
