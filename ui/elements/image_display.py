from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QImage, QPixmap, QPainter
from PyQt6.QtWidgets import  QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
import os
import cv2
import numpy as np
from services.logger import logger, log_memory_usage
from core.tools.manual_mask import ManualMask
from core.tools.sam2_masker import SamMasker2
from core.tools.MaskEditor import MaskEditor
from core.tools.intellignent_scissors import IntelligentScissors
from core.data import DataManager
class ImageDisplay(QGraphicsView):
    """
    A QGraphicsView for displaying images with zoom and pan functionality, including zoom limits.
    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.highlighted_mask_ids = []

        # Set up the QGraphicsScene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Add a QGraphicsPixmapItem to display the image
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # Set default alignment and rendering options
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)

        # Initialize pan functionality
        self._is_panning = False
        self._pan_start = QPointF()


        self.x, self.y = None, None

        # Initialize zoom limits and factor
        self._zoom_factor = 1.0
        self._zoom_min = 1.0  # Minimum zoom level (100% of original size)
        self._zoom_max = 10.0  # Maximum zoom level (400% of original size)

        # Tools
        self.masker = None
        self.sam2_masker = None
        self.intelligent_scissors = None
        self.mask_editor = None
        

    def display_image(self, image_path, preserve_zoom=False):
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
        image = self.overlay_masks(image)

        if self.mask_editor and self.mask_editor.is_editing:
            image = self.overlay_editing_masks(image)

        self._update_pixmap(image)
        
        if not preserve_zoom:
            self.resetTransform()
            self._zoom_factor = 1.0
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def overlay_masks(self, image, alpha=0.5):
        """
        Overlay masks on the given image, highlighting selected masks.
        """
        overlay = image.copy()
        mask_files = DataManager().list_masks(self.parent.state_manager.current_image_name)

        for mask_file in mask_files:
            mask = DataManager().load_mask(mask_file)
            filename = os.path.basename(mask_file)
            parts = filename.split("||")
            mask_id = parts[1]
            class_name = parts[2].replace('.dat', '')


            # Get the color for the current mask
            color = self.parent.state_manager.class_manager.get_color_by_name(class_name)
            color_bgr = [color.red(), color.green(), color.blue()]  # Convert to RGB

            cv2.fillPoly(overlay, [mask.astype(np.int32)], color_bgr)

            # Highlight the selected masks
            if mask_id in self.highlighted_mask_ids:
                print(f"Highlighting Mask ID: {mask_id}")  # Debugging
                cv2.polylines(overlay, [mask.astype(np.int32)], isClosed=True, color=(0, 0, 0), thickness=3)

        # Blend the original image and the overlay
        blended_image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)
        return blended_image
 
    def enable_mask_editor(self, selected_rows):
        """
        Enable editing for masks selected from the table.
        """
        if not selected_rows:
            print("No masks selected for editing.")
            return

        # Initialize MaskEditor only when needed
        

        for row in selected_rows:
            mask_id = row["mask_id"]
            image_name = row['image_name']
            class_name = row['class']
            
            mask_file = f'{image_name}||{mask_id}||{class_name}.dat'

    
            if not mask_file:
                print(f"Mask {mask_id} not found.")
                continue
            mask = DataManager().load_mask(f'masks/{mask_file}')
            self.mask_editor = MaskEditor(mask, mask_id, image_name, class_name)
            

            self.mask_editor.start_editing()  # Start editing with file reference
            self.display_image(self.parent.state_manager.current_image_path)  # Refresh the display

    def disable_mask_editor(self):
        """
        Disable mask editing and clear the current editing mask.
        """
        if self.mask_editor:
            self.mask_editor.stop_editing()
            self.mask_editor = None
            print("Mask editing disabled.")
            self.display_image(self.parent.state_manager.current_image_path)  # Refresh the display

    def overlay_editing_masks(self, image):
        """
        Overlay the currently editing mask on the given image.
        """
        if not self.mask_editor or not self.mask_editor.is_editing:
            return image

        editing_mask = self.mask_editor.get_current_mask()
        if editing_mask is not None:
            overlay = image.copy()

            # Draw the mask's outline in red
            cv2.polylines(overlay, [editing_mask.astype(np.int32)], isClosed=True, color=(255, 0, 0), thickness=2)

            # Highlight the vertices of the mask in blue
            for vertex in editing_mask:
                cv2.circle(overlay, (int(vertex[0]), int(vertex[1])), radius=3, color=(0, 0, 255), thickness=-1)

            return overlay

        return image

    def fit_to_view(self):
        """
        Fit the entire image to the view.
        """
        self.resetTransform()
        self._zoom_factor = 1.0
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def _update_pixmap(self, image):
        """
        Update the displayed image in the QGraphicsPixmapItem.
        """
        h, w, ch = image.shape
        q_image = QImage(image.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.pixmap_item.setPixmap(QPixmap.fromImage(q_image))

    def set_highlighted_masks(self, selected_rows):
        """
        Set the highlighted masks based on the selected rows emitted from MaskResultsDialog.
        """
        # Extract only the Mask IDs from the selected rows
        self.highlighted_mask_ids = [row["mask_id"] for row in selected_rows]
        print(f"Selected Mask IDs: {self.highlighted_mask_ids}")  # Debugging

        # Redraw the image with the highlighted masks
        self.display_image(self.parent.state_manager.current_image_path)

    def delete_selected_masks(self):
        """
        Delete the masks currently highlighted and reindex remaining masks.
        """
        if not self.highlighted_mask_ids:
            print("No masks selected for deletion.")
            return

        mask_files = DataManager().list_masks(self.parent.state_manager.current_image_name)
        for mask_file in mask_files:
            filename = os.path.basename(mask_file)
            parts = filename.split("||")
            mask_id = parts[1]

            if mask_id in self.highlighted_mask_ids:
                print(f"Deleting Mask ID: {mask_id}")  # Debugging
                os.remove(mask_file)  # Remove the mask file
                self.highlighted_mask_ids.remove(mask_id)  # Remove from highlighted list

        # Reindex the remaining masks
        DataManager().reindex_masks(self.parent.state_manager.current_image_name)

        # Refresh the display and results dialog after deletion
        self.display_image(self.parent.state_manager.current_image_path)
        self.parent.show_results()  # Refresh the results dialog

    def enable_manual_mask(self):
        """
        Enable manual mask mode.
        """
        self.disable_intelligent_scissors()
        self.disable_sam2()
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
        self.disable_intelligent_scissors()
        self.disable_manual_mask()
        self.sam2_masker = SamMasker2(self)

        self.sam2_masker.mask_added.connect(self.refresh_overlay)  # Connect signal to refresh display

    def disable_sam2(self):
        """
        Disable manual mask mode and clear temporary lines and points.
        """
        if self.sam2_masker:
            self.sam2_masker.clear_temp_items()
            self.sam2_masker = None

    def enable_intelligent_scissors(self):
        """
        Enable Intelligent Scissors mode.
        """
        self.disable_intelligent_scissors()
        self.disable_sam2()
        if self.parent.state_manager.current_image is None:
            print("No image loaded. Please load an image first.")
            return

        self.intelligent_scissors = IntelligentScissors(self)
        self.intelligent_scissors.set_image(self.parent.state_manager.current_image)
        self.intelligent_scissors.mask_added.connect(self.refresh_overlay)
        print("Intelligent Scissors enabled hrerere.")

    def disable_intelligent_scissors(self):
        """
        Disable Intelligent Scissors mode and clear temporary data.
        """
        if self.intelligent_scissors:
            self.intelligent_scissors.clear_polygon()
            self.intelligent_scissors = None
            print("Intelligent Scissors disabled.")
    
    def refresh_overlay(self, image_name, mask):
        """
        Refresh the image overlay when a new mask is added.
        """
        self.display_image(self.parent.state_manager.current_image_path)  # Redraw the current image

    def keyPressEvent(self, event):
        """
        Handle key press events.
        """
        if event.key() == Qt.Key.Key_Plus:
            if self.mask_editor and self.mask_editor.is_editing:
                new_position = (self.x, self.y)
                print(f"Adding vertex at {new_position}")
                self.mask_editor.add_vertex(new_position)
                self.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True) 
        if event.key() == Qt.Key.Key_Minus:
            if self.mask_editor and self.mask_editor.is_editing:
                if self.mask_editor.dragged_vertex_index is not None:
                    print(f"Deleting vertex at index {self.mask_editor.dragged_vertex_index}")
                    self.mask_editor.delete_vertex(self.mask_editor.dragged_vertex_index)
                    self.mask_editor.dragged_vertex_index = None
                    self.display_image(self.parent.state_manager.current_image_path)  
        if event.key() == Qt.Key.Key_S:
            if self.masker:
                self.masker.complete_mask()
            if self.sam2_masker:
                self.sam2_masker.complete_mask()
            if self.intelligent_scissors:
                self.intelligent_scissors.complete_mask()
        if event.key() == Qt.Key.Key_E:
            if self.sam2_masker:
                a = self.sam2_masker.generate_mask(self.parent.state_manager.current_image)

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
            if self.mask_editor and self.mask_editor.is_editing:
                # Find the nearest vertex in the mask being edited
                self.mask_editor.dragged_vertex_index = self.mask_editor.find_nearest_vertex(point)
                print(f"Dragging vertex: {self.mask_editor.dragged_vertex_index}")
            if self.masker:
                self.masker.add_point(point)

            if self.sam2_masker:
                self.sam2_masker.add_point(point, 1)

            if self.intelligent_scissors:
                self.intelligent_scissors.add_seed_point(point)

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
        Update the live wire dynamically as the cursor moves.
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

        scene_pos = self.mapToScene(event.position().toPoint())
        self.x, self.y = int(scene_pos.x()), int(scene_pos.y())

        if self.mask_editor and self.mask_editor.is_editing and self.mask_editor.dragged_vertex_index is not None:
            new_position = (self.x, self.y)
            self.mask_editor.update_vertex(self.mask_editor.dragged_vertex_index, new_position)
            self.display_image(self.parent.state_manager.current_image_path,  preserve_zoom=True)  # Refresh display

        # Update the dynamic path for Intelligent Scissors
        if self.intelligent_scissors and self.intelligent_scissors.seed_points:
            self.intelligent_scissors.update_dynamic_path((self.x, self.y))
    
    def mouseReleaseEvent(self, event):
        """
        Stop panning when the middle mouse button is released.
        """
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
        elif self.mask_editor and self.mask_editor.is_editing and event.button() == Qt.MouseButton.LeftButton:
            self.mask_editor.dragged_vertex_index = None
            self.mask_editor.save_current_mask()
            print("Finished dragging vertex.")
