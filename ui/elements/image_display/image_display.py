from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTableWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from core.tools.manual_mask import ManualMask
from core.tools.sam2_masker import SamMasker2
from core.tools.sam2_boxmasker import SamBoxMasker
from core.tools.dextr_mask import DEXTRMasker
from core.tools.intellignent_scissors import IntelligentScissors
import cv2
import numpy as np
import time

from PyQt6.QtWidgets import QApplication


class ImageDisplay(QGraphicsView):
    """
    QGraphicsView that shows the base image+filled masks as one pixmap, and a separate
    transparent ARGB overlay pixmap for highlights. This avoids re-uploading the full image
    when highlights change.
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

        # Scene + items
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Base image item
        self.pixmap_item = QGraphicsPixmapItem()
        self.pixmap_item.setZValue(0)
        self.scene.addItem(self.pixmap_item)

        # Highlight overlay item (transparent ARGB)
        self.highlight_item = QGraphicsPixmapItem()
        self.highlight_item.setZValue(10)
        self.scene.addItem(self.highlight_item)

        # View settings
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)

        # Cached data
        self.cached_image_with_masks = None
        self._hl_img = None                 # QImage (ARGB32 premult)
        self._mask_index = {}               # str(mask_id) -> np.ndarray(int32) polygon

    # ---------- Public API ----------

    def display_image(self, image_path, preserve_zoom=False):
        """
        Load and display the image; render filled masks once to base pixmap.
        Prepare a transparent overlay for fast highlights.
        """
        if not image_path:
            print("No image path provided.")
            return

        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image: {image_path}")
            return

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.parent.state_manager.current_image = image

        # Build polygon index for this image so highlights don't call load_masks every time
        self._rebuild_mask_index()

        # Render base once
        t0 = time.perf_counter()
        self.cached_image_with_masks = self.overlay_base_masks(image)
        self._set_base_pixmap(self.cached_image_with_masks)
        t1 = time.perf_counter()

        # Prepare transparent overlay same size as image
        h, w = image.shape[:2]
        self._hl_img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        self._hl_img.fill(0)  # fully transparent
        self.highlight_item.setPixmap(QPixmap.fromImage(self._hl_img))
        t2 = time.perf_counter()

        # Fit view
        if not preserve_zoom:
            self.resetTransform()
            self._zoom_factor = 1.0
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

        print(f"[display_image] base_render={(t1-t0)*1000:.2f} ms, overlay_init={(t2-t1)*1000:.2f} ms")

    def overlay_base_masks(self, image, alpha=0.4, outline_thickness=1):
        """
        Faster base overlay: blend per class once, then draw outlines. (Your already-optimized version can live here.)
        """
        output = image.copy()
        masks = self.parent.state_manager.mask_manager.load_masks(
            self.parent.state_manager.current_image_name
        )

        # group by class for single blends
        from collections import defaultdict
        class_to_polys = defaultdict(list)
        for _, mask, class_name, _ in masks:
            if mask.shape[0] >= 3:
                class_to_polys[class_name].append(mask.astype(np.int32))

        H, W = image.shape[:2]
        for class_name, polys in class_to_polys.items():
            if not polys:
                continue
            # rasterize all polygons of the class
            class_mask = np.zeros((H, W), dtype=np.uint8)
            cv2.fillPoly(class_mask, polys, 255)

            nz = cv2.findNonZero(class_mask)
            if nz is None:
                continue
            x, y, w, h = cv2.boundingRect(nz)
            roi_out = output[y:y+h, x:x+w]
            roi_mask = class_mask[y:y+h, x:x+w]

            color = self.parent.state_manager.class_manager.get_class_color(class_name)
            color_rgb = (int(color.red()), int(color.green()), int(color.blue()))
            roi_color = np.empty_like(roi_out); roi_color[:] = color_rgb

            blended = cv2.addWeighted(roi_out, 1.0 - alpha, roi_color, alpha, 0.0)
            cv2.copyTo(blended, roi_mask, roi_out)

            cv2.polylines(output, polys, isClosed=True, color=(0, 0, 0), thickness=outline_thickness)

        return output

    def highlight_selected_masks(self, mask_ids):
        """
        Draw white outlines on a transparent overlay (no base redraw).
        """
        if self._hl_img is None:
            return

        t0 = time.perf_counter()
        self._hl_img.fill(0)  # clear overlay
        t_clear = time.perf_counter()

        painter = QPainter(self._hl_img)
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)

        drawn = 0
        for mid in mask_ids:
            poly = self._mask_index.get(str(mid))
            if poly is None or poly.shape[0] < 3:
                continue
            # Convert to QPoint list
            from PyQt6.QtCore import QPoint
            pts = [QPoint(int(x), int(y)) for x, y in poly]
            painter.drawPolyline(*pts)
            painter.drawLine(pts[-1], pts[0])  # close shape
            drawn += 1

        painter.end()
        t_paint = time.perf_counter()

        # Upload ONLY overlay (tiny)
        self.highlight_item.setPixmap(QPixmap.fromImage(self._hl_img))
        t_upload = time.perf_counter()

        print(f"[highlight_overlay] clear={(t_clear-t0)*1000:.2f} ms, "
              f"paint={(t_paint-t_clear)*1000:.2f} ms ({drawn} polys), "
              f"upload={(t_upload-t_paint)*1000:.2f} ms, "
              f"total={(t_upload-t0)*1000:.2f} ms")

    def set_highlighted_masks(self, selected_rows):
        """
        Sync table selection -> overlay highlights (no base upload).
        """
        annotations = getattr(self.parent, "annotations", None)
        if annotations is None or not hasattr(annotations, "table"):
            return

        selected_ids = []
        for item in annotations.table.selectedItems():
            if item and item.column() == 1:
                selected_ids.append(item.text())

        self.highlighted_mask_ids = selected_ids
        self.highlight_selected_masks(self.highlighted_mask_ids)

    def fit_to_view(self):
        self.resetTransform()
        self._zoom_factor = 1.0
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def refresh_overlay(self, image_name, mask):
        self.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True)

    def refresh_masks(self):
        """
        Re-render base overlay and keep highlights; overlay is redrawn after base upload.
        """
        if self.parent.state_manager.current_image is None:
            return

        self.cached_image_with_masks = self.overlay_base_masks(self.parent.state_manager.current_image)
        self._set_base_pixmap(self.cached_image_with_masks)

        if self.highlighted_mask_ids:
            self.highlight_selected_masks(self.highlighted_mask_ids)

    def delete_selected_masks(self):
        if not self.highlighted_mask_ids:
            print("No masks selected for deletion.")
            return

        mask_ids_to_delete = [int(mask_id) for mask_id in self.highlighted_mask_ids]
        self.parent.state_manager.mask_manager.delete_mask(
            self.parent.state_manager.current_image_name,
            mask_ids_to_delete
        )
        self.parent.annotations.table.clearSelection()
        self.highlighted_mask_ids = []
        self.refresh_masks()

    # ---------- Events ----------

    def wheelEvent(self, event):
        zoom_step = 1.1
        if event.angleDelta().y() > 0:
            if self._zoom_factor < self._zoom_max:
                self.scale(zoom_step, zoom_step)
                self._zoom_factor *= zoom_step
        else:
            if self._zoom_factor > self._zoom_min:
                inv = 1 / zoom_step
                self.scale(inv, inv)
                self._zoom_factor *= inv

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_S:
            if self.parent.tool_manager.current_tool:
                self.parent.tool_manager.current_tool.complete_mask()
                if hasattr(self.parent, 'annotations') and self.parent.annotations.isVisible():
                    self.parent.annotations.refresh_table(self.parent.state_manager.current_image_path)
                if hasattr(self.parent, 'statistics') and self.parent.statistics.isVisible():
                    self.parent.statistics.refresh_plot()

        if event.key() == Qt.Key.Key_E:
            tool = self.parent.tool_manager.current_tool
            if isinstance(tool, (SamMasker2, SamBoxMasker, DEXTRMasker)):
                tool.generate_mask(self.parent.state_manager.current_image)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            point = (int(scene_pos.x()), int(scene_pos.y()))
            selected_mask_ids = self.get_clicked_masks(point)

            if selected_mask_ids:
                for mask_id in selected_mask_ids:
                    if mask_id not in self.highlighted_mask_ids:
                        self.highlighted_mask_ids.append(mask_id)
                self.highlight_selected_masks(self.highlighted_mask_ids)

                # Ensure results dialog is open
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

            tool = self.parent.tool_manager.current_tool
            if isinstance(tool, ManualMask):
                tool.add_point(point)
            elif isinstance(tool, DEXTRMasker):
                tool.add_point(point)
            elif isinstance(tool, SamMasker2):
                tool.add_point(point, 1)
            elif isinstance(tool, IntelligentScissors):
                tool.add_seed_point(point)
            elif isinstance(tool, SamBoxMasker):
                tool.box_start = point
                tool.is_drawing_box = True

        elif event.button() == Qt.MouseButton.RightButton:
            tool = self.parent.tool_manager.current_tool
            if isinstance(tool, ManualMask):
                tool.pop_last_point()
            elif isinstance(tool, SamMasker2):
                scene_pos = self.mapToScene(event.position().toPoint())
                point = (int(scene_pos.x()), int(scene_pos.y()))
                tool.add_point(point, 0)

        elif event.button() == Qt.MouseButton.MiddleButton:
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
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

        scene_pos = self.mapToScene(event.position().toPoint())
        point = (int(scene_pos.x()), int(scene_pos.y()))

        self.x, self.y = point

        tool = self.parent.tool_manager.current_tool
        if isinstance(tool, IntelligentScissors) and getattr(tool, "seed_points", None):
            tool.update_dynamic_path((self.x, self.y))

        if isinstance(tool, SamBoxMasker) and getattr(tool, "is_drawing_box", False):
            tool.update_box_preview(tool.box_start, point)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            tool = self.parent.tool_manager.current_tool
            if isinstance(tool, SamBoxMasker) and getattr(tool, "is_drawing_box", False):
                scene_pos = self.mapToScene(event.position().toPoint())
                point = (int(scene_pos.x()), int(scene_pos.y()))
                tool.add_box(tool.box_start, point)
                tool.is_drawing_box = False

        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # ---------- Helpers ----------

    def _rebuild_mask_index(self):
        """Cache mask_id -> polygon(int32) for fast highlight path."""
        self._mask_index.clear()
        masks = self.parent.state_manager.mask_manager.load_masks(
            self.parent.state_manager.current_image_name
        )
        for mask_id, mask, *_ in masks:
            if mask.shape[0] >= 3:
                self._mask_index[str(mask_id)] = mask.astype(np.int32)

    def _set_base_pixmap(self, image_rgb):
        """Upload base image once."""
        h, w, ch = image_rgb.shape
        q_image = QImage(image_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.pixmap_item.setPixmap(QPixmap.fromImage(q_image))

    def _update_pixmap(self, image):
        """(kept for compatibility, but base is uploaded via _set_base_pixmap)"""
        self._set_base_pixmap(image)

    def get_clicked_masks(self, click_point):
        """Use cached polygons for hit-test; no DB calls."""
        clicked_masks = []
        for mask_id, poly in self._mask_index.items():
            if cv2.pointPolygonTest(poly, click_point, measureDist=False) >= 0:
                clicked_masks.append(str(mask_id))
        return clicked_masks
