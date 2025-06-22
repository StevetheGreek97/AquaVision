import os
import pyqtgraph as pg
from PyQt6.QtWidgets import QDockWidget, QVBoxLayout, QWidget, QTabWidget
from PyQt6.QtCore import Qt


class MaskStatisticsDock(QDockWidget):
    def __init__(self, parent):
        super().__init__("Annotation Statistics", parent)
        self.parent = parent
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.setWidget(self.widget)

        # Tabbed layout
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Tab 1: All annotations
        self.all_plot_widget = pg.PlotWidget()
        self.all_plot_widget.setBackground('w')
        self.all_plot_widget.showGrid(x=True, y=True)
        self.all_plot_widget.setLabel('left', 'Instance Count')
        self.all_plot_widget.setLabel('bottom', 'Class Name')
        self.tabs.addTab(self.all_plot_widget, "All Images")

        # Tab 2: Current image annotations
        self.current_plot_widget = pg.PlotWidget()
        self.current_plot_widget.setBackground('w')
        self.current_plot_widget.showGrid(x=True, y=True)
        self.current_plot_widget.setLabel('left', 'Instance Count')
        self.current_plot_widget.setLabel('bottom', 'Class Name')
        self.tabs.addTab(self.current_plot_widget, "Current Image")

        self.refresh_plot()

    def refresh_plot(self):
        """
        Refresh both the 'All Images' and 'Current Image' tabs.
        """
        self._refresh_tab(
            self.all_plot_widget,
            query="SELECT class_name, COUNT(*) FROM masks GROUP BY class_name"
        )

        current_image = self.parent.state_manager.current_image_name
        if current_image:
            self._refresh_tab(
                self.current_plot_widget,
                query="SELECT class_name, COUNT(*) FROM masks WHERE image_name = ? GROUP BY class_name",
                params=(current_image,)
            )
        else:
            self.current_plot_widget.clear()

    def _refresh_tab(self, plot_widget, query, params=()):
        """
        Helper to populate a given plot with annotation statistics.
        """
        plot_widget.clear()

        try:
            results = self.parent.state_manager.mask_manager.db.fetch_all(query, params)
            if not results:
                return

            class_names = [row[0] for row in results]
            counts = [row[1] for row in results]
            x = list(range(len(class_names)))

            for i, (cls, cnt) in enumerate(zip(class_names, counts)):
                qcolor = self.parent.state_manager.class_manager.get_class_color(cls)
                brush_color = pg.mkBrush(qcolor.red(), qcolor.green(), qcolor.blue())
                bar = pg.BarGraphItem(x=[i], height=[cnt], width=0.6, brush=brush_color)
                plot_widget.addItem(bar)

            axis = plot_widget.getAxis('bottom')
            axis.setTicks([[(i, name) for i, name in enumerate(class_names)]])
        except Exception as e:
            print(f"❌ Error fetching statistics: {e}")
