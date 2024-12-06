from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QWidget


class Sidebar(QWidget):
    """
    Sidebar UI component for navigation and drawing controls.
    """

    def __init__(self, parent):
        """
        Initialize the Sidebar with navigation and drawing controls.

        Args:
            parent: Parent QWidget for the Sidebar.
            navigation_callbacks (dict): Contains `prev_image` and `next_image` callbacks.
        """
        super().__init__()
        self.parent = parent
   

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        # Add Intelligent Scissors button
        self.scissors_button = QPushButton("Manual Mask", self)
        self.scissors_button.setCheckable(True)  # Toggle mode
        self.scissors_button.clicked.connect(self.toggle_scissors_mode)
        self.layout.addWidget(self.scissors_button)

        self._init_navigation_buttons()
        self._init_drawing_button()

    def _init_navigation_buttons(self):
        """
        Initialize the navigation buttons (Previous and Next).
        """
        button_layout = QHBoxLayout()

        prev_button = self._create_button("Previous Image", self.parent.previous_image)
        button_layout.addWidget(prev_button)

        next_button = self._create_button("Next Image",self.parent.next_image)
        button_layout.addWidget(next_button)

        self.layout.addLayout(button_layout)

    def _init_drawing_button(self):
        """
        Initialize the button to toggle rectangle drawing mode.
        """
        self.draw_rect_button = QPushButton("Draw Rectangle")
        self.draw_rect_button.setCheckable(True)  # Enable toggle functionality
        self.draw_rect_button.clicked.connect(self._toggle_rectangle_drawing)
        self.layout.addWidget(self.draw_rect_button)

    def _toggle_rectangle_drawing(self):
        """
        Toggle the rectangle drawing mode on/off.
        """
        if self.draw_rect_button.isChecked():
            self.parent.image_display.enable_rectangle_drawing()
            self.draw_rect_button.setText("Stop Drawing")
        else:
            self.parent.image_display.disable_rectangle_drawing()
            self.draw_rect_button.setText("Draw Rectangle")

    def toggle_scissors_mode(self):
        """
        Toggle Intelligent Scissors mode in the ImageDisplay.
        """
        if self.scissors_button.isChecked():
            self.parent.image_display.enable_manual_mask()
        else:
            self.parent.image_display.disable_manual_mask()
    @staticmethod
    def _create_button(label, callback):
        """
        Utility function to create a QPushButton.

        Args:
            label (str): Text label for the button.
            callback (callable): Function to execute on button click.

        Returns:
            QPushButton: Configured button.
        """
        button = QPushButton(label)
        if callback:
            button.clicked.connect(callback)
        return button
