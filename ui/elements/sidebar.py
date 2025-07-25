from PyQt6.QtWidgets import (
    QVBoxLayout, QPushButton, QHBoxLayout, QWidget, QComboBox, QColorDialog, QInputDialog
)
import qtawesome as qta
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QMessageBox
import re
from services.file_handlers import get_tooltip
from PyQt6.QtCore import pyqtSignal

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
        self._init_sam2_box()
        self._init_dextr()
        self._init_intelligent_scissors()
        self._init_class_management()


    def _init_class_management(self):
        """
        Initialize class management UI elements (Dropdown, Add, Remove, Color Picker).
        """
        # Dropdown for class selection
        self.class_dropdown = QComboBox(self)
        self.layout.addWidget(self.class_dropdown)

        # Add and Remove buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Class")
        add_button.clicked.connect(self.add_class)
        button_layout.addWidget(add_button)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected_class)
        button_layout.addWidget(remove_button)

        self.layout.addLayout(button_layout)

        # Populate dropdown at startup
        self.populate_class_dropdown()
   
    def _init_navigation_buttons(self):
        button_layout = QHBoxLayout()

        prev_button = self._create_icon_button("fa5s.arrow-left", self.parent.previous_image, "prev_image")
        next_button = self._create_icon_button("fa5s.arrow-right", self.parent.next_image, "next_image")

        button_layout.addWidget(prev_button)
        button_layout.addWidget(next_button)
        self.layout.addLayout(button_layout)

    def _init_manual_mask(self):
        self.manual_mask = self._create_icon_button("fa5s.pencil-alt", self.toggle_manual_mask, "manual_mask", None)
        self.manual_mask.setCheckable(True)
        self.layout.addWidget(self.manual_mask)
    
    def _init_sam2_box(self):
        self.sam2box = self._create_icon_button('', self.toggle_sam2_boxer, "sam2_box", 'SAM2-Box')
        self.sam2box.setCheckable(True)
        self.layout.addWidget(self.sam2box)

    def _init_dextr(self):

        self.dextr = self._create_icon_button('', self.toggle_dextr, "dextr", 'DEXTR')
        self.dextr.setCheckable(True)
        self.layout.addWidget(self.dextr)

    def _init_sam2(self):

        self.sam2 = self._create_icon_button('', self.toggle_sam2, "sam2", 'Segment Anything 2')
        self.sam2.setCheckable(True)
        self.layout.addWidget(self.sam2)
    
    def _init_intelligent_scissors(self):
        """
        Initialize the Intelligent Scissors toggle button.
        """
        #self.intelligent_scissors = QPushButton("Intelligent Scissors", self)
        self.intelligent_scissors = self._create_icon_button("fa5s.cut", self.toggle_intelligent_scissors, "intelligent_scissors", None)
        self.intelligent_scissors.setCheckable(True)
        self.layout.addWidget(self.intelligent_scissors)
   
    def toggle_sam2_boxer(self):
        """
        Toggle SAM2 mode using ToolManager.
        """
        if self.sam2box.isChecked():
            self.parent.tool_manager.enable_tool("sam2_box")  # ✅ Use ToolManager
        else:
            self.parent.tool_manager.disable_tools()

    def toggle_dextr(self):
        """
        Toggle SAM2 mode using ToolManager.
        """
        if self.dextr.isChecked():
            self.parent.tool_manager.enable_tool("dextr")  # ✅ Use ToolManager

        else:
            self.parent.tool_manager.disable_tools()

    def toggle_sam2(self):
        """
        Toggle SAM2 mode using ToolManager.
        """
        if self.sam2.isChecked():
            self.parent.tool_manager.enable_tool("sam2")  # ✅ Use ToolManager
        else:
            self.parent.tool_manager.disable_tools()

    def toggle_intelligent_scissors(self):
        """
        Toggle Intelligent Scissors mode using ToolManager.
        """
        if self.intelligent_scissors.isChecked():
            self.parent.tool_manager.enable_tool("intelligent_scissors")  # ✅ Use ToolManager
        else:
            self.parent.tool_manager.disable_tools()

    def toggle_manual_mask(self):
        """
        Toggle Manual Mask mode using ToolManager.
        """
        if self.manual_mask.isChecked():
            self.parent.tool_manager.enable_tool("manual_mask")  # ✅ Use ToolManager
        else:
            self.parent.tool_manager.disable_tools()

 
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

    def add_class(self):
        """
        Adds a new class using a pop-up input dialog for name and color.
        """
        # Prompt user to enter the class name
        class_name, ok = QInputDialog.getText(self, "Add Class", "Enter class name:")
        
        if not ok or not class_name.strip():
            print("❌ Class name cannot be empty.")
            return
        class_name = class_name.strip()

        # ✅ Check for allowed characters (only a-z, A-Z, 0-9, _)
        if not re.fullmatch(r"\w+", class_name):
            QMessageBox.warning(
                self, 
                "Invalid Class Name", 
                "Class name must contain only letters, numbers, and underscores (no spaces or special characters)."
            )
            return

        
        class_name = class_name.strip()

        # Open a color picker dialog
        color = QColorDialog.getColor()

        if not color.isValid():
            print("❌ No color selected. Class not added.")
            return

        # ✅ Add class to the database
        self.parent.state_manager.class_manager.add_class(class_name, color)
        print(f"✅ Added new class: {class_name} ({color.name()})")

        # ✅ Refresh the dropdown
        self.populate_class_dropdown()


    def _create_icon_button(self, fa_icon_name, callback, tooltip=None, label=None):
        button = QPushButton(label or "")
        if fa_icon_name:
            button.setIcon(qta.icon(fa_icon_name))
        button.setIconSize(QSize(14, 14))
        button.setFixedHeight(32)
        if tooltip:
            button.setToolTip(get_tooltip(tooltip))
        if callback:
            button.clicked.connect(callback)
        return button



    def remove_selected_class(self):
        current_index = self.class_dropdown.currentIndex()
        if current_index < 0:
            print("❌ No class selected for removal.")
            return

        class_name = self.class_dropdown.currentText().split(" ")[0]  # Extract name
        print(f"🗑 Preparing to remove class: {class_name}")

        # ✅ Count how many masks would be deleted
        count = self.parent.state_manager.mask_manager.count_masks_by_class(class_name)

        # ✅ Show confirmation popup
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Confirm Deletion")
        msg_box.setText(f"Are you sure you want to delete the class '{class_name}'?")
        msg_box.setInformativeText(f"This will also delete {count} mask(s) associated with this class.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        result = msg_box.exec()

        if result == QMessageBox.StandardButton.No:
            print("❌ Deletion cancelled by user.")
            return

        # ✅ Proceed with deletion
        self.parent.state_manager.class_manager.remove_class(class_name)
        self.parent.state_manager.mask_manager.delete_masks_by_class(class_name)
        self.parent.state_manager.class_manager.reindex_classes()

        self.class_dropdown.removeItem(current_index)
        print(f"✅ Class '{class_name}' and {count} mask(s) deleted and reindexed.")

        # ✅ Refresh the image display
        self.parent.image_display.display_image(self.parent.state_manager.current_image_path, preserve_zoom=True)




    def pick_class_color(self):
        """
        Open a color picker dialog and store the selected color.
        """
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color
            print(f"🎨 Selected color: {color.name()}")

    def populate_class_dropdown(self):
        """
        Populate the class selection dropdown with class names from the database.
        """
        class_manager = self.parent.state_manager.class_manager
        class_names = class_manager.get_all_class_names()

        self.class_dropdown.clear()  # Clear existing entries
        if not class_names:
            print("⚠️ No classes found in the database.")
            return

        self.class_dropdown.addItems(class_names)  # Add class names from database
        print(f"✅ Loaded {len(class_names)} classes into the dropdown.")

    def has_valid_class_selection(self):
        """
        Ensure a class is selected and the dropdown is not empty.

        Returns:
            bool: True if a valid class is selected, else False.
        """
        if self.class_dropdown.count() == 0:
            QMessageBox.warning(self, "No Classes", "⚠️ No classes defined yet. Please add a class first.")
            return False

        if self.class_dropdown.currentIndex() < 0:
            QMessageBox.warning(self, "No Class Selected", "⚠️ Please select a class before saving the mask.")
            return False

        return True
