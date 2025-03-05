from PyQt6.QtWidgets import QFileDialog, QProgressDialog
import cv2
import numpy as np
from services.file_handlers import normalize_coordinates, write_annotations_to_file
from core.data import DataManager
from PyQt6.QtCore import Qt
import os
import re
import yaml 

class YOLOAnnotationExporter:
    """
    Handles exporting YOLO segmentation annotations for all images without threading.
    """

    def __init__(self, parent):
        self.parent = parent


    def export_all_annotations(self):
        """
        Export YOLO annotations for all images in the dataset and generate a data.yaml file.
        """
        if not self.parent.state_manager.image_paths:
            print("No images loaded to export annotations.")
            return

        export_dir = QFileDialog.getExistingDirectory(None, "Select Export Folder")
        if not export_dir:
            print("No folder selected for export.")
            return

        # Create 'annotations' subfolder inside the selected export directory
        annotations_dir = os.path.join(export_dir, "annotations")
        os.makedirs(annotations_dir, exist_ok=True)

        # Progress Dialog
        total_images = len(self.parent.state_manager.image_paths)
        progress_dialog = QProgressDialog("Exporting annotations...", "Cancel", 0, total_images, self.parent)
        progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress_dialog.setValue(0)

        for index, image_path in enumerate(self.parent.state_manager.image_paths):
            if progress_dialog.wasCanceled():
                print("Export canceled by the user.")
                break

            try:
                # Get the image name (without extension) to match with masks
                image_name = os.path.splitext(os.path.basename(image_path))[0]
                print(image_name)

                # Retrieve all associated masks using the new naming convention
                mask_files = [
                    file for file in os.listdir('masks/')
                    if re.match(rf"^{re.escape(image_name)}\|\|mask_\d+\|\|.+\.dat$", file)
                ]

                if not mask_files:
                    print(f"No masks found for image: {image_name}")
                    continue

                # Load the image
                image = cv2.imread(image_path)
                if image is None:
                    raise ValueError(f"Failed to load image: {image_path}")

                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                img_height, img_width, _ = image.shape

                # Process each mask for the current image
                masks = []
                class_ids = []
                for mask_file in mask_files:
                    mask = DataManager().load_mask(os.path.join('masks/', mask_file))
                    
                    # Parse the filename based on the new naming convention
                    parts = mask_file.split("||")
                    mask_id = parts[1]  # Example: "mask_1"
                    class_name = parts[2].replace('.dat', '').strip()  # Remove '.dat'
                    class_id = self.parent.state_manager.class_manager.get_idx_by_name(class_name)

                    masks.append(mask)
                    class_ids.append(class_id)

                # Generate YOLO annotations
                yolo_annotations = self._process_masks(masks, class_ids, img_width, img_height)

                # Write annotations to file inside the "annotations" folder
                write_annotations_to_file(image_name, yolo_annotations, annotations_dir)

            except Exception as e:
                print(f"Error processing {image_path}: {e}")

            # Update progress
            progress_dialog.setValue(index + 1)

        # Generate the data.yaml file
        self.generate_data_yaml(annotations_dir)

        progress_dialog.close()
        print(f"All annotations exported to: {annotations_dir}")


    def generate_data_yaml(self, annotations_dir):
        """
        Generate the data.yaml file with class ID and name mappings.
        """
        class_manager = self.parent.state_manager.class_manager
        class_names = class_manager.get_all_class_names()

        # Create a dictionary for YAML format
        data_yaml = {
            "names": {class_manager.get_idx_by_name(name): name for name in class_names}
        }

        # Save as a YAML file
        yaml_path = os.path.join(annotations_dir, "data.yaml")
        with open(yaml_path, "w") as yaml_file:
            yaml.dump(data_yaml, yaml_file, default_flow_style=False)

        print(f"data.yaml saved at: {yaml_path}")


    @staticmethod
    def _process_masks(masks, class_ids, img_width, img_height, simplify_tolerance=0.01):
        """
        Convert masks to YOLO format.
        """
        yolo_annotations = []
        for class_id, mask in zip(class_ids, masks):
            simplified_mask = YOLOAnnotationExporter.simplify_polygon(mask, simplify_tolerance)
            normalized_mask = normalize_coordinates(simplified_mask, img_width, img_height)
            flattened_coords = normalized_mask.flatten()
            annotation = f"{class_id} " + " ".join(f"{coord:.6f}" for coord in flattened_coords)
            yolo_annotations.append(annotation)
        return yolo_annotations

    @staticmethod
    def simplify_polygon(mask, tolerance=0.1):
        """
        Simplify the polygon to reduce the number of points.
        """
        from shapely.geometry import Polygon
        polygon = Polygon(mask)
        simplified = polygon.simplify(tolerance, preserve_topology=True)
        return np.array(simplified.exterior.coords)
