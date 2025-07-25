from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
import subprocess


class TrainingWorker(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.process = None

    def run(self):
        try:
            args = [
                "yolo",
                "train",  # this is required before the args below
                "task=segment",
                "mode=train",
                f"model={self.settings.model}",
                f"data={self.settings.data}",
                f"epochs={self.settings.epochs}",
                f"batch={self.settings.batch}",
                f"imgsz={self.settings.imgsz}",
                f"device={self.settings.device}",
                f"optimizer={self.settings.optimizer}",
                f"project={str(Path(self.settings.output_dir).parent)}",
                f"name={self.settings.name}",
                f"time={self.settings.time}",
                f"patience={self.settings.patience}",
                f"lr0={self.settings.lr0}",
                f"lrf={self.settings.lrf}",
                f"momentum={self.settings.momentum}",
                f"weight_decay={self.settings.weight_decay}",
                f"hsv_h={self.settings.hsv_h}",
                f"hsv_s={self.settings.hsv_s}",
                f"hsv_v={self.settings.hsv_v}",
                f"degrees={self.settings.degrees}",
                f"translate={self.settings.translate}",
                f"scale={self.settings.scale}",
                f"shear={self.settings.shear}",
                f"perspective={self.settings.perspective}",
                f"flipud={self.settings.flipud}",
                f"fliplr={self.settings.fliplr}",
                f"bgr={self.settings.bgr}",
                f"mosaic={self.settings.mosaic}",
                f"mixup={self.settings.mixup}",
                f"cutmix={self.settings.cutmix}",
                f"copy_paste={self.settings.copy_paste}",
                f"copy_paste_mode={self.settings.copy_paste_mode}",
                f"auto_augment={self.settings.auto_augment}",
                f"erasing={self.settings.erasing}",
            ]

            self.log_signal.emit(f"🔧 Command: {' '.join(args)}")

            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in self.process.stdout:
                if line:
                    self.log_signal.emit(line.strip())

            self.process.wait()

        except Exception as e:
            self.log_signal.emit(f"❌ Error: {e}")

        finally:
            self.finished_signal.emit()

    def stop(self):
        if self.process and self.process.poll() is None:
            self.log_signal.emit("🛑 Terminating training process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
                self.log_signal.emit("✅ Training terminated gracefully.")
            except subprocess.TimeoutExpired:
                self.log_signal.emit("⛔ Force killing training process...")
                self.process.kill()
            self.finished_signal.emit()
