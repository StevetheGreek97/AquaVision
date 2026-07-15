# ui/elements/image_display/edit_modes.py
"""
Transient, single-mask edit modes for ImageDisplay (split stroke, brush edit).

A mode owns all of its interaction state and graphics items; ImageDisplay just
delegates input events to the active mode (see start_edit_mode /
cancel_edit_mode there). Event hooks return True when the event was consumed.
"""
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPen, QColor, QImage, QPixmap, QPainterPath
from PyQt6.QtWidgets import QGraphicsPathItem
from shapely.geometry import Polygon, LineString
from shapely.ops import split as shapely_split
from services.logger import get_logger

logger = get_logger(__name__)


class MaskEditMode:
    """
    Base class for mask edit modes: lifecycle plus no-op event hooks.

    Lifecycle:
        display.start_edit_mode(Mode(display, mask_id)) calls start(); the
        mode ends via finish() (or display.cancel_edit_mode()), which always
        runs stop() exactly once for cleanup.

    Subclasses override the event hooks they need and may set `cursor`.
    """

    cursor = Qt.CursorShape.CrossCursor

    def __init__(self, display, mask_id):
        self.display = display
        self.state = display.parent.state_manager
        self.mask_id = str(mask_id)

    # ------- shared helpers -------
    def mask_polygon(self):
        return self.display._mask_index.get(self.mask_id)

    def mask_class(self) -> str:
        row = self.state.db.fetch_one(
            "SELECT class_name FROM masks WHERE id = ?", (int(self.mask_id),))
        return row[0] if row else "object"

    def replace_mask(self, pieces):
        """Save `pieces` (list of Nx2 float32 polygons) and delete the original mask."""
        image_name = self.state.current_image_name
        class_name = self.mask_class()
        for piece in pieces:
            self.state.mask_manager.save_mask(piece, image_name, class_name)
        self.state.mask_manager.delete_masks(image_name, [int(self.mask_id)], profile=False)
        return class_name

    def finish(self):
        """End the mode (runs stop() via the display)."""
        self.display.cancel_edit_mode()

    # ------- lifecycle -------
    def start(self) -> bool:
        """Prepare the mode; return False to abort activation."""
        return True

    def stop(self):
        """Remove graphics and restore the display. Called exactly once."""

    # ------- event hooks (return True = consumed) -------
    def mouse_press(self, point, button) -> bool:
        return False

    def mouse_move(self, point) -> bool:
        return False

    def mouse_release(self, button) -> bool:
        return False

    def wheel(self, event) -> bool:
        return False

    def key_press(self, event) -> bool:
        if event.key() == Qt.Key.Key_Escape:
            self.finish()
            return True
        return False


class SplitStrokeMode(MaskEditMode):
    """
    Cut one mask into pieces along a freehand stroke.

    Left-drag draws the stroke (dashed preview), release performs the cut;
    right-click or Esc cancels.
    """

    def __init__(self, display, mask_id):
        super().__init__(display, mask_id)
        self._points = []
        self._drawing = False
        self._preview = None

    # ------- lifecycle -------
    def start(self):
        if self.mask_polygon() is None:
            logger.warning("Split: mask %s not found on current image", self.mask_id)
            return False
        logger.info("Split mode armed for mask %s (drag a stroke; right-click or Esc cancels)",
                    self.mask_id)
        return True

    def stop(self):
        self._remove_preview()
        self._points = []
        self._drawing = False

    # ------- events -------
    def mouse_press(self, point, button):
        if button == Qt.MouseButton.LeftButton:
            self._points = [point]
            self._drawing = True
            return True
        if button == Qt.MouseButton.RightButton:
            self.finish()
            return True
        return False

    def mouse_move(self, point):
        if not self._drawing:
            return False
        if not self._points or point != self._points[-1]:
            self._points.append(point)
            self._update_preview()
        return True

    def mouse_release(self, button):
        if button == Qt.MouseButton.LeftButton and self._drawing:
            self._finish_stroke()
            return True
        return False

    # ------- internals -------
    def _remove_preview(self):
        if self._preview is not None:
            self.display.scene.removeItem(self._preview)
            self._preview = None

    def _update_preview(self):
        if self._preview is None:
            pen = QPen(QColor(255, 60, 60), 2, Qt.PenStyle.DashLine)
            self._preview = QGraphicsPathItem()
            self._preview.setPen(pen)
            self._preview.setZValue(20)
            self.display.scene.addItem(self._preview)
        path = QPainterPath()
        path.moveTo(self._points[0][0], self._points[0][1])
        for x, y in self._points[1:]:
            path.lineTo(x, y)
        self._preview.setPath(path)

    def _finish_stroke(self):
        """Mouse released: cut along the drawn stroke, or re-arm if too short."""
        points = self._points
        self._drawing = False

        if len(points) < 2:
            # A bare click — keep the mode armed so the user can try again
            self._points = []
            self._remove_preview()
            logger.debug("Split stroke too short; mode stays armed")
            return

        self.finish()          # cleanup first; the cut below is a pure data op
        self._split(points)

    def _split(self, stroke_points):
        """Cut the mask along the freehand stroke into separate masks."""
        poly_pts = self.mask_polygon()
        if poly_pts is None or poly_pts.shape[0] < 3:
            logger.warning("Split: mask %s not found on current image", self.mask_id)
            return

        poly = Polygon(poly_pts)
        if not poly.is_valid:
            poly = poly.buffer(0)  # heal self-intersections
            if poly.geom_type == "MultiPolygon":
                poly = max(poly.geoms, key=lambda g: g.area)
        if poly.is_empty:
            logger.warning("Split: mask %s has degenerate geometry; not split", self.mask_id)
            return

        # Smooth out cursor jitter, then extend both stroke ends far beyond
        # the mask so the cut always goes all the way through.
        stroke = LineString(stroke_points).simplify(1.0)
        coords = [np.asarray(c, dtype=float) for c in stroke.coords]
        if len(coords) < 2:
            logger.debug("Split stroke too short after simplification; nothing done")
            return

        minx, miny, maxx, maxy = poly.bounds
        reach = np.hypot(maxx - minx, maxy - miny) + 10

        def _extended(tip, inner):
            direction = tip - inner
            norm = np.hypot(*direction)
            return tip if norm < 1e-6 else tip + direction / norm * reach

        head = _extended(coords[0], coords[1])
        tail = _extended(coords[-1], coords[-2])
        cut_line = LineString([tuple(head)] + [tuple(c) for c in coords] + [tuple(tail)])

        try:
            pieces = [g for g in shapely_split(poly, cut_line).geoms
                      if g.geom_type == "Polygon" and g.area > 1.0]
        except Exception:
            logger.exception("Split of mask %s failed; try a simpler stroke", self.mask_id)
            return
        if len(pieces) < 2:
            logger.info("Split stroke does not cross mask %s; nothing changed", self.mask_id)
            return

        class_name = self.replace_mask(
            [np.array(g.exterior.coords[:-1], dtype=np.float32) for g in pieces])

        self.display.refresh_masks()
        logger.info("Split mask %s into %d masks (class %r)",
                    self.mask_id, len(pieces), class_name)


class BrushEditMode(MaskEditMode):
    """
    Paint / erase one mask with a circular brush.

    Left-drag paints, right-drag erases, scroll resizes the brush,
    Ctrl+scroll zooms, S applies, Esc cancels.
    """

    cursor = Qt.CursorShape.BlankCursor  # the circle item replaces the cursor
    _last_radius = 15                    # remembered across brush sessions

    def __init__(self, display, mask_id):
        super().__init__(display, mask_id)
        self.radius = BrushEditMode._last_radius
        self._bitmap = None              # np.uint8 working raster of the mask
        self._class = None
        self._value = None               # 255 while painting, 0 while erasing
        self._last = None                # last stamp point (gap-free strokes)
        self._cursor_item = None         # circle following the mouse
        self._timer = QTimer(display)    # throttles preview uploads
        self._timer.setSingleShot(True)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._refresh_overlay)

    # ------- lifecycle -------
    def start(self):
        poly = self.mask_polygon()
        image = self.state.current_image
        if poly is None or image is None:
            logger.warning("Brush: mask %s not found on current image", self.mask_id)
            return False

        self._class = self.mask_class()

        h, w = image.shape[:2]
        self._bitmap = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(self._bitmap, [poly.astype(np.int32)], 255)

        # Hide this mask's baked fill so erased areas read correctly
        display = self.display
        display.cached_image_with_masks = display.overlay_base_masks(
            image, exclude_ids={int(self.mask_id)})
        display._set_base_pixmap(display.cached_image_with_masks)

        self._refresh_overlay()
        logger.info("Brush mode armed for mask %s (left-drag paints, right-drag erases, "
                    "scroll resizes, Ctrl+scroll zooms, S applies, Esc cancels)", self.mask_id)
        return True

    def stop(self):
        self._timer.stop()
        self._bitmap = None
        if self._cursor_item is not None:
            self.display.scene.removeItem(self._cursor_item)
            self._cursor_item = None
        # Clear the working overlay and restore the normal base render
        if self.display._hl_img is not None:
            self.display._hl_img.fill(0)
            self.display.highlight_item.setPixmap(QPixmap.fromImage(self.display._hl_img))
        self.display.refresh_masks()

    # ------- events -------
    def mouse_press(self, point, button):
        if button == Qt.MouseButton.LeftButton:
            self._value = 255  # paint
        elif button == Qt.MouseButton.RightButton:
            self._value = 0    # erase
        else:
            return False
        self._last = None
        self._stamp(point)
        return True

    def mouse_move(self, point):
        self._move_cursor(point)
        if self._value is not None:
            self._stamp(point)
        return True  # brush mode swallows tool/selection interactions

    def mouse_release(self, button):
        if button in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._value = None
            self._last = None
            self._refresh_overlay()
            return True
        return False

    def wheel(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return False  # Ctrl+scroll falls through to the view's zoom
        step = 2 if event.angleDelta().y() > 0 else -2
        self.radius = max(3, min(200, self.radius + step))
        BrushEditMode._last_radius = self.radius
        if self.display.x is not None:
            self._move_cursor((self.display.x, self.display.y))
        return True

    def key_press(self, event):
        if event.key() == Qt.Key.Key_S:
            self._commit()
            return True
        super().key_press(event)  # Esc cancels
        return True  # swallow remaining keys while editing

    # ------- internals -------
    def _stamp(self, point):
        """Stamp a filled circle; connect to the previous stamp so fast drags leave no gaps."""
        cv2.circle(self._bitmap, point, self.radius, self._value, -1)
        if self._last is not None and self._last != point:
            cv2.line(self._bitmap, self._last, point, self._value,
                     thickness=max(1, self.radius * 2))
        self._last = point
        if not self._timer.isActive():
            self._timer.start()

    def _refresh_overlay(self):
        """Render the working bitmap as a translucent fill + white outline."""
        if self._bitmap is None:
            return
        color = self.state.class_manager.get_class_color(self._class)
        h, w = self._bitmap.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[self._bitmap > 0] = (color.red(), color.green(), color.blue(), 120)
        edges = cv2.morphologyEx(self._bitmap, cv2.MORPH_GRADIENT,
                                 np.ones((3, 3), np.uint8)) > 0
        rgba[edges] = (255, 255, 255, 230)
        qimg = QImage(rgba.data, w, h, 4 * w, QImage.Format.Format_RGBA8888)
        self.display.highlight_item.setPixmap(QPixmap.fromImage(qimg.copy()))

    def _move_cursor(self, point):
        r = self.radius
        if self._cursor_item is None:
            self._cursor_item = self.display.scene.addEllipse(
                0, 0, 0, 0, QPen(QColor(255, 255, 255), 1.5))
            self._cursor_item.setZValue(30)
        self._cursor_item.setRect(point[0] - r, point[1] - r, 2 * r, 2 * r)

    def _commit(self):
        """Re-contour the working bitmap and replace the original mask with the result."""
        bitmap, mask_id = self._bitmap, self.mask_id

        contours, _ = cv2.findContours(bitmap, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        pieces = [c.squeeze(axis=1).astype(np.float32) for c in contours
                  if c.shape[0] >= 3 and cv2.contourArea(c) > 10]

        self.replace_mask(pieces)
        self.finish()  # stop() restores the base render via refresh_masks()
        logger.info("Brush edit applied: mask %s replaced by %d mask(s)", mask_id, len(pieces))
