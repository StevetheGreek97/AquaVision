import os
import cv2
import numpy as np
from shapely.geometry import Polygon
from services.file_handlers import normalize_coordinates, write_annotations_to_file
from core.exporters.base_exporter import BaseExporter
from ultralytics.data.split import autosplit
import shutil
from PyQt6.QtWidgets import QMessageBox
class YOLOExporter(BaseExporter):
    """
    Handles exporting YOLO segmentation annotations.
    """

    def export_all_annotations(self,  train_pct, val_pct, test_pct):
        """
        Export YOLO annotations for all images and generate a data.yaml file.
        """
        if not self.parent.state_manager.image_paths:
            print("❌ No images loaded to export annotations.")
            return

        # Determine labels directory

        if os.path.exists(self.export_dir):
            reply = QMessageBox.warning(
                self.parent,
                "Overwrite Existing Labels",
                f"The labels folder already exists at:\n\n{self.export_dir}\n\n"
                "Do you want to overwrite it?\nAll existing label files will be deleted.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                print("❌ Export cancelled by user to prevent overwriting.")
                return

            # Delete the existing labels folder
            shutil.rmtree(self.export_dir)
            print(f"⚠️ Existing labels folder deleted: {self.export_dir}")

        # Create the labels directory
        os.makedirs(self.export_dir, exist_ok=True)



        progress_dialog = self._show_progress_dialog(len(self.parent.state_manager.image_paths))

        for index, image_path in enumerate(self.parent.state_manager.image_paths):
            if progress_dialog.wasCanceled():
                print("❌ Export canceled by the user.")
                break

            try:
                self._process_image(image_path)
            except Exception as e:
                print(f"❌ Error processing {image_path}: {e}")

            progress_dialog.setValue(index + 1)
        split_weights = (train_pct / 100, val_pct / 100, test_pct / 100)
        print(f'{self.export_dir} export_dir')
        autosplit(path=os.path.join(self.parent.project_root, "images"), weights=split_weights, annotated_only=False)

        self.generate_data_yaml()
        progress_dialog.close()


    def _process_image(self, image_path):
        """
        Process a single image: retrieve masks, convert them, and save as a YOLO annotation file.
        """
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        masks, class_ids = self.fetch_image_masks_from_db(image_name)

        if not masks:
            print(f"⚠️ No masks found for image: {image_name}. Skipping...")
            return

        image = self._load_image(image_path)
        img_height, img_width, _ = image.shape


        yolo_annotations = self._convert_masks_to_yolo(masks, class_ids, img_width, img_height)

        write_annotations_to_file(image_name, yolo_annotations, self.export_dir)

    def fetch_image_masks_from_db(self, image_name):
        """
        Fetch all masks and their corresponding class IDs for a given image from the database.
        """
        db_masks = self.parent.state_manager.mask_manager.load_masks(image_name)

        if not db_masks:
            return [], []

        masks, class_ids = [], []
        for mask_id, mask_array, class_name, _ in db_masks:
            class_id = self.parent.state_manager.class_manager.get_idx_by_name(class_name)
            if class_id is None:
                print(f"❌ Warning: Class '{class_name}' not found for mask ID {mask_id}. Skipping...")
                continue

            masks.append(mask_array)
            class_ids.append(class_id)

        return masks, class_ids

    def _load_image(self, image_path):
        """
        Load an image and return its dimensions.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"❌ Failed to load image: {image_path}")
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)



    def _convert_masks_to_yolo(self, masks, class_ids, img_width, img_height):
        """
        Convert masks into YOLO format.
        """
        return [
            f"{class_id - 1} " + " ".join(f"{coord:.6f}" for coord in normalize_coordinates(
                self._simplify_polygon(mask), img_width, img_height
            ).flatten())
            for class_id, mask in zip(class_ids, masks)
        ]

    @staticmethod
    def _simplify_polygon(mask, tolerance=0.01):
        """
        Simplify the polygon to reduce unnecessary points.
        """
        polygon = Polygon(mask)
        return np.array(polygon.simplify(tolerance, preserve_topology=True).exterior.coords)
