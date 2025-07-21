# core/trainer/worker.py
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from core.trainer.launcher import launch_training
import subprocess
class TrainingWorker(QObject):

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, settings, working_dir):
        super().__init__()
        self.settings = settings
        self.working_dir = working_dir
        self.process = None

    def run(self):
        try:
            args = ["yolo", "task=segment", "mode=train"] + [f"{k}={v}" for k, v in self.settings.items()]
            print("[TRAINING CMD]", " ".join(args))

            self.process = subprocess.Popen(args, cwd=self.working_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            for line in self.process.stdout:
                self.log_signal.emit(line.strip())

            self.process.wait()
            self.finished_signal.emit()
        except Exception as e:
            self.log_signal.emit(f"❌ Error: {e}")
            self.finished_signal.emit()


    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.finished_signal.emit()



