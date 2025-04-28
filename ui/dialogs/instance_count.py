import os
import pyqtgraph as pg
from PyQt6.QtWidgets import QDockWidget, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
import random

class MaskStatisticsDock(QDockWidget):
    def __init__(self, parent):
        super().__init__("Annotation Statistics", parent)
        self.parent = parent
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.setWidget(self.widget)

        # Setup pyqtgraph PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')  # White background
        self.layout.addWidget(self.plot_widget)

        # Customize plot
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Instance Count')
        self.plot_widget.setLabel('bottom', 'Class Name')

        self.bars = []
        self.class_names = []
        self.counts = []



        self.refresh_plot()

    def refresh_plot(self):
        """
        Refresh the bar plot using class colors from the database.
        """
        self.plot_widget.clear()
        self.bars = []
        self.class_names = []
        self.counts = []

        try:
            query = "SELECT class_name, COUNT(*) FROM masks GROUP BY class_name"
            results = self.parent.state_manager.mask_manager.db.fetch_all(query)

            if results:
                self.class_names = [row[0] for row in results]
                self.counts = [row[1] for row in results]

                x = list(range(len(self.class_names)))

                for i, (cls, cnt) in enumerate(zip(self.class_names, self.counts)):
                    # ✅ Fetch the real color from the class database
                    qcolor = self.parent.state_manager.class_manager.get_class_color(cls)
                    brush_color = pg.mkBrush(qcolor.red(), qcolor.green(), qcolor.blue())

                    bar = pg.BarGraphItem(x=[i], height=[cnt], width=0.6, brush=brush_color)
                    self.plot_widget.addItem(bar)
                    self.bars.append((bar, cls, cnt))

                # X Axis Labels
                axis = self.plot_widget.getAxis('bottom')
                axis.setTicks([[(i, name) for i, name in enumerate(self.class_names)]])

        except Exception as e:
            print(f"❌ Error fetching mask statistics: {e}")
