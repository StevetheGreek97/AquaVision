from PyQt6.QtCore import QObject, Qt, QPointF
from PyQt6.QtWidgets import QTableWidget
from core.tools.manual_mask import ManualMask
from core.tools.sam2_masker import SamMasker2
from core.tools.sam2_boxmasker import SamBoxMasker
from core.tools.dextr_mask import DEXTRMasker
from core.tools.intellignent_scissors import IntelligentScissors
import cv2
import numpy as np

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtGui import QMouseEvent
class ImageController(QObject):
    """
    Handles all keyboard and mouse interactions with the ImageDisplay.
    """

    def __init__(self, image_display):
        super().__init__(image_display)
        self.image_display = image_display
        self.parent = image_display.parent
        self._is_panning = False
        self._pan_start = QPointF()
        self.x, self.y = None, None
        self._zoom_factor = 1.0
        self._zoom_min = 1.0
        self._zoom_max = 10.0

    def eventFilter(self, watched, event):
        if watched is self.image_display:
            if event.type() == QEvent.Type.KeyPress:
                return self.handle_key_press(event)

            elif event.type() == QEvent.Type.MouseButtonPress:
                self.handle_mouse_press(event)
                return False  # allow further processing

            elif event.type() == QEvent.Type.MouseMove:
                self.handle_mouse_move(event)
                return False  # important to allow further processing for continuous updates

            elif event.type() == QEvent.Type.MouseButtonRelease:
                self.handle_mouse_release(event)
                return False  # allow further processing
        return False  # ensure default handling if not specifically intercepted


    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_S:
            if self.parent.tool_manager.current_tool:
                self.parent.tool_manager.current_tool.complete_mask()
                # ✅ After saving the mask, update the Annotations table
            if hasattr(self.parent, 'annotations') and self.parent.annotations.isVisible():
                self.parent.annotations.refresh_table(self.parent.state_manager.current_image_path)

            # ✅ After saving the mask, update the Statistics plot
            if hasattr(self.parent, 'statistics') and self.parent.statistics.isVisible():
                self.parent.statistics.refresh_plot()

            
            return True

        if event.key() == Qt.Key.Key_E:
            if isinstance(self.parent.tool_manager.current_tool, (SamMasker2, SamBoxMasker, DEXTRMasker)):
                self.parent.tool_manager.current_tool.generate_mask(self.parent.state_manager.current_image)
            return True

        return False

    def handle_mouse_press(self, event):
        scene_pos = self.image_display.mapToScene(event.position().toPoint())
        point = (int(scene_pos.x()), int(scene_pos.y()))

        if event.button() == Qt.MouseButton.LeftButton:
            selected_mask_ids = self.get_clicked_masks(point)
            if selected_mask_ids:
                for mask_id in selected_mask_ids:
                    if mask_id not in self.image_display.highlighted_mask_ids:
                        self.image_display.highlighted_mask_ids.append(mask_id)
                self.image_display.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True)

                if not hasattr(self.parent, 'annotations') or not self.parent.annotations.isVisible():
                    self.parent.show_results()                    
                self.parent.annotations.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)

                selected_rows = []
                for row in range(self.parent.annotations.table.rowCount()):
                    table_mask_id = self.parent.annotations.table.item(row, 1).text()
                    if table_mask_id in selected_mask_ids:
                        self.parent.annotations.table.selectRow(row)
                        selected_rows.append({
                            "image_name": self.parent.annotations.table.item(row, 0).text(),
                            "mask_id": table_mask_id,
                            "class": self.parent.annotations.table.item(row, 3).text(),
                        })

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

        elif event.button() == Qt.MouseButton.RightButton:
            if isinstance(self.parent.tool_manager.current_tool, ManualMask):
                self.parent.tool_manager.current_tool.pop_last_point()
            if isinstance(self.parent.tool_manager.current_tool, SamMasker2):
                self.parent.tool_manager.current_tool.add_point(point, 0)

        elif event.button() == Qt.MouseButton.MiddleButton:
            
            self.image_display.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            fake_event = QMouseEvent(
                QEvent.Type.MouseButtonPress,
                event.position(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            QApplication.sendEvent(self.image_display.viewport(), fake_event)
            return True
        return False

    def handle_mouse_move(self, event):
        scene_pos = self.image_display.mapToScene(event.position().toPoint())
        point = (int(scene_pos.x()), int(scene_pos.y()))
        self.x, self.y = point

        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.image_display.horizontalScrollBar().setValue(
                self.image_display.horizontalScrollBar().value() - int(delta.x())
            )
            self.image_display.verticalScrollBar().setValue(
                self.image_display.verticalScrollBar().value() - int(delta.y())
            )

        if isinstance(self.parent.tool_manager.current_tool, IntelligentScissors):
            if self.parent.tool_manager.current_tool.seed_points:
                self.parent.tool_manager.current_tool.update_dynamic_path(point)

        if isinstance(self.parent.tool_manager.current_tool, SamBoxMasker):
            if self.parent.tool_manager.current_tool.is_drawing_box:
                self.parent.tool_manager.current_tool.update_box_preview(
                    self.parent.tool_manager.current_tool.box_start,
                    point
                )
                print(f"📏 Updating Box Preview: {self.parent.tool_manager.current_tool.box_start} → {point}")

        return True


    def handle_mouse_release(self, event):
        scene_pos = self.image_display.mapToScene(event.position().toPoint())
        point = (int(scene_pos.x()), int(scene_pos.y()))

        if event.button() == Qt.MouseButton.LeftButton:
            if isinstance(self.parent.tool_manager.current_tool, SamBoxMasker):
                if self.parent.tool_manager.current_tool.is_drawing_box:
                    self.parent.tool_manager.current_tool.add_box(
                        self.parent.tool_manager.current_tool.box_start,
                        point
                    )
                    self.parent.tool_manager.current_tool.is_drawing_box = False

        if event.button() == Qt.MouseButton.MiddleButton:
            fake_event = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            event.position(),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
            )
            QApplication.sendEvent(self.image_display.viewport(), fake_event)
            self.image_display.setDragMode(QGraphicsView.DragMode.NoDrag)
            return True
        return False

    def get_clicked_masks(self, click_point):
        masks = self.parent.state_manager.mask_manager.load_masks(self.parent.state_manager.current_image_name)
        clicked_masks = []
        for mask_id, mask, class_name in masks:
            if mask is not None and mask.shape[0] >= 3:
                if cv2.pointPolygonTest(mask.astype(np.int32), click_point, measureDist=False) >= 0:
                    clicked_masks.append(str(mask_id))
        return clicked_masks











