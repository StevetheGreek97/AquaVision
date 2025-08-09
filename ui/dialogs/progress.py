from PyQt6.QtWidgets import QProgressDialog
from PyQt6.QtCore import Qt

class ProgressDialogManager:
    def __init__(self, parent, total_items, cancel_callback, display_text= "Running Inference..."):
        """
        Initialize the progress dialog.
        :param parent: Parent widget for the progress dialog.
        :param total_items: Total number of items to process.
        :param cancel_callback: Callback function to execute on cancel.
        """
        self.progress_dialog = QProgressDialog(display_text, "Cancel", 0, total_items, parent)
        #self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.progress_dialog.setValue(0)

        # Connect cancel button to the provided callback
        self.progress_dialog.canceled.connect(cancel_callback)
        self.progress_dialog.setWindowModality(Qt.WindowModality.NonModal)
        self.progress_dialog.setMinimumDuration(0)   # show immediately without blocking
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)

    def update_progress(self, current_value):
        """
        Update the progress value.
        :param current_value: The current progress value.
        """
        self.progress_dialog.setValue(current_value)

    def close(self):
        """Close the progress dialog."""
        self.progress_dialog.close()
