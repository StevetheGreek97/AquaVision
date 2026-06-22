from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image
import numpy as np
from ultralytics import YOLO, SAM

class InferenceThread(QThread):
    # Emit: image_path, list_of_polygons (each Nx2 ndarray), list_of_class_names
    inference_completed = pyqtSignal(str, list, list)

    def __init__(self, model_path, image_paths, mode, conf, dims):
        super().__init__()
        self.model_path = model_path
        self.image_paths = image_paths
        self.mode = mode.lower()
        self.conf = conf
        self.dims = dims
        self._is_running = True

    def run(self):
        try:
            if self.mode == "yolo":
                self._run_yolo()
            elif self.mode == "sam":
                self._run_sam()
            else:
                print(f"Unsupported mode: {self.mode}")
        except Exception as e:
            print(f"Error during inference: {e}")
        finally:
            self._is_running = False
            self.finished.emit()

    def _run_yolo(self):
        try:
            model = YOLO(self.model_path)
            for image_path in self.image_paths:
                if not self._is_running:
                    break

                image = Image.open(image_path).convert("RGB")
                results = model.predict(
                    image_path, save_txt=False, save_crop=False, imgsz=self.dims,
                    verbose=False, conf=self.conf, iou=0.2, agnostic_nms=True
                )

                masks_xy = results[0].masks.xy if results[0].masks else []
                class_ids = results[0].boxes.cls.tolist() if results[0].boxes is not None else []
                class_names = [model.names[int(i)] for i in class_ids]

                self.inference_completed.emit(image_path, masks_xy, class_names)
        except Exception as e:
            print(f"Error in YOLO inference: {e}")

    def _run_sam(self):
        try:
            model = SAM(self.model_path)
            for image_path in self.image_paths:
                if not self._is_running:
                    break
                try:
                    image = Image.open(image_path).convert("RGB")
                    results = model(image)
                    masks_xy = results[0].masks.xy if results[0].masks else []
                    class_names = ["object"] * len(masks_xy)
                    self.inference_completed.emit(image_path, masks_xy, class_names)
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
        except Exception as e:
            print(f"Error initializing SAM model: {e}")

    def stop(self):
        self._is_running = False
