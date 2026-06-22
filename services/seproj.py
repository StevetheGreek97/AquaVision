import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


def find_seproj(project_root: str | Path) -> Optional[Path]:
    candidates = list(Path(project_root).glob("*.SEproj"))
    return candidates[0] if candidates else None


def read_seproj(project_root: str | Path) -> Dict[str, Any]:
    path = find_seproj(project_root)
    if not path or not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
        if text.startswith("{"):
            return json.loads(text)
        return {}  # legacy plain-text marker
    except Exception:
        return {}


def write_seproj(project_root: str | Path, data: Dict[str, Any]):
    path = find_seproj(project_root)
    if path is None:
        name = Path(project_root).name
        path = Path(project_root) / f"{name}.SEproj"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_saved_images(project_root: str | Path) -> List[str]:
    return read_seproj(project_root).get("images", [])


def update_images(project_root: str | Path, image_names: List[str]):
    data = read_seproj(project_root)
    data["images"] = sorted(image_names)
    data.setdefault("name", Path(project_root).name)
    data.setdefault("created", datetime.now().isoformat())
    data["last_modified"] = datetime.now().isoformat()
    write_seproj(project_root, data)


def update_classes(project_root: str | Path, classes: List[Dict[str, str]]):
    """classes: list of {"name": "Fish", "color": "#ff0000"}"""
    data = read_seproj(project_root)
    data["classes"] = classes
    data.setdefault("name", Path(project_root).name)
    data.setdefault("created", datetime.now().isoformat())
    data["last_modified"] = datetime.now().isoformat()
    write_seproj(project_root, data)
