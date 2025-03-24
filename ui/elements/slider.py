from PyQt6.QtWidgets import QSlider, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer


class ImageSlider(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        layout = QVBoxLayout(self)

        # Label to display the current image index
        self.label = QLabel("Image: 0 / 0", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        # Slider for image navigation
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)  # Updated dynamically
        self.slider.setValue(0)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.setSingleStep(1)

        layout.addWidget(self.slider)

        # **Delay Timer** to make image switching smoother
        self.timer = QTimer()
        self.timer.setSingleShot(True)  # Ensure it runs only once per event
        self.timer.timeout.connect(self.update_image)

        # Connect slider change event (delayed response)
        self.slider.valueChanged.connect(self.on_slider_changed)

        # Listen for image changes from the main application
        self.parent.state_manager.image_changed.connect(self.update_slider)

    def set_image_count(self, count):
        """Update the slider range and label based on the total image count."""
        self.slider.setMaximum(max(count - 1, 0))  # Prevent negative values
        self.update_slider(self.parent.state_manager.current_image_path)

    def on_slider_changed(self, value):
        """Handle slider movement and trigger a delayed image update."""
        self.label.setText(f"Image: {value + 1} / {len(self.parent.state_manager.image_paths)}")
        self.timer.start(150)  # **Delay image loading** (150ms)

    def update_image(self):
        """Update the displayed image based on the slider position."""
        if self.parent.state_manager.image_paths:
            self.parent.state_manager.image_index = self.slider.value()
            image_path = self.parent.state_manager.current_image_path
            self.parent.image_display.display_image(image_path)
            self.update_label(self.slider.value())

    def update_slider(self, image_path):
        """Ensure the slider stays in sync when the image changes."""
        if image_path in self.parent.state_manager.image_paths:
            index = self.parent.state_manager.image_paths.index(image_path)
            self.slider.blockSignals(True)  # Prevent recursion loop
            self.slider.setValue(index)
            self.slider.blockSignals(False)
            self.update_label(index)

    def update_label(self, index):
        """Update the slider label based on the current index."""
        total_images = len(self.parent.state_manager.image_paths)
        self.label.setText(f"Image: {index + 1} / {total_images}")
