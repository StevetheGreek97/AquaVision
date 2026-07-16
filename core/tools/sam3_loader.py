"""Shared, cross-platform SAM3 model loading.

SAM3 has no Hydra configs — the architecture is built in code by
`build_sam3_image_model`, so only the checkpoint lives on disk (kept next
to the SAM2 ones in sam2_configs/).

The full SAM3 image model is ~3.4 GB, so unlike SAM2 the built predictor
is cached at module level while the tool is in use (ToolManager may
re-create the tool object, e.g. on a variant hot-reload). When the SAM
button is toggled off, ToolManager calls unload_sam3_predictor() so the
memory is returned; the next toggle rebuilds the model.
"""
import hashlib
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor

from services.file_handlers import get_resource_path
from services.logger import get_logger

logger = get_logger(__name__)

_CHECKPOINT = Path("sam2_configs") / "sam3.pt"

_cached_predictor = None
_cached_device = None
_cpu_patch_done = False


def _patch_sam3_for_cpu():
    """Make sam3 buildable on machines without CUDA.

    Two sam3 modules precompute caches on device="cuda" at __init__ time
    (an optimization for torch.compile); the caches are otherwise filled
    lazily on the right device at inference. On CPU-only machines those
    lines raise "No CUDA GPUs are available", so skip/redirect them.
    """
    global _cpu_patch_done
    if _cpu_patch_done:
        return

    import torch.nn.functional as F
    from sam3.model import vitdet
    from sam3.model.position_encoding import PositionEmbeddingSine
    from sam3.model.decoder import TransformerDecoder

    # vitdet's MLP always routes fc1 through a fused addmm that casts to
    # bfloat16; the following fc2 stays float32 and errors on CPU. Use a
    # plain float32 linear + activation instead.
    def addmm_act_fp32(activation, linear, mat1):
        out = linear(mat1)
        if activation in (F.relu, torch.nn.ReLU):
            return F.relu(out)
        if activation in (F.gelu, torch.nn.GELU):
            return F.gelu(out)
        raise ValueError(f"Unexpected activation {activation}")

    vitdet.addmm_act = addmm_act_fp32

    orig_pes_init = PositionEmbeddingSine.__init__

    def pes_init_no_precompute(self, *args, **kwargs):
        kwargs.pop("precompute_resolution", None)
        orig_pes_init(self, *args, **kwargs)

    PositionEmbeddingSine.__init__ = pes_init_no_precompute

    orig_get_coords = TransformerDecoder._get_coords

    @staticmethod
    def get_coords_cpu(H, W, device):
        if str(device).startswith("cuda"):
            device = "cpu"
        return orig_get_coords(H, W, device)

    TransformerDecoder._get_coords = get_coords_cpu

    _cpu_patch_done = True
    logger.debug("Patched sam3 init-time cuda precomputations for CPU")


class Sam3InteractivePredictor:
    """Adapter giving the SAM3 image model the SAM2ImagePredictor API.

    SAM3's inst_interactive_predictor has no backbone of its own — image
    features must come from the main model via Sam3Processor.set_image and
    model.predict_inst. This wrapper hides that, so the SAM3 tool can call
    set_image/predict exactly like the SAM2 tool does.
    """

    def __init__(self, model, device):
        self.model = model
        self.processor = Sam3Processor(model, device=device)
        self.state = None
        self._image_key = None

    def set_image(self, image):
        # Encoding an image takes ~20s on CPU, so skip it when the same
        # image is set again (every E press re-sets the current image).
        if isinstance(image, np.ndarray):
            key = (image.shape, hashlib.md5(image.tobytes()).hexdigest())
            if key == self._image_key and self.state is not None:
                logger.debug("SAM3: image unchanged, reusing encoded features")
                return
            self._image_key = key
            # Sam3Processor reads numpy dimensions as CHW; go through PIL
            # so HWC images from the app keep their true width/height.
            image = Image.fromarray(image)
        else:
            self._image_key = None
        self.state = self.processor.set_image(image)

    @torch.inference_mode()
    def predict(self, point_coords=None, point_labels=None, box=None,
                multimask_output=False):
        if self.state is None:
            raise RuntimeError("Call set_image before predict.")
        return self.model.predict_inst(
            self.state,
            point_coords=point_coords,
            point_labels=point_labels,
            box=box,
            multimask_output=multimask_output,
        )


def load_sam3_predictor(device):
    """Return the SAM3 interactive image predictor on `device`.

    The predictor has the same API as SAM2ImagePredictor (set_image /
    predict with point_coords, point_labels, box). Built once per process;
    subsequent calls return the cached instance.

    Raises FileNotFoundError if the checkpoint is missing.
    """
    global _cached_predictor, _cached_device

    if _cached_predictor is not None and _cached_device == str(device):
        return _cached_predictor

    checkpoint = Path(get_resource_path(str(_CHECKPOINT)))
    if not checkpoint.is_file():
        raise FileNotFoundError(
            f"SAM3 checkpoint not found at {checkpoint}. "
            "Download sam3.pt from https://huggingface.co/facebook/sam3 "
            "(gated — request access, then `hf auth login`) and place it "
            "in the sam2_configs folder."
        )

    if not torch.cuda.is_available():
        _patch_sam3_for_cpu()

    logger.info("Building SAM3 model (checkpoint=%s, device=%s) — this can "
                "take a while on CPU...", checkpoint, device)
    model = build_sam3_image_model(
        device=device,
        checkpoint_path=str(checkpoint),
        load_from_HF=False,
        enable_inst_interactivity=True,
    )

    _cached_predictor = Sam3InteractivePredictor(model, device)
    _cached_device = str(device)
    logger.info("Loaded SAM3 model (checkpoint=%s, device=%s)", checkpoint, device)
    return _cached_predictor


def unload_sam3_predictor():
    """Drop the cached SAM3 predictor so its ~3.4 GB can be reclaimed.

    Callers should follow up with gc.collect(). The next
    load_sam3_predictor call rebuilds the model from the checkpoint.
    """
    global _cached_predictor, _cached_device
    if _cached_predictor is None:
        return
    _cached_predictor = None
    _cached_device = None
    logger.info("Unloaded cached SAM3 model")
