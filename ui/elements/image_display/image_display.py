from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QPainter
from PyQt6.QtWidgets import QTableWidget
from core.tools.manual_mask import ManualMask
from core.tools.sam2_masker import SamMasker2
from core.tools.sam2_boxmasker import SamBoxMasker
from core.tools.dextr_mask import DEXTRMasker
from core.tools.intellignent_scissors import IntelligentScissors
import cv2
import numpy as np

from PyQt6.QtWidgets import QApplication

from PyQt6.QtWidgets import QGraphicsView



class ImageDisplay(QGraphicsView):
    """
    A QGraphicsView for displaying images and masks with zoom and pan functionality.
    No control or interaction logic here.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.x, self.y = None, None
        self._zoom_factor = 1.0
        self._zoom_min = 1.0
        self._zoom_max = 10.0
        self._is_panning = False

        self.highlighted_mask_ids = []

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)


    def display_image(self, image_path, preserve_zoom=False):
        """
        Load and display the image along with overlays.
        """
        if not image_path:
            print("No image path provided.")
            return

        import cv2

        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image: {image_path}")
            return

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.parent.state_manager.current_image = image

        image = self.overlay_masks(image)
        self._update_pixmap(image)

        if not preserve_zoom:
            self.resetTransform()
            self._zoom_factor = 1.0
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)


    def overlay_masks(self, image, alpha=0.4, outline_thickness=1):
        """
        Overlay all masks onto the image with transparency and optional outlines.
        """
        import numpy as np
        import cv2

        output = image.copy()
        masks = self.parent.state_manager.mask_manager.load_masks(
            self.parent.state_manager.current_image_name
        )

        for mask_id, mask, class_name in masks:
            if mask.shape[0] < 3:
                continue

            color = self.parent.state_manager.class_manager.get_class_color(class_name)
            color_bgr = (int(color.red()), int(color.green()), int(color.blue()))

            binary_mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.fillPoly(binary_mask, [mask.astype(np.int32)], 1)

            overlay_mask = np.full(image.shape, color_bgr, dtype=np.uint8)
            indices = binary_mask.astype(bool)
            output[indices] = cv2.addWeighted(image[indices], 1 - alpha, overlay_mask[indices], alpha, 0)

            cv2.polylines(output, [mask.astype(np.int32)], isClosed=True, color=(0, 0, 0), thickness=outline_thickness)

            if str(mask_id) in self.highlighted_mask_ids:
                cv2.polylines(output, [mask.astype(np.int32)], isClosed=True, color=(255, 255, 255), thickness=outline_thickness + 2)

        return output

    def _update_pixmap(self, image):
        """
        Update the displayed pixmap with a new image.
        """
        h, w, ch = image.shape
        q_image = QImage(image.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.pixmap_item.setPixmap(QPixmap.fromImage(q_image))

    def fit_to_view(self):
        """
        Fit the image to the view.
        """
        self.resetTransform()
        self._zoom_factor = 1.0
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def refresh_overlay(self, image_name, mask):
        """
        Refresh the overlay (e.g., after mask editing).
        """
        self.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True)

    def set_highlighted_masks(self, selected_rows):
        """
        Highlight selected masks in the overlay.
        """
        self.highlighted_mask_ids = [str(row["mask_id"]) for row in selected_rows]
        self.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True)

    def delete_selected_masks(self):
        """
        Delete selected masks and refresh view.
        """
        if not self.highlighted_mask_ids:
            print("No masks selected for deletion.")
            return

        mask_ids_to_delete = [int(mask_id) for mask_id in self.highlighted_mask_ids]

        self.parent.state_manager.mask_manager.delete_mask(
            self.parent.state_manager.current_image_name,
            mask_ids_to_delete
        )

        self.highlighted_mask_ids = []
        self.parent.state_manager.mask_manager.reindex_masks()

        self.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True)
        self.parent.show_results()
    def wheelEvent(self, event):
        zoom_in_factor = 1.15  # this factor was from your original refactored version
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

        # Update zoom factor (keeping within limits)
        self._zoom_factor = max(self._zoom_min, min(self._zoom_max, self._zoom_factor * zoom_factor))

        event.accept()

    def keyPressEvent(self, event):
        """
        Handle key press events.
        """
        if event.key() == Qt.Key.Key_S:
            if self.parent.tool_manager.current_tool:
                self.parent.tool_manager.current_tool.complete_mask()
                # ✅ After saving the mask, update the Annotations table
                if hasattr(self.parent, 'annotations') and self.parent.annotations.isVisible():
                    self.parent.annotations.refresh_table(self.parent.state_manager.current_image_path)

                # ✅ After saving the mask, update the Statistics plot
                if hasattr(self.parent, 'statistics') and self.parent.statistics.isVisible():
                    self.parent.statistics.refresh_plot()

        if event.key() == Qt.Key.Key_E:
            if isinstance(self.parent.tool_manager.current_tool, SamMasker2):
                a = self.parent.tool_manager.current_tool.generate_mask(self.parent.state_manager.current_image)
            if isinstance(self.parent.tool_manager.current_tool, SamBoxMasker):
                a = self.parent.tool_manager.current_tool.generate_mask(self.parent.state_manager.current_image)
            if isinstance(self.parent.tool_manager.current_tool, DEXTRMasker):
                a = self.parent.tool_manager.current_tool.generate_mask(self.parent.state_manager.current_image)


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
            scene_pos = self.mapToScene(event.position().toPoint())
            point = (int(scene_pos.x()), int(scene_pos.y()))
            # Get all masks that contain the clicked point
            selected_mask_ids = self.get_clicked_masks(point)

            # Get all masks that contain the clicked point
            selected_mask_ids = self.get_clicked_masks(point)

            if selected_mask_ids:
                print(f"Clicked on masks: {selected_mask_ids}")  # Debugging output

                # Ensure all masks are highlighted
                for mask_id in selected_mask_ids:
                    if mask_id not in self.highlighted_mask_ids:
                        self.highlighted_mask_ids.append(mask_id)  # Add if not already selected

                # Refresh display with the selected masks highlighted
                self.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True)

                # Ensure results dialog is open before interacting with the table
                if not hasattr(self.parent, 'annotations') or not self.parent.annotations.isVisible():
                    self.parent.show_results()                    
                self.parent.annotations.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)


                selected_rows = []
                for row in range(self.parent.annotations.table.rowCount()):
                    table_mask_id = self.parent.annotations.table.item(row, 1).text()
                    if table_mask_id in selected_mask_ids:
                        self.parent.annotations.table.selectRow(row)  # Select multiple rows
                        selected_rows.append({
                            "image_name": self.parent.annotations.table.item(row, 0).text(),
                            "mask_id": table_mask_id,
                            "class": self.parent.annotations.table.item(row, 3).text(),
                        })


                # Emit selection event to sync mask editor
                if selected_rows:
                    self.parent.annotations.masks_selected.emit(selected_rows)

            if isinstance(self.parent.tool_manager.current_tool, ManualMask):
                self.parent.tool_manager.current_tool.add_point(point)

            if isinstance(self.parent.tool_manager.current_tool, DEXTRMasker):
                self.parent.tool_manager.current_tool.add_point(point)

            if isinstance(self.parent.tool_manager.current_tool, SamMasker2):
                self.parent.tool_manager.current_tool.add_point(point, 1)

            if isinstance(self.parent.tool_manager.current_tool, IntelligentScissors):
                self.parent.tool_manager.current_tool.add_seed_point(point)

            if isinstance(self.parent.tool_manager.current_tool, SamBoxMasker):
                self.parent.tool_manager.current_tool.box_start = point  
                self.parent.tool_manager.current_tool.is_drawing_box = True 
                print(f"📏 Started Box at {point}")

        elif event.button() == Qt.MouseButton.RightButton:
            if isinstance(self.parent.tool_manager.current_tool, ManualMask):
                self.parent.tool_manager.current_tool.pop_last_point()

            if isinstance(self.parent.tool_manager.current_tool, SamMasker2):
                scene_pos = self.mapToScene(event.position().toPoint())
                point = (int(scene_pos.x()), int(scene_pos.y()))


                self.parent.tool_manager.current_tool.add_point(point, 0)

        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)
        scene_pos = self.mapToScene(event.position().toPoint())
        point = (int(scene_pos.x()), int(scene_pos.y()))


        self.x, self.y = int(scene_pos.x()), int(scene_pos.y())

        tool = self.parent.tool_manager.current_tool
        if isinstance(tool, IntelligentScissors):
            if tool.seed_points:
                tool.update_dynamic_path((self.x, self.y))

        if isinstance(tool, SamBoxMasker):
            if tool.is_drawing_box:
                tool.update_box_preview(tool.box_start, point)
                print(f"📏 Updating Box: {tool.box_start} → {point}")

    def mouseReleaseEvent(self, event):
        """
        Stop panning when the middle mouse button is released.
        """
        scene_pos = self.mapToScene(event.position().toPoint())
        point = (int(scene_pos.x()), int(scene_pos.y()))

        if event.button() == Qt.MouseButton.LeftButton:
             if isinstance(self.parent.tool_manager.current_tool, SamBoxMasker):
                if self.parent.tool_manager.current_tool.is_drawing_box:
                    self.parent.tool_manager.current_tool.add_box(self.parent.tool_manager.current_tool.box_start, point)
                    print(f"✅ Finalized Box: {self.parent.tool_manager.current_tool.box}")
                    self.parent.tool_manager.current_tool.is_drawing_box = False  # ✅ Reset drawing flag


        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    def get_clicked_masks(self, click_point):
        """
        Identify all masks that contain the clicked point.

        Args:
            click_point (tuple): (x, y) coordinates of the click.

        Returns:
            list: A list of mask IDs that contain the clicked point.
        """
        masks = self.parent.state_manager.mask_manager.load_masks(
            self.parent.state_manager.current_image_name
        )
        clicked_masks = []

        for mask_id, mask, class_name in masks:
            # Check if the clicked point is inside the mask polygon
            if cv2.pointPolygonTest(mask.astype(np.int32), click_point, measureDist=False) >= 0:
                clicked_masks.append(str(mask_id))  # Convert ID to string for consistency

        return clicked_masks