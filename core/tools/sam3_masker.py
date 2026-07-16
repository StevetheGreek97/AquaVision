from core.tools.sam2_masker import SamMasker2
from core.tools.sam3_loader import load_sam3_predictor
from services.logger import get_logger

logger = get_logger(__name__)


class Sam3Masker(SamMasker2):
    """
    Interactive masking with the SAM 3 model.

    Same prompts and keys as the SAM 2 tool:
    * left click        — positive (foreground) point
    * right click       — negative (background) point
    * Ctrl + left drag  — bounding box
    * E to segment, S to save

    SAM3's interactive predictor exposes the same set_image/predict API as
    SAM2ImagePredictor, so only the model loading differs.
    """

    def _load_model(self):
        return load_sam3_predictor(self.device)
