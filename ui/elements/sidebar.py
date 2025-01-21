from PyQt6.QtWidgets import (
    QVBoxLayout, QPushButton, QHBoxLayout, QWidget, QComboBox, QColorDialog, QInputDialog
)
class Sidebar(QWidget):
    """
    Sidebar UI component for navigation, drawing controls, and class-color management.
    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self._init_navigation_buttons()
        self._init_manual_mask()
        self._init_sam2()
        self._init_intelligent_scissors()
        self._init_class_color_dropdown()

    def _init_class_color_dropdown(self):
        """
        Initialize the class-color dropdown menu with add/remove functionality.
        """
 
        self.class_dropdown = QComboBox(self)
        self.layout.addWidget(self.class_dropdown)

        # Add and Remove buttons
        button_layout = QHBoxLayout()

        add_button = QPushButton("Add Class")
        add_button.clicked.connect(self.parent.add_class)
        button_layout.addWidget(add_button)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.parent.remove_selected_class)
        button_layout.addWidget(remove_button)

        self.layout.addLayout(button_layout)

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
    def _init_intelligent_scissors(self):
        """
        Initialize the Intelligent Scissors toggle button.
        """
        self.intelligent_scissors = QPushButton("Intelligent Scissors", self)
        self.intelligent_scissors.setCheckable(True)  # Toggle mode
        self.intelligent_scissors.clicked.connect(self.toggle_intelligent_scissors)
        self.layout.addWidget(self.intelligent_scissors)

    def toggle_manual_mask(self):
        """
        Toggle Intelligent Scissors mode in the ImageDisplay.
        """
        if self.manual_mask.isChecked():
            self.parent.image_display.enable_manual_mask()
        else:
            self.parent.image_display.disable_manual_mask()
    def toggle_intelligent_scissors(self):
        """
        Toggle Intelligent Scissors mode in the ImageDisplay.
        """
        if self.intelligent_scissors.isChecked():
            self.parent.image_display.enable_intelligent_scissors()
        else:
            self.parent.image_display.disable_intelligent_scissors()

    
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
      
    def get_selected_class_color(self):
        """
        Get the selected class name and color from the dropdown.

        Returns:
            tuple: (class_name, QColor) of the selected class, or (None, None) if no selection.
        """
        current_index = self.class_dropdown.currentIndex()
        if current_index >= 0:
            text = self.class_dropdown.currentText()
            color = self.class_dropdown.itemData(current_index)
            return text.split(" ")[0], color  # Extract class name from text
        return None, None

 