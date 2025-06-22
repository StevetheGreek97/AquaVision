from PyQt6.QtWidgets import QMainWindow, QWidget, QFileDialog, QHBoxLayout,QApplication, QVBoxLayout, QDockWidget
from PyQt6.QtCore import Qt, QEvent, pyqtSignal
from ui.elements.image_display.image_display import ImageDisplay
from ui.elements.menubar import MenuBar
from ui.elements.sidebar import Sidebar
from ui.dialogs.inference_dialog import InferenceDialog
from ui.dialogs.table import MaskResultsDock
from ui.dialogs.instance_count import MaskStatisticsDock
from ui.elements.slider import ImageSlider
import os
from PyQt6.QtGui import QIcon 
from core.state import StateManager  
from core.inference_manager import  InferenceManager
from core.exporters.yolo_exporter import YOLOExporter
from core.managers.tool_manager import ToolManager
from core.tools.auto_sam2 import Sam2Auto

from services.file_handlers import loader, get_resource_path
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

        icon_path = get_resource_path("resources/icons/icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        #self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.models_dir = get_resource_path("models/yolo")
        self.sam_dir = get_resource_path("models/sam")
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
                self.slider.set_image_count(len(image_paths)) 
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


    def run_sam2_auto(self):
        """
        Runs SAM2 automatic segmentation from the menu.
        """
        model = Sam2Auto(self)
        model.generate_masks(self.state_manager.current_image)
        print("🟢 Running SAM2 Auto Segmentation...")

#    def toggle_results_dock(self):
#        """Toggle visibility of the Results Table (dockable)."""
#        if self.results_dock.isHidden():
#            self.results_dock.show()
#            self.results_dock.raise_()  # Bring it to front if it's hidden behind something
#        else:
#            self.results_dock.hide()
