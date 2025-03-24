import cv2
import numpy as np
import heapq
from PyQt6.QtCore import pyqtSignal,QObject, QPointF, QRectF, QTimer
from PyQt6.QtGui import QPolygonF, QPen, QColor
from PyQt6.QtWidgets import QGraphicsPolygonItem, QGraphicsEllipseItem
from shapely.geometry import Polygon


class IntelligentScissors(QObject):
    """
    Optimized Intelligent Scissors functionality.
    """
    mask_added = pyqtSignal(str, np.ndarray)

    def __init__(self, parent, threshold=100):
        super().__init__()
        self.parent = parent
        self.edge_weights = None  # Precomputed edge weights
        self.seed_points = []
        self.polygon_points = []
        self.current_polygon_item = None
        self.dynamic_path_item = None
        self.path_cache = {}  # Cache for computed paths with a size limit
        self.anchor_point = None  # Save the last intermediate anchor point
        self.scale_factor = 0.5  # Default scaling factor
        self.threshold = threshold
        self.restrictive_circle_item = None

        # Timer for throttling scene updates
        self.update_timer = QTimer()
        self.update_timer.setInterval(5)  # Update every 50ms
        self.update_timer.timeout.connect(self.render_updates)
        self.pending_updates = []  # Store pending updates

    def update_dynamic_path(self, cursor_position):
        """
        Update the dynamic path from the last seed or anchor point to the cursor position.
        """
        if not self.seed_points:
            return

        last_point = self.anchor_point if self.anchor_point else self.seed_points[-1]
        distance = np.hypot(cursor_position[0] - last_point[0], cursor_position[1] - last_point[1])

        if distance > self.threshold:
            # Approximate path for distant points
            dynamic_path = self.approximate_path(last_point, cursor_position)
        else:
            # Full path computation for closer points
            dynamic_path = self.compute_path(last_point, cursor_position)

        self.pending_updates.append(dynamic_path)
        if not self.update_timer.isActive():
            self.update_timer.start()

    def render_updates(self):
        """
        Render pending updates in batches to reduce rendering overhead.
        """
        if not self.pending_updates:
            self.update_timer.stop()
            return

        dynamic_path = self.pending_updates.pop(0)
        path_polygon = QPolygonF([QPointF(x, y) for x, y in dynamic_path])

        if not self.dynamic_path_item:
            pen = QPen(QColor(0, 0, 0))  # Black color
            pen.setWidth(2)
            self.dynamic_path_item = QGraphicsPolygonItem()
            self.dynamic_path_item.setPen(pen)
            self.parent.scene.addItem(self.dynamic_path_item)

        self.dynamic_path_item.setPolygon(path_polygon)

    def set_image(self, image):
        """
        Set the current image and compute the edge map and weights.
        """
        if image is not None:
            
            #raise ValueError("No image provided.")

            resized_image = cv2.resize(image, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
            gray_image = cv2.cvtColor(resized_image, cv2.COLOR_RGB2GRAY)
            edge_map = cv2.Canny(gray_image, 50, 150)
            self.edge_weights = 1 / (edge_map + 1e-5)  # Avoid division by zero
            print("Edge map and weights computed.")
        else: 
            print('Image not found')

    def add_seed_point(self, point):
        """
        Add a seed point and update the polygon.
        """
        if self.edge_weights is None:
            return
            #raise ValueError("Edge weights not set. Please set the image first.")

        if self.seed_points:
            last_point = self.seed_points[-1]
            distance = np.hypot(point[0] - last_point[0], point[1] - last_point[1])
            if distance > self.threshold:
                print(f"Point {point} is outside the restrictive threshold.")
                return

        self.seed_points.append(point)
        self.anchor_point = point  # Save this point as an anchor

        if len(self.seed_points) > 1:
            start = self.seed_points[-2]
            end = self.seed_points[-1]
            path = self.compute_path(start, end)
            self.polygon_points.extend(path)

        self.update_polygon()
        self.clear_dynamic_path()
        self.draw_restrictive_threshold(point)

    def draw_restrictive_threshold(self, center):
        """
        Draw a visual representation of the restrictive threshold around the last seed point.
        """
        if self.restrictive_circle_item:
            self.parent.scene.removeItem(self.restrictive_circle_item)

        rect = QRectF(center[0] - self.threshold, center[1] - self.threshold, self.threshold * 2, self.threshold * 2)
        pen = QPen(QColor(255, 0, 0))  # Red color
        pen.setWidth(1)
        self.restrictive_circle_item = QGraphicsEllipseItem(rect)
        self.restrictive_circle_item.setPen(pen)
        self.parent.scene.addItem(self.restrictive_circle_item)

    def compute_path(self, start, end):
        """
        Compute the minimum cost path between two points.
        """
        scaled_start = (int(start[0] * self.scale_factor), int(start[1] * self.scale_factor))
        scaled_end = (int(end[0] * self.scale_factor), int(end[1] * self.scale_factor))

        if (scaled_start, scaled_end) in self.path_cache:
            scaled_path = self.path_cache[(scaled_start, scaled_end)]
        else:
            scaled_path = self._astar_path(scaled_start, scaled_end)
            if len(self.path_cache) > 1000:  # Limit cache size
                self.path_cache.pop(next(iter(self.path_cache)))
            self.path_cache[(scaled_start, scaled_end)] = scaled_path

        return [(int(x / self.scale_factor), int(y / self.scale_factor)) for x, y in scaled_path]

    def approximate_path(self, start, end):
        """
        Approximate a straight-line path between two points for distant cursor movements.
        """
        x1, y1 = start
        x2, y2 = end
        num_points = int(np.hypot(x2 - x1, y2 - y1))
        line_x = np.linspace(x1, x2, num_points, dtype=int)
        line_y = np.linspace(y1, y2, num_points, dtype=int)
        return list(zip(line_x, line_y))

    def _astar_path(self, start, end):
        """
        A* pathfinding algorithm.
        """
        h, w = self.edge_weights.shape
        costs = np.full((h, w), np.inf, dtype=np.float32)
        costs[start[1], start[0]] = 0
        prev = np.full((h, w, 2), -1, dtype=np.int32)
        pq = [(0, start)]

        visited = set()  # To avoid revisiting nodes

        while pq:
            _, current = heapq.heappop(pq)
            if current == end:
                break

            if current in visited:
                continue
            visited.add(current)

            x, y = current

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    edge_cost = self.edge_weights[ny, nx]
                    new_cost = costs[y, x] + edge_cost
                    heuristic = abs(nx - end[0]) + abs(ny - end[1])
                    total_cost = new_cost + heuristic

                    if new_cost < costs[ny, nx]:
                        costs[ny, nx] = new_cost
                        prev[ny, nx] = [x, y]
                        heapq.heappush(pq, (total_cost, (nx, ny)))

        path = []
        x, y = end
        while (x, y) != (-1, -1):
            path.append((x, y))
            x, y = prev[y, x]
        return path[::-1]

    def update_polygon(self):
        """
        Update the polygon display in the parent scene.
        """
        if self.current_polygon_item:
            self.parent.scene.removeItem(self.current_polygon_item)
            self.current_polygon_item = None

        if not self.polygon_points:
            return

        #simplified_points = self.simplify_polygon(self.polygon_points)
        polygon = QPolygonF([QPointF(x, y) for x, y in self.polygon_points])

        pen = QPen(QColor(0, 255, 255))  # Cyan color
        pen.setWidth(2)
        polygon_item = QGraphicsPolygonItem(polygon)
        polygon_item.setPen(pen)
        self.parent.scene.addItem(polygon_item)
        self.current_polygon_item = polygon_item

    def simplify_polygon(self, points, tolerance=2.0):
        """
        Simplify a polygon for rendering.
        """
        polygon = Polygon(points)
        simplified = polygon.simplify(tolerance, preserve_topology=True)
        return list(simplified.exterior.coords)

    def clear_dynamic_path(self):
        if self.dynamic_path_item:
            self.parent.scene.removeItem(self.dynamic_path_item)
            self.dynamic_path_item = None

    def clear_polygon(self):
        self.seed_points = []
        self.polygon_points = []
        self.anchor_point = None  # Reset the anchor point

        if self.current_polygon_item:
            self.parent.scene.removeItem(self.current_polygon_item)
            self.current_polygon_item = None

        self.clear_dynamic_path()
        print("Polygon cleared.")
    def remove_restrictive_threshold(self):
        """
        Remove the restrictive threshold visual indicator.
        """
        if self.restrictive_circle_item:
            self.parent.scene.removeItem(self.restrictive_circle_item)
            self.restrictive_circle_item = None
    def complete_mask(self):
        """
        Complete the current mask and add it to the list of masks.
        """
        if not self.parent.parent.sidebar.has_valid_class_selection():
            self.clear_temp_items()
            return  # ❌ Cancel saving if no valid class is selected

        # Create the mask polygon from the polygon points
        mask_polygon = np.array(self.polygon_points, dtype=np.float32)
        class_name, selected_color = self.parent.parent.sidebar.get_selected_class_color()
        self.parent.parent.state_manager.mask_manager.save_mask(mask_polygon, self.parent.parent.state_manager.current_image_name, class_name)
        # Emit the signal
        self.mask_added.emit(self.parent.parent.state_manager.current_image_name, mask_polygon)
        
        # Clear temporary items
        self.clear_temp_items()


    def clear_temp_items(self):
        self.clear_polygon()
        self.remove_restrictive_threshold()

 


        # Clear temporary items
        return 

