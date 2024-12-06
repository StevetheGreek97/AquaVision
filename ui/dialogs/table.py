from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
import cv2
import numpy as np
class MaskResultsDialog(QDialog):
    def __init__(self, parent, image_path, image_mask):
        super().__init__(parent)
        self.setWindowTitle("Mask Results")
        self.resize(400, 300)

        self.image_path = image_path
        self.image_mask = image_mask

        # Main layout
        layout = QVBoxLayout(self)

        # Create table widget
        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Mask ID", "Surface Area"])

        # Populate the table
        self.populate_table()

        # Add close button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)

        # Add widgets to layout
        layout.addWidget(self.table)
        layout.addWidget(close_button)

    def populate_table(self):
        """
        Populate the table with mask IDs and surface areas.
        """
        if not self.image_mask or not self.image_mask.masks:
            self.table.setRowCount(0)
            return

        # Calculate surface areas and add rows
        for idx, mask in enumerate(self.image_mask.masks):
            if isinstance(mask, list):
                mask = np.array(mask, dtype=np.int32)
            mask_id = f"{self.image_path}_mask_{idx + 1}"
            surface_area = cv2.contourArea(mask.astype(int))  # Calculate surface area

            # Add row to table
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(mask_id))
            self.table.setItem(row, 1, QTableWidgetItem(f"{surface_area:.2f}"))

    def refresh_table(self, image_path, image_mask):
        """
        Refresh the table with the masks of the current image.
        """
        self.image_path = image_path
        self.image_mask = image_mask
        self.table.setRowCount(0)  # Clear the table
        self.populate_table()  # Repopulate the table
