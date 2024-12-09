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


        self._init_navigation_buttons()
        self._init_manual_mask()
        self._init_sam2()

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


    def _init_manual_mask(self):
        self.manual_mask = QPushButton("Manual Mask", self)
        self.manual_mask.setCheckable(True)  # Toggle mode
        self.manual_mask.clicked.connect(self.toggle_manual_mask)
        self.layout.addWidget(self.manual_mask)

    def _init_sam2(self):
        self.sam2 = QPushButton("Segment Anything 2", self)
        self.sam2.setCheckable(True)  # Toggle mode
        self.sam2.clicked.connect(self.toggle_sam2)
        self.layout.addWidget(self.sam2)

    def toggle_manual_mask(self):
        """
        Toggle Intelligent Scissors mode in the ImageDisplay.
        """
        if self.manual_mask.isChecked():
            self.parent.image_display.enable_manual_mask()
        else:
            self.parent.image_display.disable_manual_mask()
    def toggle_sam2(self):
        """
        Toggle Intelligent Scissors mode in the ImageDisplay.
        """
        if self.sam2.isChecked():
            self.parent.image_display.enable_sam2()
        else:
            self.parent.image_display.disable_sam2()


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
