import os
import yaml
from PyQt6.QtWidgets import QFileDialog, QProgressDialog
from PyQt6.QtCore import Qt


class BaseExporter:
    """
    Base class for dataset annotation exporters.
    Provides methods for exporting annotation files and handling directory structures.
    """

    def __init__(self, parent):
        self.parent = parent
        self.export_dir = None

    def select_export_directory(self):
        """
        Open a file dialog for the user to select the export directory.
        """
        self.export_dir = QFileDialog.getExistingDirectory(None, "Select Export Folder")
        if not self.export_dir:
            print("❌ No folder selected for export.")
            return False

        os.makedirs(self.annotations_dir, exist_ok=True)
        return True

    @property
    def annotations_dir(self):
        """
        Returns the annotations directory path inside the selected export directory.
        """
        return os.path.join(self.export_dir, "annotations")

    def generate_data_yaml(self):
        """
        Generate the `data.yaml` file with class ID and name mappings.
        """
        class_manager = self.parent.state_manager.class_manager
        class_names = class_manager.get_all_class_names()

        data_yaml = {
            "names": {class_manager.get_idx_by_name(name): name for name in class_names}
        }

        yaml_path = os.path.join(self.annotations_dir, "data.yaml")
        with open(yaml_path, "w") as yaml_file:
            yaml.dump(data_yaml, yaml_file, default_flow_style=False)

        print(f"✅ data.yaml saved at: {yaml_path}")

    def _show_progress_dialog(self, total):
        """
        Create and return a progress dialog.
        """
        progress_dialog = QProgressDialog("Exporting annotations...", "Cancel", 0, total, self.parent)
        progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress_dialog.setValue(0)
        return progress_dialog
