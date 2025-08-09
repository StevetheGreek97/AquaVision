from PyQt6.QtCore import QObject, QTimer
from ui.dialogs.progress import ProgressDialogManager
from core.inference_thread import InferenceThread
from PyQt6.QtGui import QColor
import random, os

class InferenceManager(QObject):
    def __init__(self, parent, mode, display_text):
        super().__init__()
        self.parent = parent
        self.mode = mode
        self.display_text = display_text
        self.progress_manager = None
        self.inference_thread = None

        # Coalesce UI updates coming from many images
        self._ui_refresh_timer = QTimer(self)
        self._ui_refresh_timer.setSingleShot(True)
        self._ui_refresh_timer.timeout.connect(self._do_ui_refresh)

        self._need_overlay_refresh = False
        self._need_stats_refresh = False
        self._need_class_dropdown_refresh = False

    def run_inference(self, model_path, image_files, conf):
        if not image_files:
            print("No image files provided for inference.")
            return

        if self.inference_thread and self.inference_thread.isRunning():
            self.stop_inference()

        self.inference_thread = InferenceThread(model_path, image_files, mode=self.mode, conf=conf)
        self.inference_thread.inference_completed.connect(self.on_inference_progress)
        self.inference_thread.finished.connect(self.finalize_progress)

        self.progress_manager = ProgressDialogManager(
            self.parent,
            total_items=len(image_files),
            cancel_callback=self.stop_inference,
            display_text=self.display_text,
        )

        self.inference_thread.start()

    def stop_inference(self):
        if self.inference_thread and self.inference_thread.isRunning():
            self.inference_thread.stop()
            self.inference_thread.wait()
        if self.progress_manager:
            self.progress_manager.close()

    def on_inference_progress(self, image_path, masks, class_names):
        """
        Called once per image from the worker thread (Qt queued connection).
        Keep this light: save to DB, flag what needs UI refresh, then schedule one UI pass.
        """
        image_name = os.path.splitext(os.path.basename(image_path))[0]

        # Save masks
        for mask, class_name in zip(masks, class_names):
            if mask is None:
                continue
            if getattr(mask, "size", 0) < 2:
                continue
            # NOTE: expect mask as Nx2 coordinates array (float) from Ultralytics
            self.parent.state_manager.mask_manager.save_mask(mask, image_name, class_name)

            # Ensure the class exists (don’t repopulate dropdown yet)
            if class_name not in self.parent.state_manager.class_manager.get_all_class_names():
                rand = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                self.parent.state_manager.class_manager.add_class(class_name, rand)
                self._need_class_dropdown_refresh = True

        # Flag one overlay/stat refresh (coalesced)
        self._need_overlay_refresh = True
        self._need_stats_refresh = True

        # Progress
        if self.progress_manager:
            cur = self.progress_manager.progress_dialog.value() + 1
            self.progress_manager.update_progress(cur)

        # Schedule a single UI refresh after a short delay to absorb bursts
        self._ui_refresh_timer.start(60)

    def _do_ui_refresh(self):
        if self._need_class_dropdown_refresh and hasattr(self.parent, "sidebar"):
            self.parent.sidebar.populate_class_dropdown()
        if self._need_overlay_refresh and hasattr(self.parent, "image_display"):
            self.parent.image_display.refresh_masks()
        if self._need_stats_refresh and hasattr(self.parent, "statistics") and self.parent.statistics.isVisible():
            self.parent.statistics.refresh_plot()

        # Let the table rebuild on its own throttled path
        if hasattr(self.parent, "annotations") and self.parent.annotations.isVisible():
            self.parent.annotations.refresh_table(delay_ms=80)

        # reset flags
        self._need_class_dropdown_refresh = False
        self._need_overlay_refresh = False
        self._need_stats_refresh = False

    def finalize_progress(self):
        if self.progress_manager:
            self.progress_manager.close()
        if self.inference_thread and self.inference_thread.isRunning():
            self.inference_thread.wait()
        self.inference_thread = None
        print("Inference completed and cleaned up.")
