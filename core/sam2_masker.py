import numpy as np
from core.data import DataManager
from PyQt6.QtGui import QPen, QColor, QPolygonF
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPolygonItem
from PyQt6.QtCore import pyqtSignal, QObject, QPointF
from sam2.sam2_image_predictor import SAM2ImagePredictor
from sam2.build_sam import build_sam2
import torch
import cv2


class SamMasker2(QObject):
    """
    A class for creating masks interactively using the SAM 2 model.
    """
    mask_added = pyqtSignal(str, np.ndarray)  # Signal emitted when a mask is added

    def __init__(self, parent, device='cpu'):
        """
        Initialize the Sam2 class.

        Args:
            parent: Reference to the parent ImageDisplay instance.
            device (str): Device to run the model on ('cpu' or 'cuda').
        """
        super().__init__()
        self.parent = parent
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')

        # Load the SAM 2 model and predictor
        sam2_model = build_sam2("sam2_hiera_l.yaml", 'sam2_configs/sam2_hiera_large.pt', device=self.device)
        self.predictor = SAM2ImagePredictor(sam2_model)

        self.foreground_points = []
        self.background_points = []
        self.foreground_items = []
        self.background_items = []

        self.current_polygon_item = None  # Reference to the currently displayed polygon

    def add_point(self, point, label):
        """
        Add a point to the appropriate list (foreground or background).

        Args:
            point (tuple): The point to add as (x, y).
            label (int): The label for the point (1 for foreground, 0 for background).
        """
        pen = QPen(QColor(0, 255, 0) if label == 1 else QColor(255, 0, 0), 2)
        ellipse = QGraphicsEllipseItem(point[0] - 2, point[1] - 2, 4, 4)
        ellipse.setPen(pen)
        ellipse.setBrush(QColor(0, 255, 0) if label == 1 else QColor(255, 0, 0))
        self.parent.scene.addItem(ellipse)

        if label == 1:
            self.foreground_points.append(point)
            self.foreground_items.append(ellipse)  # Track the QGraphicsItem
        else:
            self.background_points.append(point)
            self.background_items.append(ellipse)  # Track the QGraphicsItem

        print(f"Added point: {point}, Label: {label}")

    def display_polygon(self, polygon_points, color=QColor(0, 255, 0), line_width=2):
        """
        Display a polygon on the scene using the provided points.

        Args:
            polygon_points (list): List of (x, y) tuples representing the polygon vertices.
            color (QColor): Color of the polygon outline.
            line_width (int): Width of the polygon lines.
        """
        # Remove the previous polygon if it exists
        if self.current_polygon_item:
            self.parent.scene.removeItem(self.current_polygon_item)
            self.current_polygon_item = None

        if not polygon_points:
            print("No polygon points to display.")
            return

        # Create a QPolygonF from the points
        polygon = QPolygonF([QPointF(x, y) for x, y in polygon_points])

        # Create a QGraphicsPolygonItem and set its pen
        pen = QPen(color)
        pen.setWidth(line_width)
        polygon_item = QGraphicsPolygonItem(polygon)
        polygon_item.setPen(pen)

        # Add the polygon to the scene via the parent
        self.parent.scene.addItem(polygon_item)

        # Store the polygon item for future updates
        self.current_polygon_item = polygon_item
        self.mask = None

    def generate_mask(self, image):
        """
        Generate a mask using the SAM 2 model based on added points.

        Args:
            image (numpy.ndarray): The input image for mask generation.

        Returns:
            numpy.ndarray: Generated mask.
        """
        if not self.foreground_points:
            raise ValueError("No foreground points added for mask generation.")

        # Prepare input points and labels
        points = np.array(self.foreground_points + self.background_points)
        labels = np.array([1] * len(self.foreground_points) + [0] * len(self.background_points))

        # Set the image and predict the mask
        self.predictor.set_image(image)
        masks, scores, _ = self.predictor.predict(
            point_coords=points,
            point_labels=labels,
            multimask_output=False
        )
        mask = masks[0]

        # Find contours in the mask
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Convert contours to a list of (x, y) coordinates
        if contours:
            polygon = contours[0].squeeze(axis=1).tolist()
        else:
            polygon = []

        # Display the polygon
        self.display_polygon(polygon)

        self.mask = np.array(polygon)
    def clear_temp_items(self):
        """
        Clear temporary points and lines.
        """
        for item in self.foreground_items:
            self.parent.scene.removeItem(item)
        for item in self.background_items:
            self.parent.scene.removeItem(item)

        # Clear the tracked items and points
        self.foreground_items = []
        self.background_items = []
        self.foreground_points = []
        self.background_points = []

        # Remove the polygon if it exists
        if self.current_polygon_item:
            self.parent.scene.removeItem(self.current_polygon_item)
            self.current_polygon_item = None

        self.mask = None
        print("Temporary items cleared.")


    def complete_mask(self):
        """
        Save the mask to a file.

        Args:
            mask (numpy.ndarray): The mask to save.
            file_path (str): Path to save the mask.
        """
        
        DataManager().save_mask(self.mask, self.parent.parent.state_manager.current_image_name)
        self.mask_added.emit(self.parent.parent.state_manager.current_image_name, self.mask)
        self.clear_temp_items()
        print(f"Mask saved")
