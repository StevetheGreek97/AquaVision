# core/trainer/launcher.py
import subprocess
import os

def launch_training(settings: dict, working_dir: str):
    """
    Launches the training subprocess.
    Args:
        settings (dict): Dictionary of YOLO training arguments.
        working_dir (str): Directory to execute the training script in.
    """
    args = ["yolo", "task=segment", "mode=train"]
    for key, value in settings.items():
        args.append(f"{key}={value}")

    return subprocess.Popen(args, cwd=working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
