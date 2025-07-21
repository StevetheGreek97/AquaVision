from PyQt6.QtWidgets import QMainWindow, QWidget, QFileDialog, QHBoxLayout,QApplication, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, QEvent, pyqtSignal
from ui.elements.image_display.image_display import ImageDisplay
from ui.elements.menubar import MenuBar
from ui.elements.sidebar import Sidebar
from ui.dialogs.inference_dialog import InferenceDialog
from ui.dialogs.table import MaskResultsDock
from ui.dialogs.instance_count import MaskStatisticsDock
from ui.elements.slider import ImageSlider
import os
from core.config import ProjectConfigManager
from PyQt6.QtGui import QIcon 
from core.state import StateManager  
from core.inference_manager import  InferenceManager
from core.exporters.yolo_exporter import YOLOExporter
from core.managers.tool_manager import ToolManager
from core.tools.auto_sam2 import Sam2Auto
import shutil
from services.file_handlers import loader, get_resource_path
from services.logger import logger, log_memory_usage
from ui.dialogs.export_dialog import ExportDialog  # Adjust path if needed
from core.exporters.yolo_exporter import YOLOExporter  # Already there
from ui.dialogs.training_dialog import TrainingDialog  # adjust if needed
# from core.exporters.coco_exporter import COCOExporter  # If you support COCO
# Modify popup_training_dialog in MainApp
from ui.dialogs.training_monitor import TrainingMonitor
from core.trainer.worker import TrainingWorker
from PyQt6.QtCore import QThread, QTimer


class MainApp(QMainWindow):
    image_changed = pyqtSignal(str, object)
    #masks_updated = pyqtSignal()
    """
    Main application window.
    """

    def __init__(self, db_path="masks.db"):
        super().__init__()
        self.setWindowTitle("SegmentME")
        self.resize(1000, 600)

        icon_path = get_resource_path("resources/icons/desktop.png")
        self.setWindowIcon(QIcon(icon_path))
        #self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.models_dir = get_resource_path("models/yolo")
        self.sam_dir = get_resource_path("models/sam")
        self.current_model_path = None
        # Initialize StateManager
    
        self.state_manager = StateManager(db_path=db_path)

        # Initialize InferenceManager
        self.inference_manager = None
        self.tool_manager = ToolManager(self)

        # Create widgets
        self.image_display = ImageDisplay(self)
        self.sidebar = Sidebar(self)
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.slider = ImageSlider(self)


        

        # Create main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)  # Horizontal layout

        # Create image container layout (Slider above ImageDisplay)
        image_layout = QVBoxLayout()
        image_layout.addWidget(self.slider)  # Add slider above
        image_layout.addWidget(self.image_display)  # Add image display

        # Add sidebar and image container to main layout
        main_layout.addWidget(self.sidebar, stretch=1)  # Sidebar on the left
        main_layout.addLayout(image_layout, stretch=4)  # Image section on the right

        #self.init_dock_widgets()


        self.state_manager.image_changed.connect(self.slider.update_slider)
        QApplication.instance().installEventFilter(self)


    def import_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images to Import", filter="Images (*.png *.jpg *.jpeg *.bmp *.tif)")
        if not files:
            return

        images_dir = self.config.get_images_dir()
        os.makedirs(images_dir, exist_ok=True)

        imported_count = 0
        for file in files:
            fname = os.path.basename(file)
            dest = os.path.join(images_dir, fname)
            if not os.path.exists(dest):
                shutil.copy(file, dest)
                imported_count += 1

        image_paths = loader(images_dir)
        self.state_manager.set_image_paths(image_paths)
        self.slider.set_image_count(len(image_paths))
        self.image_display.display_image(self.state_manager.current_image_path)

        QMessageBox.information(self, "Import Complete", f"✅ Imported {imported_count} images into your project.")


    def next_image(self):
        """
        Navigate to the next image and notify listeners.
        """
        next_image_path = self.state_manager.next_image()
        if next_image_path:
            if self.tool_manager.current_tool:
                self.tool_manager.current_tool.clear_temp_items()
            self.image_display.display_image(next_image_path)


            print(f"Current image: {self.state_manager.current_image_index + 1}/{len(self.state_manager.image_paths)}")
            # Emit signal with the new image path and its mask data
            #image_mask = self.state_manager.image_masks.get(next_image_path)
            #self.image_changed.emit(next_image_path, image_mask)
            #logger.info(self.print_current_state())
            log_memory_usage()
        else:
            logger.info("No next image available.")
            

    def previous_image(self):
        """
        Navigate to the previous image and notify listeners.
        """
        previous_image_path = self.state_manager.previous_image()
        if previous_image_path:
            if self.tool_manager.current_tool:
                self.tool_manager.current_tool.clear_temp_items()
            self.image_display.display_image(previous_image_path)

            print(f"Current image: {self.state_manager.current_image_index + 1}/{len(self.state_manager.image_paths)}")
        else:
            logger.info("No previous image available.")

    def popup_inference_dialog(self, dir, mode, display_text):
        """
        Open the inference dialog, select a model, and start inference.
        """
        print(f"Opening Inference Dialog with mode: {mode}, dir: {dir}")  # Debug

        if not self.state_manager.image_paths:
            print("No images loaded.")  # Debug
            return

        dialog = InferenceDialog(dir, self)
        if dialog.exec():


            threshold = dialog.get_threshold()
            selected_model = dialog.get_selected_model()
            print(f"Selected Model: {selected_model}")  # Debug

            if selected_model:
                self.current_model_path = os.path.join(dir, selected_model)
                print(f"Running Inference with model: {self.current_model_path}")  # Debug

                # Stop any ongoing inference before starting a new one
                if self.inference_manager:
                    self.inference_manager.stop_inference()

                # Initialize and start the inference
                self.inference_manager = InferenceManager(self, mode, display_text)
                self.inference_manager.run_inference(
                    self.current_model_path, self.state_manager.image_paths, threshold
                )      

    def closeEvent(self, event):
        if hasattr(self, 'export_thread') and self.export_thread.isRunning():
            print("Stopping export thread...")
            self.export_thread.stop()
            self.export_thread.wait()
        event.accept()

    def show_results(self):
        current_image_path = self.state_manager.current_image_path

        if not hasattr(self, 'annotations'):
            self.annotations = MaskResultsDock(self)
            self.annotations.masks_selected.connect(self.image_display.set_highlighted_masks)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.annotations)
        if not hasattr(self, 'statistics') or self.statistics is None:
            self.statistics = MaskStatisticsDock(self)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.statistics)
            self.state_manager.image_changed.connect(self.statistics.refresh_plot)
        
        print("Refreshing results and statistics...")
        self.annotations.refresh_table(current_image_path)
        self.statistics.refresh_plot()
        self.annotations.show()
        self.statistics.show()


    def _export_results(self):
        dialog = ExportDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()

 

            format = settings["format"]
            train = settings["train"]
            val = settings["val"]
            test = settings["test"]



            print(f"📊 Train: {train}%, Val: {val}%, Test: {test}%")

            if format == "yolo":
                exporter = YOLOExporter(self)
                exporter.export_all_annotations(train, val, test)
            elif format == "coco":
                # exporter = COCOExporter(self)
                # exporter.export(output_dir, train, val, test)
                QMessageBox.information(self, "Coming Soon", "COCO export not implemented yet.")
            else:
                QMessageBox.warning(self, "Unsupported Format", f"Export format '{format}' not supported.")


    

    def eventFilter(self, source, event):
        """
        Handle global key events for navigation and deletion.
        """
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Delete:
                print("Delete key pressed")
                self.image_display.delete_selected_masks()
                self.annotations.refresh_table(self.state_manager.current_image_path)
                self.show_results()  # Update results
                return True
            elif event.key() == Qt.Key.Key_Right:  # Navigate to the next image
                self.next_image()
                return True
            elif event.key() == Qt.Key.Key_Left:  # Navigate to the previous image
                self.previous_image()
                return True

        return super().eventFilter(source, event)

    def popup_training_dialog(self):
        dialog = TrainingDialog(self.project_root, self)
        if dialog.exec():
            settings = dialog.get_settings()

            # Keep references
            self.training_thread = QThread(self)
            self.training_worker = TrainingWorker(settings, self.project_root)
            self.training_worker.moveToThread(self.training_thread)

            self.training_monitor = TrainingMonitor(self)
            self.training_monitor.set_stop_callback(self.training_worker.stop)
            self.training_monitor.set_thread(self.training_thread)

            # Signals
            self.training_worker.log_signal.connect(self._handle_training_log)

            self.training_worker.finished_signal.connect(self.training_monitor.accept)
            self.training_worker.finished_signal.connect(self.training_worker.deleteLater)
            self.training_thread.finished.connect(self.training_thread.deleteLater)

            # Final cleanup
            def cleanup_monitor():
                if self.training_monitor.isVisible():
                    self.training_monitor.accept()
                self.training_monitor.deleteLater()
                self.training_worker = None
                self.training_thread = None
                self.training_monitor = None

            self.training_thread.finished.connect(cleanup_monitor)
            self.training_thread.started.connect(self.training_worker.run)

            self.training_thread.start()
            self.training_monitor.exec()




    def initialize_project(self, db_path):
        self.project_root = os.path.dirname(os.path.dirname(db_path))  # .aquavision/masks.db → project/
        self.config = ProjectConfigManager(self.project_root)

        # Load image paths from config
        images_dir = self.config.get_images_dir()

        if not os.path.exists(images_dir):
            reply = QMessageBox.question(self, "Images Folder Not Found",
                                        f"The folder '{images_dir}' does not exist.\nWould you like to locate it?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                folder = QFileDialog.getExistingDirectory(self, "Locate Images Folder")
                if folder:
                    relative = os.path.relpath(folder, self.project_root)
                    self.config.set_images_dir(relative)
                    images_dir = folder
                else:
                    return  # User canceled

        image_paths = loader(images_dir)
        if image_paths:
            self.state_manager.set_image_paths(image_paths)
            self.slider.set_image_count(len(image_paths))
            self.image_display.display_image(self.state_manager.current_image_path)
            QTimer.singleShot(0, self.image_display.fit_to_view)
        else:
            QMessageBox.information(self, "No Images", "No images found in the selected folder.")

    def _handle_training_log(self, log_text):
        # Optional: forward raw logs to console or logger
        print(log_text)

        # Try to extract metrics from YOLO training log
        from services.utils import extract_logging_path

        match = extract_logging_path(log_text)
        
        if match:
            
            print(f"Training log detected: {match}")

            if self.training_monitor:
                run_dir = os.path.join(self.project_root, match)
                
                results_csv = os.path.join(run_dir, "results.csv")


                self.training_monitor.results_csv = results_csv
   
            