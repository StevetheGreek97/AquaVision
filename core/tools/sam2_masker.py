import numpy as np
from PyQt6.QtGui import QPen, QColor, QPolygonF
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPolygonItem
from PyQt6.QtCore import pyqtSignal, QObject, QPointF
from sam2.sam2_image_predictor import SAM2ImagePredictor
from sam2.build_sam import build_sam2
import torch
import cv2
from services.file_handlers import get_resource_path
from services.logger import get_logger

logger = get_logger(__name__)


class SamMasker2(QObject):
    """
    A class for creating masks interactively using the SAM 2 model.
    """
    mask_added = pyqtSignal(str, np.ndarray)

    def __init__(self, parent, device: str = "cpu"):
        """
        Initialize the Sam2 class.

        Args:
            parent: Reference to the parent ImageDisplay instance.
            device (str): Device to run the model on ('cpu' or 'cuda').
        """
        super().__init__()
        self.parent = parent
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        # Load the SAM 2 model
        self.predictor = self._load_sam2_model()

        # Interactive points and items
        self.foreground_points = []
        self.background_points = []
        self.foreground_items = []
        self.background_items = []

        self.current_polygon_item = None  # Reference to displayed polygon
        self.mask = None

    def _load_sam2_model(self):
        """Load the SAM 2 model once."""
        model_path = get_resource_path("sam2_configs/sam2_hiera_tiny.pt")
        logger.info("Loading SAM2 model from %s (device=%s)", model_path, self.device)
        sam2_model = build_sam2("sam2_hiera_t.yaml", model_path, device=self.device)
        return SAM2ImagePredictor(sam2_model)

    def _add_graphics_point(self, point: tuple, label: int):
        """Helper function to add a point to the scene."""
        color = QColor(0, 255, 0) if label == 1 else QColor(255, 0, 0)
        pen = QPen(color, 2)

        ellipse = QGraphicsEllipseItem(point[0] - 2, point[1] - 2, 4, 4)
        ellipse.setPen(pen)
        ellipse.setBrush(color)
        self.parent.scene.addItem(ellipse)

        return ellipse

    def add_point(self, point: tuple, label: int):
        """
        Add a point to the appropriate list (foreground or background).

        Args:
            point (tuple): The point to add as (x, y).
            label (int): The label for the point (1 for foreground, 0 for background).
        """
        ellipse = self._add_graphics_point(point, label)

        if label == 1:
            self.foreground_points.append(point)
            self.foreground_items.append(ellipse)
        else:
            self.background_points.append(point)
            self.background_items.append(ellipse)

        logger.debug("Added %s point at %s",
                     "foreground" if label == 1 else "background", point)

    def display_polygon(self, polygon_points: list, color=QColor(0, 255, 0), line_width: int = 2):
        """
        Display a polygon on the scene using the provided points.

        Args:
            polygon_points (list): List of (x, y) tuples representing the polygon vertices.
            color (QColor): Color of the polygon outline.
            line_width (int): Width of the polygon lines.
        """
        if self.current_polygon_item:
            self.parent.scene.removeItem(self.current_polygon_item)
            self.current_polygon_item = None

        if not polygon_points:
            logger.warning("No polygon points to display.")
            return

        polygon = QPolygonF([QPointF(x, y) for x, y in polygon_points])
        pen = QPen(color)
        pen.setWidth(line_width)

        polygon_item = QGraphicsPolygonItem(polygon)
        polygon_item.setPen(pen)
        self.parent.scene.addItem(polygon_item)

        self.current_polygon_item = polygon_item
        self.mask = None

    def generate_mask(self, image: np.ndarray) -> np.ndarray:
        """
        Generate a mask using the SAM 2 model based on added points.

        Args:
            image (numpy.ndarray): The input image for mask generation.

        Returns:
            numpy.ndarray: Generated mask.
        """
        if not self.foreground_points:
            logger.warning("Cannot generate mask: no foreground points added")
            return None

        points = np.array(self.foreground_points + self.background_points)
        labels = np.array([1] * len(self.foreground_points) + [0] * len(self.background_points))

        self.predictor.set_image(image)
        masks, scores, _ = self.predictor.predict(
            point_coords=points, point_labels=labels, multimask_output=False
        )
        mask = masks[0]

        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        polygon = contours[0].squeeze(axis=1).tolist() if contours else []

        self.display_polygon(polygon)
        self.mask = np.array(polygon, dtype=np.float32)

        return self.mask

    def clear_temp_items(self):
        """
        Clear temporary points, lines, and polygons.
        """
        for item in self.foreground_items + self.background_items:
            self.parent.scene.removeItem(item)

        self.foreground_items.clear()
        self.background_items.clear()
        self.foreground_points.clear()
        self.background_points.clear()

        if self.current_polygon_item:
            self.parent.scene.removeItem(self.current_polygon_item)
            self.current_polygon_item = None

        self.mask = None
        logger.debug("Cleared temporary items")

    def complete_mask(self):
        """
        Save the generated mask to the database.
        """
        if self.mask is None or self.mask.shape[0] == 0:
            logger.warning("No mask to save; press E to generate one first")
            return

        if self.mask.ndim != 2 or self.mask.shape[1] != 2:
            logger.error("Invalid mask shape %s (expected Nx2); not saved", self.mask.shape)
            return
        if not self.parent.parent.sidebar.has_valid_class_selection():
            self.clear_temp_items()
            return  # Cancel saving if no valid class is selected

        image_name = self.parent.parent.state_manager.current_image_name
        class_name, selected_color = self.parent.parent.sidebar.get_selected_class_color()

        self.parent.parent.state_manager.mask_manager.save_mask(self.mask, image_name, class_name)

        self.mask_added.emit(image_name, self.mask)
        logger.info("Saved SAM2 mask (%d points) for image %s as class %r",
                    self.mask.shape[0], image_name, class_name)
        self.clear_temp_items()
