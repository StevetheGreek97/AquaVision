from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image
import numpy as np
from ultralytics import YOLO, SAM


class InferenceThread(QThread):
    inference_completed = pyqtSignal(str, list, np.ndarray, list)  # Signal for progress updates

    def __init__(self, model_path, image_paths, mode):
        super().__init__()
        self.model_path = model_path
        self.image_paths = image_paths
        self.mode = mode.lower()
        self._is_running = True  # Flag to control thread execution

    def run(self):
        """
        Main execution method of the thread.
        """
        try:
            if self.mode == "yolo":
                self.run_yolo()
            elif self.mode == "sam":
                self.run_sam()
            else:
                print(f"Unsupported mode: {self.mode}")
        except Exception as e:
            print(f"Error during inference: {e}")
        finally:
            self._is_running = False  # Ensure thread stops gracefully
            self.finished.emit()

    def run_yolo(self):
        """
        Perform inference using YOLO.
        """
        try:
            print("Initializing YOLO model...")
            model = YOLO(self.model_path)

            for image_path in self.image_paths:
                if not self._is_running:  # Check if thread was stopped
                    print("YOLO inference canceled.")
                    break

                # Perform inference
                image = Image.open(image_path).convert("RGB")
                results = model.predict(image, save_txt=False, save_crop=False, verbose = False)
                segmentation_results = results[0].masks.xy if results[0].masks else []
                np_image = np.array(image)
                # Extract class names
                class_ids = results[0].boxes.cls.tolist()  # Get class IDs
                class_names = [model.names[int(cls_id)] for cls_id in class_ids]  # Convert IDs to names



                # Emit progress signal ""     str         list                  np.ndarray list
                self.inference_completed.emit(image_path, segmentation_results, np_image, class_names)

        except Exception as e:
            print(f"Error in YOLO inference: {e}")
        finally:
            print("Cleaning up YOLO model...")

    def run_sam(self):
        """
        Perform inference using SAM.
        """
        try:
            print("Initializing SAM model...")
            model = SAM(self.model_path)

            for image_path in self.image_paths:
                if not self._is_running:  # Check stop flag
                    print("SAM inference canceled.")
                    break

                # Perform inference
                try:
                    image = Image.open(image_path).convert("RGB")
                    results = model(image)
                    segmentation_results = results[0].masks.xy if results[0].masks else []
                    np_image = np.array(image)

                    # Emit progress signal
                    self.inference_completed.emit(image_path, segmentation_results, np_image)
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")

        except Exception as e:
            print(f"Error initializing SAM model: {e}")
        finally:
            print("Cleaning up SAM model...")
            del model  # Explicitly delete the model to release resources

    def stop(self):
        """
        Gracefully stop the thread.
        """
        print("Stopping thread...")
        self._is_running = False
