from pathlib import Path
import numpy as np
import yaml
from shapely.geometry import Polygon
from PyQt6.QtWidgets import QProgressDialog
from PyQt6.QtCore import Qt

from services.logger import get_logger

logger = get_logger(__name__)

class BaseExporter:
    def __init__(self, parent):
        self.parent = parent
        self.export_dir = self.set_export_dir()

    def set_export_dir(self):
        base_dir = Path(self.parent.state_manager.project_root) / "labels"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

    def generate_data_yaml(self):
        class_manager = self.parent.state_manager.class_manager
        class_names = class_manager.get_all_class_names()
        num_classes = len(class_names)

        data_yaml = {
            "path": str(self.parent.project_root),
            "test": "autosplit_test.txt",
            "train": "autosplit_train.txt",
            "val": "autosplit_val.txt",
            "nc": num_classes,
            "names": {
                class_manager.get_idx_by_name(name) - 1: name for name in class_names
            }
        }

        yaml_path = Path(self.parent.state_manager.project_root) / "data.yaml"
        with yaml_path.open("w") as f:
            yaml.dump(data_yaml, f, default_flow_style=False, sort_keys=False)
        logger.info("Wrote dataset config (%d classes) to %s", num_classes, yaml_path)

    def _show_progress_dialog(self, total):
        progress_dialog = QProgressDialog("Exporting annotations...", "Cancel", 0, total, self.parent)
        progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress_dialog.setValue(0)
        return progress_dialog

    @staticmethod
    def simplify_polygon(mask, tolerance=0.01):
        polygon = Polygon(mask)
        return np.array(polygon.simplify(tolerance, preserve_topology=True).exterior.coords)
