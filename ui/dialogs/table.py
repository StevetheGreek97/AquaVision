# ui/dialogs/table.py

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSizePolicy,
    QTableView, QComboBox, QAbstractItemView, QStyledItemDelegate
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QModelIndex, QSortFilterProxyModel
from PyQt6.QtGui import QIcon, QPixmap, QColor

import time
from contextlib import contextmanager

# --- Back-compat shim for code expecting QTableWidget.selectedItems() ----
class _FakeItem:
    """Minimal stand-in for QTableWidgetItem with column() and text()."""
    def __init__(self, col: int, text: str):
        self._col = col
        self._text = text
    def column(self) -> int:
        return self._col
    def text(self) -> str:
        return self._text

from PyQt6.QtWidgets import QTableView
class SelectionView(QTableView):
    """
    QTableView with a back-compat .selectedItems(), .rowCount(), and .item()
    so existing QTableWidget-style callers keep working.
    We only really need col=1 (Mask ID), but item() works for any column.
    """
    def __init__(self, dock, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dock = dock  # access to _proxy and _model

    # --- Back-compat: QTableWidget.selectedItems() ---
    def selectedItems(self):
        items = []
        sel = self.selectionModel().selectedRows()  # indexes in proxy
        for proxy_idx in sel:
            src_idx = self._dock._proxy.mapToSource(proxy_idx)
            row = self._dock._model.row_at(src_idx.row())
            items.append(_FakeItem(1, str(row.mask_id)))
        return items

    # --- Back-compat: QTableWidget.rowCount() ---
    def rowCount(self):
        m = self.model()
        return m.rowCount() if m is not None else 0

    # --- Back-compat: QTableWidget.item(row, col) ---
    def item(self, row: int, column: int):
        m = self.model()
        if m is None or row < 0 or row >= m.rowCount():
            return None
        idx = m.index(row, column)
        # fetch display data from proxy model (since view is using proxy)
        val = m.data(idx, Qt.ItemDataRole.DisplayRole)
        return _FakeItem(column, "" if val is None else str(val))

# ----------------------------- tiny timing helper -----------------------------
@contextmanager
def _t(section, bucket: dict):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        bucket[section] = bucket.get(section, 0.0) + (time.perf_counter() - t0)


# ----------------------------- Table Model -----------------------------------
class MaskTableModelData:
    """
    Simple row container to keep the code readable.
    """
    __slots__ = ("image_name", "mask_id", "surface_area", "klass")

    def __init__(self, image_name: str, mask_id: int, surface_area: float | None, klass: str | None):
        self.image_name = image_name
        self.mask_id = int(mask_id)
        self.surface_area = 0.0 if surface_area is None else float(surface_area)
        self.klass = "" if klass is None else str(klass)


from PyQt6.QtCore import QAbstractTableModel, QVariant


class MaskTableModel(QAbstractTableModel):
    """
    Lightweight model for annotations.
    Edits are allowed only for the 'Class' column.
    """
    classChanged = pyqtSignal(str, int, str)  # image_name, mask_id, new_class

    HEADERS = ["Image Name", "Mask ID", "Surface Area", "Class"]

    COL_IMAGE = 0
    COL_ID = 1
    COL_AREA = 2
    COL_CLASS = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[MaskTableModelData] = []

    # ---------------- required overrides -----------------
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 4

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return section + 1

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        row = self._rows[r]

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if c == self.COL_IMAGE:
                return row.image_name
            elif c == self.COL_ID:
                return str(row.mask_id)
            elif c == self.COL_AREA:
                return f"{row.surface_area:.2f}"
            elif c == self.COL_CLASS:
                return row.klass

        # Center numeric columns visually
        if role == Qt.ItemDataRole.TextAlignmentRole and c in (self.COL_ID, self.COL_AREA):
            return int(Qt.AlignmentFlag.AlignCenter)

        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if index.column() == self.COL_CLASS:
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        if index.column() != self.COL_CLASS:
            return False

        r = index.row()
        row = self._rows[r]
        new_class = str(value)
        if row.klass == new_class:
            return True

        row.klass = new_class
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        # Notify listeners (dock) to persist to DB & refresh overlays/plots.
        self.classChanged.emit(row.image_name, int(row.mask_id), new_class)
        return True

    # ---------------- convenience API -------------------
    def set_rows(self, rows: list[MaskTableModelData]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def row_at(self, row_idx: int) -> MaskTableModelData:
        return self._rows[row_idx]


# ----------------------------- Filter/Sort Proxy ------------------------------
class MaskFilterProxy(QSortFilterProxyModel):
    """
    Text search across all columns + class filter.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._class = None  # None => all classes, else exact match
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def setSearchText(self, text: str):
        t = (text or "").strip()
        if t == self._text:
            return
        self._text = t
        self.invalidateFilter()

    def setClassFilter(self, klass: str | None):
        v = None if (not klass or klass == "All classes") else klass
        if v == self._class:
            return
        self._class = v
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model: MaskTableModel = self.sourceModel()  # type: ignore
        idx_img = model.index(source_row, MaskTableModel.COL_IMAGE, source_parent)
        idx_id = model.index(source_row, MaskTableModel.COL_ID, source_parent)
        idx_area = model.index(source_row, MaskTableModel.COL_AREA, source_parent)
        idx_class = model.index(source_row, MaskTableModel.COL_CLASS, source_parent)

        # Class filter
        if self._class is not None:
            klass = model.data(idx_class, Qt.ItemDataRole.DisplayRole) or ""
            if klass != self._class:
                return False

        # Text search across all textual columns
        if not self._text:
            return True

        txt = self._text.lower()
        vals = [
            (model.data(idx_img) or "").lower(),
            (model.data(idx_id) or "").lower(),
            (model.data(idx_area) or "").lower(),
            (model.data(idx_class) or "").lower(),
        ]
        return any(txt in v for v in vals)


# ----------------------------- delegate for Class col -------------------------
class ClassComboDelegate(QStyledItemDelegate):
    """
    Provides a QComboBox editor only while editing the 'Class' column.
    No per-row widget overhead.
    """
    def __init__(self, class_manager, get_icon_cache, parent=None):
        super().__init__(parent)
        self.cm = class_manager
        self._get_icon_cache = get_icon_cache  # callable — always returns the dock's current cache

    def createEditor(self, parent, option, index: QModelIndex):
        # Only column 3 gets a combo editor
        if index.column() != MaskTableModel.COL_CLASS:
            return super().createEditor(parent, option, index)

        combo = QComboBox(parent)
        icon_cache = self._get_icon_cache()
        for cls in self.cm.get_all_class_names():
            combo.addItem(icon_cache.get(cls), cls)
        QTimer.singleShot(0, combo.showPopup)
        return combo

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            current = index.data(Qt.ItemDataRole.EditRole) or index.data()
            i = editor.findText(current)
            editor.setCurrentIndex(max(i, 0))
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
        else:
            super().setModelData(editor, model, index)


# --------------------------------- main dock ----------------------------------
class MaskResultsDock(QDockWidget):
    masks_selected = pyqtSignal(list)  # list of dicts with image_name, mask_id, class

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

        # --- Table (Model/View)
        self.table = SelectionView(self, self.card) 
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setWordWrap(False)                           # NEW
        self.table.verticalHeader().setDefaultSectionSize(22)  
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        # Model + Proxy
        self._model = MaskTableModel(self.table)
        self._proxy = MaskFilterProxy(self.table)
        self._proxy.setSourceModel(self._model)
        self.table.setModel(self._proxy)

        # Delegate for column 3 (Class) — uses a lambda so it always reads the current cache
        self._class_icon_cache = self._build_class_icon_cache()
        self.table.setItemDelegateForColumn(
            MaskTableModel.COL_CLASS,
            ClassComboDelegate(
                class_manager=self.parent.state_manager.class_manager,
                get_icon_cache=lambda: self._class_icon_cache,
                parent=self.table
            )
        )

        # Persist edits coming from the model
        self._model.classChanged.connect(self._commit_class_change)

        # Selection signal
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

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

    # ------------------------------ Helpers / setup ---------------------------
    def _build_class_icon_cache(self):
        cache = {}
        cm = self.parent.state_manager.class_manager
        for cls in cm.get_all_class_names():
            qcol = cm.get_class_color(cls)
            pm = QPixmap(12, 12)
            pm.fill(qcol if isinstance(qcol, QColor) else QColor(qcol))
            cache[cls] = QIcon(pm)
        return cache

    def _commit_class_change(self, image_name: str, mask_id: int, new_class: str):
        # Persist to DB
        self.parent.state_manager.mask_manager.rename_mask(image_name, mask_id, new_class)
        # Light refreshes
        self.parent.image_display.refresh_masks()
        if hasattr(self.parent, 'statistics') and self.parent.statistics.isVisible():
            self.parent.statistics.refresh_plot()

    # ------------------------------ Public refresh API (throttled) -----------
    def refresh_table(self, *_, delay_ms: int = 50):
        self._refresh_timer.start(delay_ms)

    # ------------------------------ Populate / Refresh (impl) ----------------
    def _populate_table_impl(self):
        stats = {}
        with _t("total", stats):

            selected_ids = self.get_current_selected_mask_ids()

            with _t("class_filter_refresh", stats):
                self._refresh_class_filter()

            self.table.setUpdatesEnabled(False)
            try:
                image_name = self.parent.state_manager.current_image_name
                if not image_name:
                    self._model.set_rows([])
                    self.update_status(0)
                    return

                with _t("load_masks", stats):
                    masks = self.parent.state_manager.mask_manager.load_masks(image_name)
                    # expected tuples: (mask_id, _mask, class_name, surface_area)

                with _t("build_rows", stats):
                    rows = [MaskTableModelData(
                        image_name=image_name,
                        mask_id=mask_id,
                        surface_area=surface_area,
                        klass=class_name
                    ) for (mask_id, _mask, class_name, surface_area) in masks]
                    self._model.set_rows(rows)

                # Keep sort if user clicked a header previously
                # (QTableView + QSortFilterProxyModel handles this efficiently)

            finally:
                self.table.setUpdatesEnabled(True)

            with _t("restore_selection", stats):
                self.restore_selected_mask_ids(selected_ids)

            with _t("apply_filters", stats):
                self.apply_filters()

        ms = lambda k: stats.get(k, 0.0) * 1000.0
        print(
            "[MaskResultsDock] table refresh fast:\n"
            f"  total={ms('total'):.2f} ms\n"
            f"    class_filter_refresh={ms('class_filter_refresh'):.2f} ms\n"
            f"    load_masks={ms('load_masks'):.2f} ms\n"
            f"    build_rows={ms('build_rows'):.2f} ms\n"
            f"    restore_selection={ms('restore_selection'):.2f} ms\n"
            f"    apply_filters={ms('apply_filters'):.2f} ms"
        )

    # ------------------------------ Selection & filters -----------------------
    def _refresh_class_filter(self):
        self._class_icon_cache = self._build_class_icon_cache()
        current = self.class_filter.currentText() if self.class_filter.count() else "All classes"
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("All classes")
        for name in self.parent.state_manager.class_manager.get_all_class_names():
            self.class_filter.addItem(name)
        idx = self.class_filter.findText(current)
        self.class_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.class_filter.blockSignals(False)

    def get_current_selected_mask_ids(self) -> set[str]:
        ids: set[str] = set()
        sel = self.table.selectionModel().selectedRows()  # indexes in proxy
        for proxy_idx in sel:
            src_idx = self._proxy.mapToSource(proxy_idx)
            row = self._model.row_at(src_idx.row())
            ids.add(str(row.mask_id))
        return ids

    def restore_selected_mask_ids(self, selected_ids: set[str]):
        if not selected_ids:
            return
        self.table.selectionModel().clearSelection()
        # iterate all source rows and select those whose mask_id is in the set
        for src_row in range(self._model.rowCount()):
            row = self._model.row_at(src_row)
            if str(row.mask_id) in selected_ids:
                src_idx = self._model.index(src_row, 0)
                proxy_idx = self._proxy.mapFromSource(src_idx)
                if proxy_idx.isValid():
                    self.table.selectRow(proxy_idx.row())

    def on_selection_changed(self, *_):
        sel = self.table.selectionModel().selectedRows()
        selected_rows = []
        for proxy_idx in sel:
            src_idx = self._proxy.mapToSource(proxy_idx)
            row = self._model.row_at(src_idx.row())
            selected_rows.append({
                "image_name": row.image_name,
                "mask_id": str(row.mask_id),
                "class": row.klass,
            })
        self.masks_selected.emit(selected_rows)

    def apply_filters(self):
        t0 = time.perf_counter()

        text = self.search.text()
        klass = self.class_filter.currentText()

        self._proxy.setSearchText(text)
        self._proxy.setClassFilter(klass)

        self.update_status()
        print(
            f"[MaskResultsDock] apply_filters: {(time.perf_counter()-t0)*1000:.2f} ms  "
            f"(rows={self._model.rowCount()}, visible={self._proxy.rowCount()})"
        )

    def update_status(self):
        total = self._model.rowCount()
        visible = self._proxy.rowCount()
        self.status.setText(f"{visible} / {total} rows")

    # ------------------------------ Styles -----------------------------------
    def _apply_styles(self):
        self.setStyleSheet("""
        QWidget#DockCard {
            background-color: palette(Base);
            border: 1px solid palette(Mid);
            border-radius: 12px;
        }
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
        QToolButton {
            border: 1px solid palette(Mid);
            border-radius: 8px;
            padding: 6px 8px;
            background-color: palette(Button);
            color: palette(ButtonText);
        }
        QToolButton:hover { background-color: palette(Midlight); }
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
        QTableView, QAbstractItemView {
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
            border: 0;
            padding: 4px 6px;
        }
        QWidget { font-size: 12.5px; }
        """)
