import os
import json

class ProjectConfigManager:
    def __init__(self, project_root):
        self.project_root = project_root
        self.config_path = os.path.join(project_root, ".segmentme", "config.json")
        self.data = {
            "images_dir": "images"
        }
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.data.update(json.load(f))
            except Exception as e:
                print(f"⚠️ Failed to load config: {e}")

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_images_dir(self):
        return os.path.join(self.project_root, self.data.get("images_dir", "images"))

    def set_images_dir(self, new_dir_relative_to_project):
        self.data["images_dir"] = new_dir_relative_to_project
        self.save()
