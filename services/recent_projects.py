import os
import json

import platform

def get_recent_file():
    base = os.path.expanduser("~")

    if platform.system() == "Windows":
        base = os.path.join(os.getenv("APPDATA"), "AquaVision")
    elif platform.system() == "Darwin":  # macOS
        base = os.path.join(base, "Library", "Application Support", "AquaVision")
    else:
        base = os.path.join(base, ".config", "aquavision")

    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "recent.json")


def load_recent_projects():
    try:
        with open(get_recent_file(), "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_recent_project(path):
    projects = load_recent_projects()
    if path in projects:
        projects.remove(path)
    projects.insert(0, path)  # Add to top
    projects = projects[:5]  # Keep most recent 5
    with open(get_recent_file(), "w") as f:
        json.dump(projects, f)
