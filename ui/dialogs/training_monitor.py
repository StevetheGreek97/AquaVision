
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
import pyqtgraph as pg

from services.logger import get_logger

logger = get_logger(__name__)

class TrainingMonitorCMD(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = None
        self.setWindowTitle("📉 Training Monitor")
        self.setMinimumSize(600, 400)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)

        self.stop_btn = QPushButton("🛑 Stop Training")
        self.stop_btn.clicked.connect(self._on_stop)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text_area)
        layout.addWidget(self.stop_btn)

        self._stop_requested = False
        self.stop_callback = None

    def append_log(self, message):
        self.text_area.append(message)

    def _on_stop(self):
        self._stop_requested = True
        if self.stop_callback:
            self.stop_callback()
        self.append_log("Training stopped by user.")

    def set_stop_callback(self, callback):
        self.stop_callback = callback

    # training_monitor.py
    def closeEvent(self, event):
        """
        When user presses 'X'. Stop training and hide dialog safely.
        """
        if not self._stop_requested:
            self._on_stop()

        self.hide()
        event.ignore()  # Do not destroy the dialog yet

        
    def set_thread(self, thread):
        self.thread = thread





class TrainingMonitorcmd(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📉 Training Monitor")
        self.setMinimumSize(800, 500)

        self.plot_widget = pg.PlotWidget(title="Training Metrics")
        self.plot_widget.addLegend()
        self.plot_widget.setLabel('left', 'Loss')
        self.plot_widget.setLabel('bottom', 'Epoch')
        self.plot_widget.showGrid(x=True, y=True)

        self.stop_btn = QPushButton("🛑 Stop Training")
        self.stop_btn.clicked.connect(self._on_stop)

        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_widget)
        layout.addWidget(self.stop_btn)

        self._stop_requested = False
        self.stop_callback = None

        # Curves for each metric
        self.epoch_data = []
        self.metrics = {
            'box_loss': {'curve': pg.PlotDataItem(pen='r'), 'data': []},
            'seg_loss': {'curve': pg.PlotDataItem(pen='g'), 'data': []},
            'cls_loss': {'curve': pg.PlotDataItem(pen='b'), 'data': []},
            'dfl_loss': {'curve': pg.PlotDataItem(pen='y'), 'data': []},
        }

        for metric in self.metrics.values():
            self.plot_widget.addItem(metric['curve'])

    def update_metrics(self, epoch, box_loss, seg_loss, cls_loss, dfl_loss):
        self.epoch_data.append(epoch)
        self.metrics['box_loss']['data'].append(box_loss)
        self.metrics['seg_loss']['data'].append(seg_loss)
        self.metrics['cls_loss']['data'].append(cls_loss)
        self.metrics['dfl_loss']['data'].append(dfl_loss)

        for name, metric in self.metrics.items():
            metric['curve'].setData(self.epoch_data, metric['data'])

    def _on_stop(self):
        self._stop_requested = True
        if self.stop_callback:
            self.stop_callback()

    def set_stop_callback(self, callback):
        self.stop_callback = callback

    def closeEvent(self, event):
        if not self._stop_requested:
            self._on_stop()
        self.hide()
        event.ignore()

    def set_thread(self, thread):
        self.thread = thread



import os
import pandas as pd
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QTextEdit
from PyQt6.QtCore import QTimer
import pyqtgraph as pg

class TrainingMonitor(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📉 Training Monitor")
        self.setMinimumSize(1000, 700)
        self.thread = None
        self.results_csv = None
        self._stop_requested = False
        self.stop_callback = None

        # Metrics plot
        self.metrics_plot = pg.PlotWidget(title="📊 Loss Metrics (box, seg, cls, dfl)")
        self.metrics_plot.setLabel('left', 'Loss')
        self.metrics_plot.setLabel('bottom', 'Epoch')
        self.metrics_plot.addLegend()
        self.metrics_plot.showGrid(x=True, y=True)

        # Train/Val plot
        self.trainval_plot = pg.PlotWidget(title="📈 Train/Validation Scores")
        self.trainval_plot.setLabel('left', 'Score')
        self.trainval_plot.setLabel('bottom', 'Epoch')
        self.trainval_plot.addLegend()
        self.trainval_plot.showGrid(x=True, y=True)

        # Log view
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Training logs will appear here...")

        # Stop button
        self.stop_btn = QPushButton("🛑 Stop Training")
        self.stop_btn.clicked.connect(self._on_stop)

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.metrics_plot)
        layout.addWidget(self.trainval_plot)
        layout.addWidget(self.log_view)
        layout.addWidget(self.stop_btn)

        # Timer to monitor results.csv
        self.timer = QTimer()
        self.timer.setInterval(10000)  # Check every 10 sec
        self.timer.timeout.connect(self._update_from_csv)
        self.timer.start()

    def _update_from_csv(self):
        if not self.results_csv or not os.path.exists(self.results_csv):
            logger.debug("Waiting for training results file %s", self.results_csv)
            return

        try:
            df = pd.read_csv(self.results_csv)
            if df.empty:
                return

            logger.debug("Read %d epoch row(s) from %s", len(df), self.results_csv)

            epochs = pd.to_numeric(df["epoch"], errors="coerce")

            self.metrics_plot.clear()
            self.trainval_plot.clear()

            # Loss Metrics
            self._plot_metric(self.metrics_plot, epochs, df.get("train/box_loss"), 'box_loss', 'r')
            self._plot_metric(self.metrics_plot, epochs, df.get("train/seg_loss"), 'seg_loss', 'g')
            self._plot_metric(self.metrics_plot, epochs, df.get("train/cls_loss"), 'cls_loss', 'b')
            self._plot_metric(self.metrics_plot, epochs, df.get("train/dfl_loss"), 'dfl_loss', 'y')

            # Eval Metrics
            self._plot_metric(self.trainval_plot, epochs, df.get("metrics/precision(B)"), 'precision', 'c')
            self._plot_metric(self.trainval_plot, epochs, df.get("metrics/recall(B)"), 'recall', 'm')
            self._plot_metric(self.trainval_plot, epochs, df.get("metrics/mAP50(B)"), 'mAP50', 'w')
            self._plot_metric(self.trainval_plot, epochs, df.get("metrics/mAP50-95(B)"), 'mAP50-95', 'orange')

        except Exception as e:
            logger.warning("Failed to read training results %s: %s", self.results_csv, e)

    def _plot_metric(self, widget, x, y, label, color):
        if y is not None and not y.isna().all() and len(x) > 0:
            for item in widget.listDataItems():
                if item.name() == label:
                    widget.removeItem(item)

            plot_item = pg.PlotDataItem(x, y, pen=pg.mkPen(color=color, width=2), name=label)
            widget.addItem(plot_item)
            widget.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    def append_log(self, message: str):
        self.log_view.append(message)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def set_thread(self, thread):
        self.thread = thread

    def set_stop_callback(self, callback):
        self.stop_callback = callback

    def _on_stop(self):
        self._stop_requested = True
        self.timer.stop()

        if self.stop_callback:
            try:
                self.stop_callback()
            except RuntimeError as e:
                logger.debug("Stop callback skipped (worker already deleted): %s", e)

        self.append_log("🛑 Training stopped manually.")


    def closeEvent(self, event):
        self._on_stop()

        if self.thread and self.thread.isRunning():
            logger.debug("Waiting for training thread to stop")
            self.thread.quit()
            self.thread.wait()

        self.timer.stop()
        self.hide()
        event.ignore()
