import os
import numpy as np
import torch
import cv2
from PyQt6.QtGui import QPen, QColor, QPolygonF, QBrush
from PyQt6.QtWidgets import QGraphicsPolygonItem, QMessageBox
from PyQt6.QtCore import pyqtSignal, QObject, QPointF, QRunnable, QThreadPool, Qt
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
from core.tools.sam2_loader import load_sam2_model
from services.logger import get_logger

logger = get_logger(__name__)


class MaskGenerationTask(QRunnable):
    """
    Background task for generating masks using SAM2 without freezing the UI.
    """

    def __init__(self, parent, image):
        super().__init__()
        self.parent = parent
        self.image = image

    def run(self):
        """
        Execute the mask generation process in a separate thread.
        """
        try:
            logger.debug("Running SAM2 automatic mask generation in background thread")
            masks = self.parent.mask_generator.generate(self.image)

            if not masks:
                logger.warning("SAM2 automatic generation produced no masks")
                return

            self.parent.current_masks = masks  # Store masks
            self.parent.display_masks(masks)  # Display masks

            # Ask user if they want to save the masks
            self.parent.ask_user_to_save_masks(masks)

            logger.info("SAM2 automatic generation produced %d mask(s)", len(masks))

        except Exception:
            logger.exception("SAM2 automatic mask generation failed")


class Sam2Auto(QObject):
    """
    A class for automatically generating segmentation masks using the SAM2 model.
    """

    def __init__(self, parent, device: str = "cpu"):
        """
        Initialize the automatic mask generator.

        Args:
            parent: Reference to the parent ImageDisplay instance.
            device (str): Device to run the model on ('cpu' or 'cuda').
        """
        super().__init__()
        self.parent = parent
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        # Load the SAM2 model
        self.mask_generator = self._load_sam2_model()

        self.current_masks = []  # Store generated masks
        self.current_polygon_items = []  # Store displayed polygons
        self.thread_pool = QThreadPool()  # Thread pool for background tasks

    def _load_sam2_model(self):
        """Load the SAM 2 model once."""
        return SAM2AutomaticMaskGenerator(load_sam2_model(self.device))

    def generate_masks(self, image: np.ndarray):
        """
        Generate segmentation masks for the given image in a background thread.

        Args:
            image (numpy.ndarray): The input image for mask generation.
        """
        if image is None:
            logger.warning("Cannot generate masks: no image provided")
            return

        task = MaskGenerationTask(self, image)
        self.thread_pool.start(task)

    def display_masks(self, masks):
        """
        Display generated masks as polygons on the scene.

        Args:
            masks (list): List of segmentation mask dictionaries.
        """
        # Clear previous masks
        for item in self.current_polygon_items:
            self.parent.image_display.scene.removeItem(item)
        self.current_polygon_items = []

        for mask_data in masks:
            mask = mask_data["segmentation"]

            # Extract contours
            contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                polygon_points = contour.squeeze(axis=1).tolist()
                if len(polygon_points) < 3:
                    continue  # Skip invalid polygons

                self.display_polygon(polygon_points)

    def display_polygon(self, polygon_points: list, color=QColor(0, 255, 0), line_width: int = 2):
        """
        Display a polygon on the scene using the provided points.

        Args:
            polygon_points (list): List of (x, y) tuples representing the polygon vertices.
            color (QColor): Color of the polygon outline.
            line_width (int): Width of the polygon lines.
        """
        if not polygon_points:
            logger.warning("No polygon points to display.")
            return

        polygon = QPolygonF([QPointF(x, y) for x, y in polygon_points])
        pen = QPen(color)
        pen.setWidth(line_width)

        # ✅ Correct way to set brush (semi-transparent fill)
        brush = QBrush(color)
        brush.setStyle(Qt.BrushStyle.SolidPattern)  # Use a solid fill style

        polygon_item = QGraphicsPolygonItem(polygon)
        polygon_item.setPen(pen)
        polygon_item.setBrush(brush)  # Apply corrected brush

        self.parent.image_display.scene.addItem(polygon_item)
        self.current_polygon_items.append(polygon_item)  # Store for later clearing

    def ask_user_to_save_masks(self, masks):
        """
        Ask the user if they want to save the generated masks to the database.
        """
        image_name = self.parent.state_manager.current_image_name

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setText(f"Do you want to save the {len(masks)} masks?")
        msg_box.setWindowTitle("Save Masks")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        response = msg_box.exec()

        if response == QMessageBox.StandardButton.Yes:
            self.save_masks_to_database(masks, image_name)
        else:
            logger.debug("User declined to save auto-generated masks")

    def save_masks_to_database(self, masks, image_name):
        """
        Save the generated masks to the database under the class name 'object'.
        """
        class_name = "object"  # Default class name for auto-generated masks

        for mask_data in masks:
            mask = mask_data["segmentation"]
            self.parent.state_manager.mask_manager.save_mask(mask, image_name, class_name)

        logger.info("Saved %d auto-generated mask(s) for image %s", len(masks), image_name)

    def clear_masks(self):
        """
        Clear all displayed masks.
        """
        for item in self.current_polygon_items:
            self.parent.image_display.scene.removeItem(item)
        self.current_polygon_items = []
        self.current_masks = []
        logger.debug("Cleared displayed masks")
