"""Registry of the SAM model variants the unified SAM tool can run.

One sidebar button ("SAM") serves every variant; which one it loads is a
user preference persisted with QSettings and edited via
Settings -> SAM Model in the menu bar.

Checkpoints all live in sam2_configs/ (SAM3's too). A variant listed here
is only usable once its checkpoint file exists there — `is_available`
checks that, and the settings dialog greys out missing ones with their
download URL.
"""
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QSettings

from services.file_handlers import get_resource_path

_SETTINGS_KEY = "sam/model"

_SAM2_BASE_URL = "https://dl.fbaipublicfiles.com/segment_anything_2/072824"
_SAM21_BASE_URL = "https://dl.fbaipublicfiles.com/segment_anything_2/092824"


@dataclass(frozen=True)
class SamVariant:
    key: str
    label: str
    family: str          # "sam2" (covers 2.1) or "sam3"
    checkpoint: str      # filename inside sam2_configs/
    configs: tuple = ()  # Hydra config name candidates (sam2 family only)
    download_url: str = ""
    description: str = ""


SAM_VARIANTS = {
    v.key: v for v in (
        SamVariant(
            key="sam2_tiny", label="SAM2 Tiny", family="sam2",
            checkpoint="sam2_hiera_tiny.pt",
            configs=("configs/sam2/sam2_hiera_t.yaml", "sam2_hiera_t.yaml"),
            download_url=f"{_SAM2_BASE_URL}/sam2_hiera_tiny.pt",
            description="Fastest, lowest accuracy (~156 MB).",
        ),
        SamVariant(
            key="sam2_small", label="SAM2 Small", family="sam2",
            checkpoint="sam2_hiera_small.pt",
            configs=("configs/sam2/sam2_hiera_s.yaml", "sam2_hiera_s.yaml"),
            download_url=f"{_SAM2_BASE_URL}/sam2_hiera_small.pt",
            description="Fast, a bit more accurate than Tiny (~185 MB).",
        ),
        SamVariant(
            key="sam2_base_plus", label="SAM2 Base+", family="sam2",
            checkpoint="sam2_hiera_base_plus.pt",
            configs=("configs/sam2/sam2_hiera_b+.yaml", "sam2_hiera_b+.yaml"),
            download_url=f"{_SAM2_BASE_URL}/sam2_hiera_base_plus.pt",
            description="Balanced speed/accuracy (~324 MB).",
        ),
        SamVariant(
            key="sam2_large", label="SAM2 Large", family="sam2",
            checkpoint="sam2_hiera_large.pt",
            configs=("configs/sam2/sam2_hiera_l.yaml", "sam2_hiera_l.yaml"),
            download_url=f"{_SAM2_BASE_URL}/sam2_hiera_large.pt",
            description="Most accurate SAM2, slower (~898 MB).",
        ),
        SamVariant(
            key="sam2.1_tiny", label="SAM2.1 Tiny", family="sam2",
            checkpoint="sam2.1_hiera_tiny.pt",
            configs=("configs/sam2.1/sam2.1_hiera_t.yaml",),
            download_url=f"{_SAM21_BASE_URL}/sam2.1_hiera_tiny.pt",
            description="Improved SAM2 release, fastest (~156 MB).",
        ),
        SamVariant(
            key="sam2.1_small", label="SAM2.1 Small", family="sam2",
            checkpoint="sam2.1_hiera_small.pt",
            configs=("configs/sam2.1/sam2.1_hiera_s.yaml",),
            download_url=f"{_SAM21_BASE_URL}/sam2.1_hiera_small.pt",
            description="Improved SAM2 release, fast (~185 MB).",
        ),
        SamVariant(
            key="sam2.1_base_plus", label="SAM2.1 Base+", family="sam2",
            checkpoint="sam2.1_hiera_base_plus.pt",
            configs=("configs/sam2.1/sam2.1_hiera_b+.yaml",),
            download_url=f"{_SAM21_BASE_URL}/sam2.1_hiera_base_plus.pt",
            description="Improved SAM2 release, balanced (~324 MB).",
        ),
        SamVariant(
            key="sam2.1_large", label="SAM2.1 Large", family="sam2",
            checkpoint="sam2.1_hiera_large.pt",
            configs=("configs/sam2.1/sam2.1_hiera_l.yaml",),
            download_url=f"{_SAM21_BASE_URL}/sam2.1_hiera_large.pt",
            description="Improved SAM2 release, most accurate (~898 MB).",
        ),
        SamVariant(
            key="sam3", label="SAM3", family="sam3",
            checkpoint="sam3.pt",
            download_url="https://huggingface.co/facebook/sam3",
            description="Newest and most accurate; large and slow on CPU "
                        "(~3.4 GB, gated on Hugging Face).",
        ),
    )
}

DEFAULT_KEY = "sam2_tiny"


def checkpoint_path(variant: SamVariant) -> Path:
    return Path(get_resource_path(str(Path("sam2_configs") / variant.checkpoint)))


def is_available(variant: SamVariant) -> bool:
    """True if the variant's checkpoint file is on disk."""
    return checkpoint_path(variant).is_file()


def get_selected_key() -> str:
    """The persisted user choice, falling back to the default if the saved
    key is unknown or its checkpoint has since been deleted."""
    key = QSettings("AquaVision", "AquaVision").value(_SETTINGS_KEY, DEFAULT_KEY)
    if key in SAM_VARIANTS and is_available(SAM_VARIANTS[key]):
        return key
    return DEFAULT_KEY


def set_selected_key(key: str):
    if key not in SAM_VARIANTS:
        raise ValueError(f"Unknown SAM variant {key!r}")
    QSettings("AquaVision", "AquaVision").setValue(_SETTINGS_KEY, key)


def get_selected_variant() -> SamVariant:
    return SAM_VARIANTS[get_selected_key()]
