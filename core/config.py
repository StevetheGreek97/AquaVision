from pathlib import Path
import json

class ProjectConfigManager:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.config_path = self.project_root / ".segmentme" / "config.json"
        self.data = {
            "images_dir": "images"
        }
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with self.config_path.open("r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception as e:
                print(f"⚠️ Failed to load config: {e}")

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get_images_dir(self):
        return self.project_root / self.data.get("images_dir", "images")

    def set_images_dir(self, new_dir_relative_to_project):
        self.data["images_dir"] = new_dir_relative_to_project
        self.save()
