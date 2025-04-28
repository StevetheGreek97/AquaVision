from PyQt6.QtWidgets import QDockWidget, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor
import cv2
import numpy as np

class MaskResultsDock(QDockWidget):
    masks_selected = pyqtSignal(list)

    def __init__(self, parent):
        super().__init__("Annotations", parent)
        self.parent = parent
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.table_widget = QWidget()
        self.layout = QVBoxLayout(self.table_widget)
        self.setWidget(self.table_widget)

        self.table = QTableWidget(self.table_widget)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Image Name", "Mask ID", "Surface Area", "Class"])
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        self.layout.addWidget(self.table)

        self.parent.state_manager.image_changed.connect(self.refresh_table)

        # Dock settings
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)

    def populate_table(self):
        """
        Populate or refresh the table while keeping selection.
        """
        selected_ids = self.get_current_selected_ids()

        self.table.setRowCount(0)
        masks = self.parent.state_manager.mask_manager.load_masks(self.parent.state_manager.current_image_name)
        image_name = self.parent.state_manager.current_image_name

        for mask_id, mask, class_name in masks:
            surface_area = cv2.contourArea(mask.astype(np.int32)) if mask is not None and len(mask) > 0 else 0
            color = self.parent.state_manager.class_manager.get_class_color(class_name)

            row = self.table.rowCount()
            self.table.insertRow(row)

            self._set_item(row, 0, image_name, editable=False)
            self._set_item(row, 1, str(mask_id), editable=False)
            self._set_item(row, 2, f"{surface_area:.2f}", editable=False)
            self._set_item(row, 3, class_name, editable=True, color=color)

        self.restore_selected_ids(selected_ids)

    def refresh_table(self, image_path):
        self.populate_table()

    def _set_item(self, row, column, text, editable=True, color=None):
        item = QTableWidgetItem(text)
        if color:
            item.setForeground(QBrush(color))
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, column, item)

    def get_current_selected_ids(self):
        """
        Save the currently selected mask IDs to restore later.
        """
        selected_ids = set()
        for item in self.table.selectedItems():
            if item.column() == 1:
                selected_ids.add(item.text())
        return selected_ids

    def restore_selected_ids(self, selected_ids):
        """
        Reselect the previously selected mask IDs after refresh.
        """
        for row in range(self.table.rowCount()):
            mask_id = self.table.item(row, 1).text()
            if mask_id in selected_ids:
                self.table.selectRow(row)

    def on_selection_changed(self):
        selected_rows = []
        for item in self.table.selectedItems():
            if item.column() == 1:
                row = item.row()
                row_data = {
                    "image_name": self.table.item(row, 0).text(),
                    "mask_id": self.table.item(row, 1).text(),
                    "class": self.table.item(row, 3).text()
                }
                selected_rows.append(row_data)

        self.masks_selected.emit(selected_rows)

    def on_item_changed(self, item):
        if item.column() == 3:  # Class column
            row = item.row()
            new_class_name = item.text()
            mask_id = int(self.table.item(row, 1).text())
            image_name = self.table.item(row, 0).text()
            self.parent.state_manager.mask_manager.rename_mask(image_name, mask_id, new_class_name)
