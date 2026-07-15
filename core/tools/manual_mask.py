import numpy as np
from PyQt6.QtGui import QPen, QColor
from PyQt6.QtWidgets import  QGraphicsEllipseItem, QGraphicsLineItem
from PyQt6.QtCore import pyqtSignal, QObject

from services.logger import get_logger

logger = get_logger(__name__)

class ManualMask(QObject):
    """
    A class for manually creating masks by drawing polygon shapes on the displayed image.
    """
    mask_added = pyqtSignal(str, np.ndarray)
    def __init__(self, parent):
        """
        Initialize the ManualMask class.

        Args:
            parent: Reference to the parent ImageDisplay instance.
        """
        super().__init__()  # Initialize QObject
        self.parent = parent
        self.active = False
        self.temp_points = []  # Points of the current polygon
        self.temp_lines = []   # Lines of the current polygon
        self.colors = []       # Colors for each mask

    def pop_last_point(self):
        """
        Remove the last point and its corresponding line from the mask.
        """
        if not self.temp_points:
            logger.debug("Undo requested with no points to remove")
            return

        # Remove the last point
        last_point = self.temp_points.pop()
        self.parent.scene.removeItem(last_point)

        # Remove the last line (if any)
        if self.temp_lines:
            last_line = self.temp_lines.pop()
            self.parent.scene.removeItem(last_line)

    def add_point(self, point):
        """
        Add a point to the current polygon.

        Args:
            point (tuple): The point to add as (x, y).
        """

        # Create and store a graphical item for the point
        pen = QPen(QColor(0, 255, 0), 2)
        ellipse = QGraphicsEllipseItem(point[0] - 2, point[1] - 2, 4, 4)
        ellipse.setPen(pen)
        ellipse.setBrush(QColor(0, 255, 0))
        self.parent.scene.addItem(ellipse)

        # Store the graphical item in the temp_points list
        self.temp_points.append(ellipse)

        # Draw a line if there are at least two points
        if len(self.temp_points) > 1:
            prev_point = self.temp_points[-2]
            line = QGraphicsLineItem(
                prev_point.rect().center().x(),
                prev_point.rect().center().y(),
                ellipse.rect().center().x(),
                ellipse.rect().center().y(),
            )
            line.setPen(QPen(QColor(255, 0, 0), 2))
            self.parent.scene.addItem(line)
            self.temp_lines.append(line)
    def complete_mask(self):
        """
        Complete the current mask and add it to the list of masks.
        """
        if len(self.temp_points) < 3:
            logger.warning("Cannot create mask: need at least 3 points, have %d",
                           len(self.temp_points))
            return np.array([])
        if not self.parent.parent.sidebar.has_valid_class_selection():
            self.clear_temp_items()
            return  # ❌ Cancel saving if no valid class is selected

        # Close the polygon by connecting the last point to the first
        last_point = self.temp_points[-1].rect().center()
        first_point = self.temp_points[0].rect().center()
        line = QGraphicsLineItem(last_point.x(), last_point.y(), first_point.x(), first_point.y())
        line.setPen(QPen(QColor(255, 0, 0), 2))
        self.parent.scene.addItem(line)
        self.temp_lines.append(line)

        # Create the mask polygon
        mask_polygon = np.array(
            [(int(item.rect().center().x()), int(item.rect().center().y())) for item in self.temp_points],
            dtype=np.float32
        )
        image_name = self.parent.parent.state_manager.current_image_name
        class_name, selected_color = self.parent.parent.sidebar.get_selected_class_color()
        self.parent.parent.state_manager.mask_manager.save_mask(mask_polygon, image_name, class_name)
        logger.info("Saved manual mask (%d points) for image %s as class %r",
                    mask_polygon.shape[0], image_name, class_name)
        # Emit the signal
        self.mask_added.emit(image_name, mask_polygon)
        # Clear temporary items
        self.clear_temp_items()


        # Clear temporary items
        return 
    def clear_temp_items(self):
        """
        Clear temporary points and lines.
        """
        for item in self.temp_lines:
            self.parent.scene.removeItem(item)
        for item in self.temp_points:
            self.parent.scene.removeItem(item)
        self.temp_lines.clear()
        self.temp_points.clear()
        logger.debug("Cleared temporary items")
