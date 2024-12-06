from ui.dialogs.progress import ProgressDialogManager
from core.inference_thread import InferenceThread
from PyQt6.QtCore import QObject
import numpy as np
from core.data import ImageMask

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

    def on_inference_progress(self, image_path, masks, image):
        """
        Handle progress updates during inference.
        """
        # Update masks in the parent object




        # Store the ImageMask in the StateManager
        self.parent.state_manager.add_masks(masks, image_path)

        # Update display and sidebar
        #if image_path == self.parent.state_manager.image_paths[self.parent.state_manager.current_image_index]:
            #self.parent.image_display.display_image(image_path)
            #self.parent.sidebar.update_mask_table(image_path, self.parent.image_masks)

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
