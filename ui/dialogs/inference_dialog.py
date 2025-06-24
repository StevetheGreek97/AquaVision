import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDoubleSpinBox, QPushButton,
    QCheckBox, QSpinBox, QHBoxLayout
)
from PyQt6.QtWidgets import QComboBox

class InferenceDialog(QDialog):
    def __init__(self,model_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Inference")
        self.setMinimumWidth(300)
        self.model_dir = model_dir

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select Model:"))
        self.model_selector = QComboBox()
        layout.addWidget(self.model_selector)
        self.populate_models()
        # Confidence threshold input
        layout.addWidget(QLabel("Confidence Threshold:"))
        self.conf_spinbox = QDoubleSpinBox()
        self.conf_spinbox.setRange(0.0, 1.0)
        self.conf_spinbox.setSingleStep(0.05)
        self.conf_spinbox.setValue(0.25)
        self.conf_spinbox.setFixedWidth(100)
        layout.addWidget(self.conf_spinbox)



        # Run button
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.accept)
        layout.addWidget(self.run_button)

        self.setLayout(layout)


    def get_threshold(self):
        return self.conf_spinbox.value()

    def is_chunking_enabled(self):
        return self.chunk_checkbox.isChecked()

    def get_chunk_settings(self):
        return self.chunk_size_input.value(), self.chunk_overlap_input.value()

    def get_selected_model(self):
        return self.model_selector.currentText()
    
    def populate_models(self):
        models = [f for f in os.listdir(self.model_dir) if f.lower().endswith('.pt')]
        self.model_selector.addItems(models)

