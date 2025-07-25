from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QMouseEvent, QPainterPath

class ColorRangeSlider(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(50)
        self.left = 70
        self.right = 90
        self.dragging = None
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_y = h // 2 - 6
        bar_height = 12
        handle_radius = 8

        # Background bar (rounded)
        background_rect = QRectF(10, bar_y, w - 20, bar_height)
        painter.setBrush(QColor("#E0E0E0"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(background_rect, 6, 6)

        # Train (green)
        left_x = 10 + (self.left / 100) * (w - 20)
        right_x = 10 + (self.right / 100) * (w - 20)

        painter.setBrush(QColor("#4CAF50"))  # Green
        painter.drawRoundedRect(QRectF(10, bar_y, left_x - 10, bar_height), 6, 6)

        # Validation (orange)
        painter.setBrush(QColor("#FFA726"))  # Orange
        painter.drawRect(QRectF(left_x, bar_y, right_x - left_x, bar_height))

        # Test (blue)
        painter.setBrush(QColor("#42A5F5"))  # Blue
        painter.drawRoundedRect(QRectF(right_x, bar_y, (w - 10) - right_x, bar_height), 6, 6)

        # Handle style
        handle_style = QBrush(QColor(250, 250, 250))
        border = QPen(QColor("#888"), 1)
        painter.setPen(border)
        painter.setBrush(handle_style)

        # Draw left handle
        painter.drawEllipse(QPointF(left_x, h // 2), handle_radius, handle_radius)
        # Draw right handle
        painter.drawEllipse(QPointF(right_x, h // 2), handle_radius, handle_radius)

    def mousePressEvent(self, event: QMouseEvent):
        x = event.position().x()
        w = self.width()
        left_px = 10 + (self.left / 100) * (w - 20)
        right_px = 10 + (self.right / 100) * (w - 20)

        if abs(x - left_px) < 12:
            self.dragging = "left"
        elif abs(x - right_px) < 12:
            self.dragging = "right"

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            x = max(10, min(event.position().x(), self.width() - 10))
            percent = (x - 10) / (self.width() - 20) * 100
            if self.dragging == "left":
                self.left = min(percent, self.right - 1)
            elif self.dragging == "right":
                self.right = max(percent, self.left + 1)
            self.update()
            if self.parent():
                self.parent().update_label()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging = None

    def get_split(self):
        return int(self.left), int(self.right)


class DataSplitWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Elegant Data Split Slider")

        self.slider = ColorRangeSlider()
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
       
        self.update_label()

        layout = QVBoxLayout(self)
        layout.addWidget(self.slider)
        layout.addWidget(self.label)


    def update_label(self):
        left, right = self.slider.get_split()
        train = left
        val = right - left
        test = 100 - right
        self.label.setText(f"📊 Train: {train}%  |  Val: {val}%  |  Test: {test}%")


if __name__ == "__main__":
    app = QApplication([])
    win = DataSplitWidget()
    win.resize(400, 120)
    win.show()
    app.exec()
