from PyQt6.QtWidgets import QMainWindow, QWidget, QFileDialog, QHBoxLayout, QColorDialog, QInputDialog,QApplication
from ui.elements.image_display import ImageDisplay
from ui.elements.menubar import MenuBar
from ui.elements.sidebar import Sidebar
from ui.dialogs.inference_dialog import InferenceDialog
from ui.dialogs.table import MaskResultsDialog
import os
from PyQt6.QtCore import Qt, QEvent
from core.state import StateManager  
from core.inference_manager import  InferenceManager
from PyQt6.QtCore import pyqtSignal
from core.exporters.yolo_exporter import YOLOExporter
from core.managers.tool_manager import ToolManager
from services.file_handlers import loader
from services.logger import logger, log_memory_usage

class MainApp(QMainWindow):
    image_changed = pyqtSignal(str, object)
    #masks_updated = pyqtSignal()
    """
    Main application window.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AquaVision")
        self.resize(1000, 600)
        #self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.models_dir = "models/yolo"
        self.sam_dir = "models/sam"
        self.current_model_path = None

        # Initialize StateManager
        self.state_manager = StateManager()

        # Initialize InferenceManager
        self.inference_manager = None
        self.tool_manager = ToolManager(self)

        # Create widgets
        self.image_display = ImageDisplay(self)
        self.sidebar = Sidebar(self)
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        

        # Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.addWidget(self.sidebar, stretch=1)
        layout.addWidget(self.image_display, stretch=4)
        QApplication.instance().installEventFilter(self)

    def load_images(self):
        """
        Open a directory dialog to select a folder and load all images within it.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        image_paths = loader(folder_path)
        #print(image_paths)
            
        if image_paths:
            self.state_manager.set_image_paths(image_paths)
            current_image_path = self.state_manager.current_image_path
            
            if current_image_path:
                print(f"Displaying initial image from folder: {current_image_path}")  # Debug
                self.image_display.display_image(current_image_path)
                #print(self.state_manager.current_masks)

        else:
            logger.info("No valid images found in the selected folder.")

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
            # Emit signal with the new image path and its mask data
            #image_mask = self.state_manager.image_masks.get(previous_image_path)
            #self.image_changed.emit(previous_image_path, image_mask)
            #self.print_current_state()
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
                    self.current_model_path, self.state_manager.image_paths
                )

    def closeEvent(self, event):
        if hasattr(self, 'export_thread') and self.export_thread.isRunning():
            print("Stopping export thread...")
            self.export_thread.stop()
            self.export_thread.wait()
        event.accept()

    def show_results(self):
        """
        Show a table with mask IDs and surface areas for the current image.
        """
        current_image_path = self.state_manager.current_image_path
        if not current_image_path:
            print("No image is currently loaded.")
            return

        image_mask = self.state_manager.current_masks
        if not image_mask:
            print(f"No masks found for current image: {current_image_path}")
            return

        # Open the results dialog or refresh it if already open
        if hasattr(self, 'results_dialog') and self.results_dialog.isVisible():
            print("Refreshing the results dialog...")
            self.results_dialog.refresh_table(current_image_path)  # Refresh the table
        else:
            print("Opening a new results dialog...")
            self.results_dialog = MaskResultsDialog(self)
            self.results_dialog.masks_selected.connect(self.image_display.set_highlighted_masks)
            self.results_dialog.show()

    def _export_results(self):
        exporter = YOLOExporter(self)
        exporter.export_all_annotations()

  

    def eventFilter(self, source, event):
        """
        Handle global key events for navigation and deletion.
        """
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Delete:
                print("Delete key pressed")
                self.image_display.delete_selected_masks()
                self.show_results()  # Update results
                return True
            elif event.key() == Qt.Key.Key_Right:  # Navigate to the next image
                self.next_image()
                return True
            elif event.key() == Qt.Key.Key_Left:  # Navigate to the previous image
                self.previous_image()
                return True

        return super().eventFilter(source, event)







