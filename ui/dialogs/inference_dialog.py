import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDoubleSpinBox, QPushButton, QFileDialog, QComboBox
)

class InferenceDialog(QDialog):
    def __init__(self, model_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Inference")
        self.setMinimumWidth(300)
        self.model_dir = model_dir
        self.custom_model_path = None  # Store custom path

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select Model:"))

        self.model_selector = QComboBox()
        self.model_selector.currentTextChanged.connect(self.handle_model_selection)
        layout.addWidget(self.model_selector)
        self.populate_models()

        layout.addWidget(QLabel("Confidence Threshold:"))
        self.conf_spinbox = QDoubleSpinBox()
        self.conf_spinbox.setRange(0.0, 1.0)
        self.conf_spinbox.setSingleStep(0.05)
        self.conf_spinbox.setValue(0.25)
        self.conf_spinbox.setFixedWidth(100)
        layout.addWidget(self.conf_spinbox)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.accept)
        layout.addWidget(self.run_button)

        self.setLayout(layout)

    def populate_models(self):
        models = [f for f in os.listdir(self.model_dir) if f.lower().endswith('.pt')]
        self.model_selector.addItems(models)
        self.model_selector.addItem("📁 Browse for custom model...")  # Add option at the end

    def handle_model_selection(self, selected_text):
        if selected_text == "📁 Browse for custom model...":
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Custom Model", "", "PyTorch Model (*.pt)")
            if file_path:
                self.custom_model_path = file_path
                self.model_selector.insertItem(0, os.path.basename(file_path))
                self.model_selector.setCurrentIndex(0)
            else:
                # Reset to default if cancelled
                self.model_selector.setCurrentIndex(0)
                self.custom_model_path = None

    def get_selected_model(self):
        if self.custom_model_path and self.model_selector.currentIndex() == 0:
            return self.custom_model_path
        return os.path.join(self.model_dir, self.model_selector.currentText())

    def get_threshold(self):
        return self.conf_spinbox.value()
