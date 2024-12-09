from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QPolygonF
from PyQt6.QtWidgets import QGraphicsPolygonItem, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem
import glob
import cv2
import numpy as np
from services.logger import logger, log_memory_usage
from core.manual_mask import ManualMask
from core.sam_masker import SamMasker
import os


class ImageDisplay(QGraphicsView):
    """
    A QGraphicsView for displaying images with zoom and pan functionality, including zoom limits.
    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        # Set up the QGraphicsScene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Add a QGraphicsPixmapItem to display the image
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # Set default alignment and rendering options
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing)

        # Initialize pan functionality
        self._is_panning = False
        self._pan_start = QPointF()

        # Initialize zoom limits and factor
        self._zoom_factor = 1.0
        self._zoom_min = 1.0  # Minimum zoom level (100% of original size)
        self._zoom_max = 10.0  # Maximum zoom level (400% of original size)

        # Manual mask mode
        self.masker = None

        self.sam2_masker = None


    def display_image(self, image_path):
        """
        Load an image from the given path, overlay its masks, and display it.
        """
        if not image_path:
            print("No image path provided to display.")
            return
        
        # Read the image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image: {image_path}")
            return
        
        # Convert the image to RGB format
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.parent.state_manager.current_image = image  # Update state with current image

        # Retrieve the masks and overlay them
        image = self.overlay_masks1(image)

        # Convert the image to QImage
        height, width, channels = image.shape
        bytes_per_line = channels * width
        q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

        # Set the pixmap in the QGraphicsPixmapItem
        pixmap = QPixmap.fromImage(q_image)
        self.pixmap_item.setPixmap(pixmap)
        self.resetTransform()
        self._zoom_factor = 1.0
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def overlay_masks1(self, image, alpha=0.5):
        """
        Overlay masks on the given image and return the blended image.
        """
        overlay = image.copy()

        for mask in self.parent.state_manager.current_masks:
            color = [int(c) for c in np.random.randint(0, 256, size=3)]  # Random color
            cv2.fillPoly(overlay, [mask.astype(np.int32)], color)  # Draw the mask on the overlay image

        # Blend the original image and the overlay
        blended_image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)
        return blended_image

    def enable_manual_mask(self):
        """
        Enable manual mask mode.
        """
        self.masker = ManualMask(self)
        self.masker.mask_added.connect(self.refresh_overlay)  # Connect signal to refresh display

    def disable_manual_mask(self):
        """
        Disable manual mask mode and clear temporary lines and points.
        """
        if self.masker:
            self.masker.clear_temp_items()
            self.masker = None

    def enable_sam2(self):
        """
        Enable manual mask mode.
        """
        self.sam2_masker = SamMasker(self)

        self.sam2_masker.mask_added.connect(self.refresh_overlay)  # Connect signal to refresh display

    def disable_sam2(self):
        """
        Disable manual mask mode and clear temporary lines and points.
        """
        if self.sam2_masker:
            self.sam2_masker.clear_temp_items()
            self.sam2_masker = None

    def refresh_overlay(self, image_name, mask):
        """
        Refresh the image overlay when a new mask is added.
        """
        self.display_image(self.parent.state_manager.current_image_path)  # Redraw the current image

    def keyPressEvent(self, event):
        """
        Handle key press events.
        """
        if event.key() == Qt.Key.Key_S:
            if self.masker:
                self.masker.complete_mask()
            if self.sam2_masker:
                self.sam2_masker.complete_mask()
        if event.key() == Qt.Key.Key_E:
            if self.sam2_masker:
                a = self.sam2_masker.generate_mask(self.parent.state_manager.current_image)



    def fit_to_view(self):
        """
        Fit the entire image to the view.
        """
        self.resetTransform()
        self._zoom_factor = 1.0
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        """
        Zoom in or out using the mouse wheel, with zoom limits.
        """
        zoom_step = 1.1  # Scale factor for zooming
        if event.angleDelta().y() > 0:
            # Zoom in
            if self._zoom_factor < self._zoom_max:
                self.scale(zoom_step, zoom_step)
                self._zoom_factor *= zoom_step
        else:
            # Zoom out
            if self._zoom_factor > self._zoom_min:
                zoom_step = 1 / zoom_step
                self.scale(zoom_step, zoom_step)
                self._zoom_factor *= zoom_step


    def mousePressEvent(self, event):
        """
        Handle mouse presses for scissors and panning.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            if self.masker:
                scene_pos = self.mapToScene(event.position().toPoint())
                point = (int(scene_pos.x()), int(scene_pos.y()))

                self.masker.add_point(point)
                #print(self.masker.temp_points)
            if self.sam2_masker:
                scene_pos = self.mapToScene(event.position().toPoint())
                point = (int(scene_pos.x()), int(scene_pos.y()))

                self.sam2_masker.add_point(point, 1)
            

        elif event.button() == Qt.MouseButton.RightButton:
            if self.masker:
                self.masker.pop_last_point()

            if self.sam2_masker:
                scene_pos = self.mapToScene(event.position().toPoint())
                point = (int(scene_pos.x()), int(scene_pos.y()))


                self.sam2_masker.add_point(point, 0)

        elif event.button() == Qt.MouseButton.MiddleButton:
            # Start panning
            self._is_panning = True
            self._pan_start = event.position()


    def mouseMoveEvent(self, event):
        """
        Pan the view when the mouse is moved with the middle button pressed.
        """
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )

    def mouseReleaseEvent(self, event):
        """
        Stop panning when the middle mouse button is released.
        """
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False

