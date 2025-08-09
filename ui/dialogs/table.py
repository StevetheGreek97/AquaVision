from PyQt6.QtWidgets import (
    QComboBox, QDockWidget, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QLineEdit, QLabel, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QBrush, QPixmap, QIcon

class MaskResultsDock(QDockWidget):
    masks_selected = pyqtSignal(list)

    def __init__(self, parent):
        super().__init__("Annotations", parent)
        self.parent = parent
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Throttle/Coalesce refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._populate_table_impl)

        # --- Root container
        self.card = QWidget()
        self.card_layout = QVBoxLayout(self.card)
        self.card.setObjectName("DockCard")
        self.card_layout.setContentsMargins(10, 10, 10, 10)
        self.card_layout.setSpacing(8)
        self.setWidget(self.card)

        # --- Toolbar (filter + class filter)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search = QLineEdit(placeholderText="Search…")
        self.search.textChanged.connect(self.apply_filters)
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(160)

        self.class_filter = QComboBox()
        self.class_filter.addItem("All classes")
        self.class_filter.currentIndexChanged.connect(self.apply_filters)

        toolbar.addWidget(self.search, 2)
        toolbar.addWidget(self.class_filter, 1)
        self.card_layout.addLayout(toolbar)

        # --- Table
        self.table = QTableWidget(self.card)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Image Name", "Mask ID", "Surface Area", "Class"])
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.card_layout.addWidget(self.table)

        # --- Status line
        self.status = QLabel("0 rows")
        self.status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_layout.addWidget(self.status)

        # Signals (use throttled refresh)
        self.parent.state_manager.image_changed.connect(self.refresh_table)
        self.parent.state_manager.masks_updated.connect(self.refresh_table)

        # Dock settings
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self._apply_styles()

    # ------------------------------ Public refresh API (throttled) ----------
    def refresh_table(self, *_, delay_ms: int = 50):
        # Coalesce rapid updates into one table rebuild
        self._refresh_timer.start(delay_ms)

    # ------------------------------ Populate / Refresh (impl) ---------------
    def _populate_table_impl(self):
        selected_ids = self.get_current_selected_ids()

        self._refresh_class_filter()

        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)

            image_name = self.parent.state_manager.current_image_name
            if not image_name:
                self.update_status(0)
                self.table.setSortingEnabled(True)
                self.table.blockSignals(False)
                return

            masks = self.parent.state_manager.mask_manager.load_masks(image_name)

            for mask_id, mask, class_name, surface_area in masks:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self._set_item(row, 0, image_name, editable=False)
                self._set_item(row, 1, str(mask_id), editable=False)
                self._set_item(row, 2, f"{(surface_area or 0):.2f}", editable=False)
                self._set_class_cell(row, 3, class_name)

            # Resize columns
            for col in (0, 1, 2):
                self.table.resizeColumnToContents(col)

        finally:
            self.table.blockSignals(False)
            self.table.setSortingEnabled(True)

        self.restore_selected_ids(selected_ids)
        self.apply_filters()

    # ------------------------------ Helpers ---------------------------------
    def _set_item(self, row, column, text, editable=True, color=None):
        item = QTableWidgetItem(text)
        if color:
            item.setForeground(QBrush(color))
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if column in (1, 2):
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, column, item)

    def _make_color_icon(self, qcolor, size=12):
        pm = QPixmap(size, size)
        pm.fill(qcolor)
        return QIcon(pm)

    def _set_class_cell(self, row, column, current_class):
        combo = QComboBox()
        combo.setProperty("tableCombo", True)

        class_names = self.parent.state_manager.class_manager.get_all_class_names()
        for class_name in class_names:
            color = self.parent.state_manager.class_manager.get_class_color(class_name)
            combo.addItem(self._make_color_icon(color), class_name)

        combo.setCurrentText(current_class)

        def on_class_changed(new_class):
            mask_id = int(self.table.item(row, 1).text())
            image_name = self.table.item(row, 0).text()
            self.parent.state_manager.mask_manager.rename_mask(image_name, mask_id, new_class)
            # Single overlay/stat refresh is coalesced by MainApp/InferenceManager
            self.parent.image_display.refresh_masks()
            if hasattr(self.parent, 'statistics') and self.parent.statistics.isVisible():
                self.parent.statistics.refresh_plot()

        combo.currentTextChanged.connect(on_class_changed)
        self.table.setCellWidget(row, column, combo)

    def _refresh_class_filter(self):
        current = self.class_filter.currentText() if self.class_filter.count() else "All classes"
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("All classes")
        for name in self.parent.state_manager.class_manager.get_all_class_names():
            self.class_filter.addItem(name)
        idx = self.class_filter.findText(current)
        self.class_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.class_filter.blockSignals(False)

    def get_current_selected_ids(self):
        ids = set()
        for item in self.table.selectedItems():
            if item.column() == 1:
                ids.add(item.text())
        return ids

    def restore_selected_ids(self, selected_ids):
        self.table.blockSignals(True)
        try:
            for row in range(self.table.rowCount()):
                mask_id = self.table.item(row, 1).text()
                if mask_id in selected_ids:
                    self.table.selectRow(row)
        finally:
            self.table.blockSignals(False)

    def on_selection_changed(self):
        rows = {i.row() for i in self.table.selectedIndexes()}
        selected_rows = []
        for row in rows:
            row_data = {
                "image_name": self.table.item(row, 0).text(),
                "mask_id": self.table.item(row, 1).text(),
                "class": self._current_class_text(row),
            }
            selected_rows.append(row_data)
        self.masks_selected.emit(selected_rows)

    def _current_class_text(self, row):
        w = self.table.cellWidget(row, 3)
        return w.currentText() if isinstance(w, QComboBox) else self.table.item(row, 3).text()

    def apply_filters(self):
        text = self.search.text().strip().lower()
        cls = self.class_filter.currentText()

        visible = 0
        for row in range(self.table.rowCount()):
            img = self.table.item(row, 0).text().lower()
            mask_id = self.table.item(row, 1).text().lower()
            area = self.table.item(row, 2).text().lower()
            klass = self._current_class_text(row)

            matches_text = (text in img) or (text in mask_id) or (text in area) or (text in klass.lower())
            matches_class = (cls == "All classes") or (klass == cls)

            show = (matches_text and matches_class)
            self.table.setRowHidden(row, not show)
            if show:
                visible += 1

        self.update_status(visible)

    def update_status(self, visible_count=None):
        total = self.table.rowCount()
        if visible_count is None:
            visible_count = sum(not self.table.isRowHidden(r) for r in range(total))
        self.status.setText(f"{visible_count} / {total} rows")

    def _apply_styles(self):
        self.setStyleSheet("""
        /* Card inside the dock */
        QWidget#DockCard {
            background-color: palette(Base);
            border: 1px solid palette(Mid);
            border-radius: 12px;
        }

        /* Menus */
        QMenu {
            background-color: palette(Base);
            color: palette(Text);
            border: 1px solid palette(Mid);
            padding: 4px 0;
        }
        QMenu::item { padding: 6px 14px; }
        QMenu::item:selected {
            background-color: palette(Highlight);
            color: palette(HighlightedText);
        }
        QMenu::separator {
            height: 1px; margin: 4px 8px;
            background-color: palette(Mid);
        }

        /* Tool buttons */
        QToolButton {
            border: 1px solid palette(Mid);
            border-radius: 8px;
            padding: 6px 8px;
            background-color: palette(Button);
            color: palette(ButtonText);
        }
        QToolButton:hover { background-color: palette(Midlight); }

        /* ComboBoxes (including cell editors) */
        QComboBox {
            border: 1px solid palette(Mid);
            border-radius: 8px;
            padding: 6px 10px;
            background-color: palette(Base);
            color: palette(Text);
        }
        QComboBox:hover { background-color: palette(AlternateBase); }
        QComboBox QAbstractItemView, QComboBox QAbstractItemView::viewport {
            background-color: palette(Base);
            color: palette(Text);
            border: 1px solid palette(Mid);
            outline: none;
        }
        QComboBox QAbstractItemView::item { padding: 6px 10px; }
        QComboBox QAbstractItemView::item:selected {
            background-color: palette(Highlight);
            color: palette(HighlightedText);
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: 1px solid palette(Mid);
            background-color: palette(Midlight);
        }

        /* Inputs */
        QLineEdit {
            border: 1px solid palette(Mid);
            border-radius: 10px;
            padding: 6px 10px;
            background-color: palette(Base);
            color: palette(Text);
        }
        QLineEdit:focus {
            border: 1px solid palette(Highlight);
            background-color: palette(AlternateBase);
        }

        /* Table + viewport (prevents black table in light mode) */
        QTableWidget, QTableView, QAbstractItemView {
            background-color: palette(Base);
            color: palette(Text);
            selection-background-color: palette(Highlight);
            selection-color: palette(HighlightedText);
            alternate-background-color: palette(AlternateBase);
            gridline-color: palette(Mid);
        }
        QHeaderView::section {
            background-color: palette(Button);
            color: palette(ButtonText);
            border: 0px;
            padding: 4px 6px;
        }

        /* Tiny table combos */
        QComboBox[tableCombo="true"] { padding: 2px 8px; }

        QWidget { font-size: 12.5px; }
        """)
