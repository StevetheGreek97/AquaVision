from ui.dialogs.progress import ProgressDialogManager
from core.inference_thread import InferenceThread
from PyQt6.QtCore import QObject
from PyQt6.QtGui import QColor
import numpy as np
from core.data import DataManager
import os
import random
class InferenceManager(QObject):
    def __init__(self, parent, mode, display_text):
        super().__init__()
        self.parent = parent
        self.mode = mode
        self.display_text = display_text
        self.progress_manager = None
        self.inference_thread = None

    def run_inference(self, model_path, image_files):
        """
        Start the inference process with the provided model and images.
        """
        if not image_files:
            print("No image files provided for inference.")
            return

        # Initialize the inference thread
        self.inference_thread = InferenceThread(model_path, image_files, mode=self.mode)
        self.inference_thread.inference_completed.connect(self.on_inference_progress)
        self.inference_thread.finished.connect(self.finalize_progress)

        # Initialize the progress dialog manager
        self.progress_manager = ProgressDialogManager(
            self.parent,
            total_items=len(image_files),
            cancel_callback=self.stop_inference,
            display_text=self.display_text,
        )

        # Start the thread
        print("Starting inference thread...")
        self.inference_thread.start()

    def stop_inference(self):
        """
        Stop the inference thread gracefully.
        """
        if self.inference_thread and self.inference_thread.isRunning():
            print("Stopping inference thread...")
            self.inference_thread.stop()  # Graceful stop
            self.inference_thread.wait()  # Ensure thread completes
            print("Inference thread stopped.")

        # Ensure the progress dialog is closed
        if self.progress_manager:
            self.progress_manager.close()

    def on_inference_progress(self, image_path, masks, image, class_names):
        """
        Handle progress updates during inference.
        """
        # Update masks in the parent object
        image_name = os.path.splitext(os.path.basename(image_path))[0]

        for mask, class_name in zip(masks, class_names):
            # Save the mask using DataManager
            DataManager().save_mask(mask, image_name, class_name)

            # Check if the class already exists in the StateManager
            if class_name not in self.parent.state_manager.mask_colors:
                # Assign a random color
                random_color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                
                # Update StateManager with the new class and color
                self.parent.state_manager.set_mask_color(class_name, random_color)
                
                # Update the Sidebar dropdown
                self.parent.sidebar.class_dropdown.addItem(f"{class_name} ({random_color.name()})", userData=random_color)

                print(f"Added new class '{class_name}' with color {random_color.name()}")

        # Update the progress dialog
        current_value = self.progress_manager.progress_dialog.value() + 1
        self.progress_manager.update_progress(current_value)

    def finalize_progress(self):
        """
        Finalize the progress dialog and clean up the thread.
        """
        if self.progress_manager:
            self.progress_manager.close()

        # Clean up the thread
        if self.inference_thread and self.inference_thread.isRunning():
            self.inference_thread.wait()

        self.inference_thread = None
        print("Inference completed and cleaned up.")
