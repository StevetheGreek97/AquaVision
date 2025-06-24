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
        self.export_dir = None

    @property
    def project_root(self):
        """
        Get the root folder of the project based on the database location.
        Assumes DB is in: <project_root>/.segmentme/masks.db
        """
        return os.path.dirname(os.path.dirname(self.parent.state_manager.db.db_path))

    def set_export_dir_with_timestamp(self, base_dir=None):
        """
        Set self.export_dir to a timestamped subfolder inside base_dir or default 'annotations' folder.
        """
        if base_dir is None:
            base_dir = os.path.join(self.project_root, "annotations")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.export_dir = os.path.join(base_dir, timestamp)
        os.makedirs(self.annotations_dir, exist_ok=True)

    @property
    def annotations_dir(self):
        """
        Returns the annotations directory inside the selected export directory.
        """
        return os.path.join(self.export_dir, "")

    def generate_data_yaml(self):
        """
        Generate the `data.yaml` file with class ID and name mappings.
        """
        class_manager = self.parent.state_manager.class_manager
        class_names = class_manager.get_all_class_names()

        data_yaml = {
            "names": {class_manager.get_idx_by_name(name) - 1: name for name in class_names}
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
