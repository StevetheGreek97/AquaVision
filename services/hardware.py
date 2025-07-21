import torch
import platform
from PyQt6.QtWidgets import QMessageBox

def auto_detect_device(parent=None):
    """
    Detects the best available device for training.

    Priority:
    1. CUDA (NVIDIA GPU)
    2. MPS (Apple Silicon)
    3. CPU (fallback with warning)
    """
    if torch.cuda.is_available():
        num_gpus = torch.cuda.device_count()
        devices = list(range(num_gpus))
        QMessageBox.information(parent, "Device Info", f"✅ {num_gpus} CUDA GPU(s) detected. Training will use GPU(s): {devices}")
        return devices if len(devices) > 1 else devices[0]

    elif platform.system() == "Darwin" and torch.backends.mps.is_available():
        QMessageBox.information(parent, "Device Info", "✅ Apple Silicon detected. Using Metal Performance Shaders (MPS).")
        return "mps"

    else:
        QMessageBox.warning(parent, "Device Warning", "⚠️ No GPU found. Training will use the CPU and may take significantly longer.")
        return "cpu"
