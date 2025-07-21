import os
import yaml
import datetime
from PyQt6.QtWidgets import QFileDialog, QProgressDialog
from PyQt6.QtCore import Qt


class BaseExporter:
    """
    Base class for dataset annotation exporters.
    Provides methods for exporting annotation files and handling directory structures.
    """

    def __init__(self, parent):
        self.parent = parent
        self.export_dir = self.set_export_dir()


    def set_export_dir(self, base_dir=None):
        """
        Sets the export directory path and ensures it exists.
        """

        base_dir = os.path.join(self.parent.project_root, "labels")
   


        os.makedirs(base_dir, exist_ok=True)
        return base_dir




    def generate_data_yaml(self):
        """
        Generate the `data.yaml` file with the correct order and format.
        """
        class_manager = self.parent.state_manager.class_manager
        class_names = class_manager.get_all_class_names()
        num_classes = len(class_names)

        data_yaml = {
            "path": self.parent.project_root,
            "test": "autosplit_test.txt",
            "train": "autosplit_train.txt",
            "val": "autosplit_val.txt",
            "nc": num_classes,
            "names": {
                class_manager.get_idx_by_name(name) - 1: name for name in class_names
            }
        }

        yaml_path = os.path.join(self.parent.project_root, "data.yaml")
        with open(yaml_path, "w") as yaml_file:
            yaml.dump(data_yaml, yaml_file, default_flow_style=False, sort_keys=False)

        print(f"✅ data.yaml saved at: {yaml_path}")

    def _show_progress_dialog(self, total):
        """
        Create and return a progress dialog.
        """
        progress_dialog = QProgressDialog("Exporting annotations...", "Cancel", 0, total, self.parent)
        progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress_dialog.setValue(0)
        return progress_dialog

