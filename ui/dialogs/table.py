from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import Qt
import cv2
import numpy as np
from PyQt6.QtGui import QColor, QBrush

class MaskResultsDialog(QDialog):
    masks_selected = pyqtSignal(list)  # Signal for mask selection

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setWindowTitle("Mask Results")
        self.resize(400, 300)

        # Main layout
        layout = QVBoxLayout(self)

        # Create table widget
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Image Name", "Mask ID", "Surface Area", "Class"])
        self.table.itemChanged.connect(self.on_item_changed)  # Detect changes in the table
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Populate the table
        self.populate_table()

        # Add close button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)

        # Add widgets to layout
        layout.addWidget(self.table)
        layout.addWidget(close_button)

        # Connect image_changed signal to refresh_table
        self.parent.state_manager.image_changed.connect(self.refresh_table)

        self.table.itemSelectionChanged.connect(self.on_selection_changed)

    def populate_table(self):
        """
        Populate the table with mask IDs, surface areas, and class names with respective colors.
        """
        self.table.setRowCount(0)  # Clear previous rows

        # Retrieve masks from the database
        masks = self.parent.state_manager.mask_manager.load_masks(self.parent.state_manager.current_image_name)

        for mask_id, mask, class_name in masks:
            surface_area = cv2.contourArea(mask.astype(np.int32)) if len(mask) > 0 else 0

            # Retrieve the associated color for this mask
            color = self.parent.state_manager.class_manager.get_class_color(class_name)

            # Add row to the table
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(self.parent.state_manager.current_image_name))  # Image Name
            self.table.setItem(row, 1, QTableWidgetItem(str(mask_id)))  # Mask ID
            self.table.setItem(row, 2, QTableWidgetItem(f"{surface_area:.2f}"))  # Surface Area

            # Create a QTableWidgetItem for the class name with the color
            class_item = QTableWidgetItem(class_name)
            class_item.setForeground(QBrush(color))
            class_item.setFlags(class_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, class_item)  # Class Name

    def refresh_table(self, image_path):
        """
        Refresh the table with the masks of the new current image.
        """
        self.populate_table()  # Repopulate the table
    

    def on_selection_changed(self):
        """
        Emit all selected rows as a list of dictionaries and enable mask editing.
        """
        selected_rows = []
        selected_mask_ids = []  # To ensure multiple masks are tracked

        for item in self.table.selectedItems():
            if item.column() == 1:  # Mask ID column
                row = item.row()
                row_data = {
                    "image_name": self.table.item(row, 0).text(),
                    "mask_id": self.table.item(row, 1).text(),
                    "class": self.table.item(row, 3).text()
                }
                selected_rows.append(row_data)
                selected_mask_ids.append(row_data["mask_id"])

        print(f"Selected Rows: {selected_rows}")  # Debugging

        # Emit the selected rows
        self.masks_selected.emit(selected_rows)


    def on_item_changed(self, item):
        """
        Handle changes in the class name column and update the corresponding database record.
        """
        if item.column() == 3:  # Class column
            row = item.row()
            new_class_name = item.text()
            mask_id = int(self.table.item(row, 1).text())  # Convert mask_id to integer
            image_name = self.table.item(row, 0).text()

            # Update class name in the database
            self.parent.state_manager.mask_manager.rename_mask(image_name, mask_id, new_class_name)
