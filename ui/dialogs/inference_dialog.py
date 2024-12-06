import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox

class InferenceDialog(QDialog):
    def __init__(self, model_dir, parent):
        super().__init__(parent)
        self.setWindowTitle("Run Inference")
        self.model_dir = model_dir
        self.selected_model = None

        # Layout and widgets
        layout = QVBoxLayout()
        self.model_selector = QComboBox()
        self.populate_models()
        layout.addWidget(QLabel("Select Model"))
        layout.addWidget(self.model_selector)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def populate_models(self):
        """
        Populate the dropdown with models from the specified directory.
        """
        models = [f for f in os.listdir(self.model_dir) if f.lower().endswith('.pt')]
        print(f"Models found: {models}")  # Debug
        self.model_selector.addItems(models)

    def get_selected_model(self):
        """
        Return the selected model from the dropdown.
        """
        return self.model_selector.currentText()