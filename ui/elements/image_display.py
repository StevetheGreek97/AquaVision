from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QImage, QPixmap, QPainter
from PyQt6.QtWidgets import  QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTableWidget
import os
import cv2
import numpy as np
from services.logger import logger, log_memory_usage
from core.tools.manual_mask import ManualMask
from core.tools.sam2_masker import SamMasker2

from core.tools.intellignent_scissors import IntelligentScissors

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

        #if self.mask_editor and self.mask_editor.is_editing:
        #    image = self.overlay_editing_masks(image)

        self._update_pixmap(image)
        
        if not preserve_zoom:
            self.resetTransform()
            self._zoom_factor = 1.0
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def overlay_masks(self, image, alpha=0.6, outline_thickness=2):
        """
        Overlay masks on the given image with transparency and ensure all masks remain visible.
        """
        overlay = image.copy()
        masks = self.parent.state_manager.mask_manager.load_masks(self.parent.state_manager.current_image_name)

        mask_layer = np.zeros_like(image, dtype=np.uint8)  

        for mask_id, mask, class_name in masks:
            print(f"🔍 Overlaying Mask - ID: {mask_id}, Class: {class_name}, Shape: {mask.shape}")

            if mask.shape[0] < 3:  
                print(f"❌ Skipping mask {mask_id} - Invalid shape {mask.shape}")
                continue  

            # Get the class color
            color = self.parent.state_manager.class_manager.get_class_color(class_name)
            color_bgr = (int(color.red()), int(color.green()), int(color.blue()))

            # Create a temporary layer for each mask
            temp_layer = np.zeros_like(image, dtype=np.uint8)

            # Fill the mask area
            cv2.fillPoly(temp_layer, [mask.astype(np.int32)], color_bgr)

            # Blend the mask into the mask layer
            mask_layer = cv2.addWeighted(mask_layer, 1.0, temp_layer, alpha, 0)  

            # Draw outlines around each mask
            cv2.polylines(mask_layer, [mask.astype(np.int32)], isClosed=True, color=(0, 0, 0), thickness=outline_thickness)

            # 🔹 Ensure Highlighted Masks Have White Borders
            if str(mask_id) in self.highlighted_mask_ids:
                print(f"🌟 Highlighting Mask {mask_id}")
                cv2.polylines(mask_layer, [mask.astype(np.int32)], isClosed=True, color=(255, 255, 255), thickness=outline_thickness + 2)

        # Blend the final mask layer with the original image
        blended_image = cv2.addWeighted(image, 1 - alpha, mask_layer, alpha, 0)

        return blended_image

 
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
        self.highlighted_mask_ids = [str(row["mask_id"]) for row in selected_rows]  # Ensure all selected IDs are stored as strings

        print(f"🔍 Selected Mask IDs for Highlighting: {self.highlighted_mask_ids}")  # Debugging

        # Redraw the image with the highlighted masks
        self.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True)

    def delete_selected_masks(self):
        """
        Delete the selected masks from the database and refresh the display.
        """
        if not self.highlighted_mask_ids:
            print("No masks selected for deletion.")
            return

        image_name = self.parent.state_manager.current_image_name
        mask_ids_to_delete = [int(mask_id) for mask_id in self.highlighted_mask_ids]  # Convert to int for DB query

        if not mask_ids_to_delete:
            print("No valid mask IDs found for deletion.")
            return

        #  Delete masks from the database
        self.parent.state_manager.mask_manager.delete_mask(image_name, mask_ids_to_delete)

        #  Clear highlighted masks after deletion
        self.highlighted_mask_ids = []

        # Reindex masks after deletion
        self.parent.state_manager.mask_manager.reindex_masks()

        # Refresh the display and results table
        self.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True)
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
            self.intelligent_scissors.clear_temp_items()
            self.intelligent_scissors = None
            print("Intelligent Scissors disabled.")
    
    def refresh_overlay(self, image_name, mask):
        """
        Refresh the image overlay when a new mask is added.
        """
        self.display_image(self.parent.state_manager.current_image_path,  preserve_zoom=True)  # Redraw the current image

    def keyPressEvent(self, event):
        """
        Handle key press events.
        """
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
                if not hasattr(self.parent, 'results_dialog') or not self.parent.results_dialog.isVisible():
                    self.parent.show_results()  # Open the table if it’s not already open

                # Set table to allow multiple selections
                self.parent.results_dialog.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)

                selected_rows = []
                for row in range(self.parent.results_dialog.table.rowCount()):
                    table_mask_id = self.parent.results_dialog.table.item(row, 1).text()
                    if table_mask_id in selected_mask_ids:
                        self.parent.results_dialog.table.selectRow(row)  # Select multiple rows
                        selected_rows.append({
                            "image_name": self.parent.results_dialog.table.item(row, 0).text(),
                            "mask_id": table_mask_id,
                            "class": self.parent.results_dialog.table.item(row, 3).text(),
                        })


                # Emit selection event to sync mask editor
                if selected_rows:
                    self.parent.results_dialog.masks_selected.emit(selected_rows)
                    #self.parent.image_display.enable_mask_editor(selected_rows) 

            #if self.mask_editor and self.mask_editor.is_editing:
            #    # Find the nearest vertex in the mask being edited
            #    self.mask_editor.dragged_vertex_index = self.mask_editor.find_nearest_vertex(point)
            #    print(f"Dragging vertex: {self.mask_editor.dragged_vertex_index}")
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

        #if self.mask_editor and self.mask_editor.is_editing and self.mask_editor.dragged_vertex_index is not None:
        #    new_position = (self.x, self.y)
        #    self.mask_editor.update_vertex(self.mask_editor.dragged_vertex_index, new_position)
        #    self.display_image(self.parent.state_manager.current_image_path,  preserve_zoom=True)  # Refresh display

        # Update the dynamic path for Intelligent Scissors
        if self.intelligent_scissors and self.intelligent_scissors.seed_points:
            self.intelligent_scissors.update_dynamic_path((self.x, self.y))
    
    def mouseReleaseEvent(self, event):
        """
        Stop panning when the middle mouse button is released.
        """
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
        #elif self.mask_editor and self.mask_editor.is_editing and event.button() == Qt.MouseButton.LeftButton:
        #    self.mask_editor.dragged_vertex_index = None
        #    self.mask_editor.save_current_mask()
        #    print("Finished dragging vertex.")
    def get_clicked_masks(self, click_point):
        """
        Identify all masks that contain the clicked point.

        Args:
            click_point (tuple): (x, y) coordinates of the click.

        Returns:
            list: A list of mask IDs that contain the clicked point.
        """
        masks = self.parent.state_manager.mask_manager.load_masks(self.parent.state_manager.current_image_name)
        clicked_masks = []

        for mask_id, mask, class_name in masks:
            # Check if the clicked point is inside the mask polygon
            if cv2.pointPolygonTest(mask.astype(np.int32), click_point, measureDist=False) >= 0:
                clicked_masks.append(str(mask_id))  # Convert ID to string for consistency

        return clicked_masks

