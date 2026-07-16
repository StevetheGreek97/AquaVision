import cv2
import shutil
from ultralytics.data.split import autosplit
from PyQt6.QtWidgets import QMessageBox
from core.exporters.base_exporter import BaseExporter
from services.file_handlers import normalize_coordinates, write_annotations_to_file
from services.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)


class YOLOExporter(BaseExporter):
    def export_all_annotations(self, train_pct, val_pct, test_pct):
        if not self.parent.state_manager.image_paths:
            logger.warning("Export requested with no images loaded; ignoring")
            return

        if self.export_dir.exists():
            reply = QMessageBox.warning(
                self.parent,
                "Overwrite Existing Labels",
                f"The labels folder already exists at:\n\n{self.export_dir}\n\n"
                "Do you want to overwrite it?\nAll existing label files will be deleted.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                logger.info("Export cancelled by user (labels folder exists)")
                return

            shutil.rmtree(self.export_dir)
            logger.info("Deleted existing labels folder %s", self.export_dir)

        self.export_dir.mkdir(parents=True, exist_ok=True)

        progress_dialog = self._show_progress_dialog(len(self.parent.state_manager.image_paths))

        logger.info("Exporting YOLO annotations for %d image(s) to %s (split %d/%d/%d)",
                    len(self.parent.state_manager.image_paths), self.export_dir,
                    train_pct, val_pct, test_pct)

        for index, image_path in enumerate(self.parent.state_manager.image_paths):
            if progress_dialog.wasCanceled():
                logger.info("Export cancelled by user after %d image(s)", index)
                break

            try:
                self._process_image(Path(image_path))
            except Exception:
                logger.exception("Failed to export annotations for %s; continuing", image_path)

            progress_dialog.setValue(index + 1)

        split_weights = (train_pct / 100, val_pct / 100, test_pct / 100)
        autosplit(
            path=Path(self.parent.state_manager.project_root) / "images",
            weights=split_weights,
            annotated_only=False
        )

        self.generate_data_yaml()
        progress_dialog.close()
        logger.info("YOLO export finished")

    def _process_image(self, image_path: Path):
        image_name = image_path.stem
        masks, class_ids = self.fetch_image_masks_from_db(image_name)

        if not masks:
            logger.debug("No masks for image %s; skipped", image_name)
            return

        image = self._load_image(image_path)
        h, w, _ = image.shape

        yolo_annotations = self._convert_masks_to_yolo(masks, class_ids, w, h)
        write_annotations_to_file(image_name, yolo_annotations, self.export_dir)

    def fetch_image_masks_from_db(self, image_name):
        db_masks = self.parent.state_manager.mask_manager.load_masks(image_name)
        if not db_masks:
            return [], []

        masks, class_ids = [], []
        for mask_id, mask_array, class_name, _ in db_masks:
            class_id = self.parent.state_manager.class_manager.get_idx_by_name(class_name)
            if class_id is None:
                logger.warning("Class %r not found for mask %s; mask skipped in export",
                               class_name, mask_id)
                continue
            masks.append(mask_array)
            class_ids.append(class_id)

        return masks, class_ids

    def _load_image(self, image_path: Path):
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"❌ Failed to load image: {image_path}")
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def _convert_masks_to_yolo(self, masks, class_ids, img_width, img_height):
        return [
            f"{class_id - 1} " + " ".join(f"{coord:.6f}" for coord in normalize_coordinates(
                self.simplify_polygon(mask), img_width, img_height
            ).flatten())
            for class_id, mask in zip(class_ids, masks)
        ]
