from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
import cv2
import os 
from core.data import DataManager
from PyQt6.QtGui import QColor, QBrush

class MaskResultsDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setWindowTitle("Mask Results")
        self.resize(400, 300)


        # Main layout
        layout = QVBoxLayout(self)

        # Create table widget
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Mask ID", "Surface Area", "Class"])

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
        if self.parent.image_display.masker:
            self.parent.image_display.masker.mask_added.connect(self.refresh_table)
    def populate_table(self):
        """
        Populate the table with mask IDs, surface areas, and class names with respective colors.
        """
        if not self.parent.state_manager.current_masks:
            self.table.setRowCount(0)
            return

        # Retrieve mask files associated with the current image
        mask_files = DataManager().list_masks(self.parent.state_manager.current_image_name)

        for idx, mask_file in enumerate(mask_files):
            mask = DataManager().load_mask(mask_file)
            filename = os.path.basename(mask_file)
            parts = filename.split('_')
            surface_area = cv2.contourArea(mask.astype(int))
            mask_id = '_'.join(parts[:-1])
            seg_name = parts[-1].replace('.dat', '')

            # Retrieve the associated color for this mask
            color = self.parent.state_manager.get_mask_color(seg_name)
            

            # Add row to the table
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(mask_id))
            self.table.setItem(row, 1, QTableWidgetItem(f"{surface_area:.2f}"))

            # Create a QTableWidgetItem for the class name with the color
            class_item = QTableWidgetItem(seg_name)
            class_item.setForeground(QBrush(color))
            self.table.setItem(row, 2, class_item)

    def refresh_table(self, image_path):
        """
        Refresh the table with the masks of the new current image.
        """
        self.table.setRowCount(0)  # Clear the table
        self.populate_table()  # Repopulate the table
