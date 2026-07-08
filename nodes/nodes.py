"""
COMFYJBB: Load & Process Image Batch node
- Queue-style incremental / random / single-file modes
- Routes loading by extension:
    * images (.png/.jpg/.jpeg/.webp/.bmp) -> PIL / InputImpl
    * .heic -> HEIC loader (InputImpl or pillow-heif fallback)
    * raw camera formats (.arw/.cr2/.cr3/.dng/.nef/.raf/.raw) -> rawpy if available
    * others -> bypass (moved to bypass_path)
- Moves processed files to processed_path, bypassed files to bypass_path.
- Outputs: IMAGE tensor, FILENAME_TEXT (string)
"""
import os
import shutil
import hashlib
import logging
import random
from typing import List, Optional

from PIL import Image, ImageOps, ImageSequence
import numpy as np
import torch

import folder_paths
import node_helpers
import comfy.model_management
from comfy.comfy_types import IO, ComfyNodeABC, InputTypeDict
from comfy_api.latest import InputImpl

logger = logging.getLogger(__name__)

COMMON_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
HEIC_EXTS = {".heic"}
RAW_EXTS = {".arw", ".cr2", ".cr3", ".dng", ".nef", ".raf", ".raw"}

def _ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create directory {path}: {e}")
        raise

def _list_files_in_dir(path: str) -> List[str]:
    try:
        entries = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        entries = [e for e in entries if not e.endswith(".processing")]
        return sorted(entries)
    except FileNotFoundError:
        return []

def _claim_file_atomic(src: str) -> Optional[str]:
    processing = src + ".processing"
    try:
        os.rename(src, processing)
        return processing
    except Exception:
        return None

def _finalize_move(src_processing: str, dest_dir: str, original_name: str):
    dest_path = os.path.join(dest_dir, original_name)
    try:
        shutil.move(src_processing, dest_path)
    except Exception:
        shutil.copy2(src_processing, dest_path)
        os.remove(src_processing)

def _load_with_inputimpl_or_pillow(path: str):
    dtype = comfy.model_management.intermediate_dtype()
    device = comfy.model_management.intermediate_device()

    try:
        components = InputImpl.VideoFromFile(path).get_components()
        if components.images.shape[0] > 0:
            images = components.images.to(device=device, dtype=dtype)
            mask = None
            if components.alpha is not None:
                mask = (1.0 - components.alpha[..., -1]).to(device=device, dtype=dtype)
            return images, mask
    except Exception:
        pass

    img = node_helpers.pillow(Image.open, path)
    output_images = []
    output_masks = []
    w, h = None, None
    for frame in ImageSequence.Iterator(img):
        frame = node_helpers.pillow(ImageOps.exif_transpose, frame)
        image = frame.convert("RGB")
        if len(output_images) == 0:
            w, h = image.size
        if image.size[0] != w or image.size[1] != h:
            continue
        arr = np.array(image).astype(np.float32) / 255.0
        tensor = torch.from_numpy(arr)[None,]
        if 'A' in frame.getbands():
            mask = np.array(frame.getchannel('A')).astype(np.float32) / 255.0
            mask = 1.0 - torch.from_numpy(mask)
            output_masks.append(mask.unsqueeze(0).to(dtype=dtype))
        output_images.append(tensor.to(dtype=dtype))

    if not output_images:
        raise RuntimeError(f"No usable image frames found in {path}")

    images_tensor = torch.cat(output_images, dim=0).to(device=device)
    mask_tensor = torch.cat(output_masks, dim=0).to(device=device) if output_masks else None
    return images_tensor, mask_tensor

def _load_raw_image(path: str):
    try:
        import rawpy
    except Exception:
        raise RuntimeError("rawpy not installed; cannot load raw camera formats")

    raw = rawpy.imread(path)
    rgb = raw.postprocess(use_camera_wb=True, output_bps=8)
    arr = rgb.astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr)[None,]
    dtype = comfy.model_management.intermediate_dtype()
    device = comfy.model_management.intermediate_device()
    return tensor.to(dtype=dtype, device=device), None

class LoadAndProcessImageBatch(ComfyNodeABC):
    @classmethod
    def INPUT_TYPES(s) -> InputTypeDict:
        default_batch = "/workspace/ComfyUI/InputBatch/"
        default_processed = "/workspace/ComfyUI/InputBatch/processed/"
        default_bypass = "/workspace/ComfyUI/InputBatch/Bypass/"

        return {
            "required": {
                "batch_path": (IO.STRING, {"default": default_batch}),
                "processed_path": (IO.STRING, {"default": default_processed}),
                "bypass_path": (IO.STRING, {"default": default_bypass}),
                "mode": (["single_file", "incremental", "random"], {"default": "incremental"}),
                "index": ("INT", {"default": 0, "min": 0}),
                "seed": ("INT", {"default": 0}),
                "label": (IO.STRING, {"default": ""}),
                "dry_run": (["false", "true"], {"default": "false", "tooltip": "If true, do not move files; useful for testing."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    FUNCTION = "process_next"
    CATEGORY = "image/batch"
    DESCRIPTION = "COMFYJBB: Load and process image batch queue; routes by extension to appropriate loaders, moves processed files to processed_path or bypass_path."

    def _normalize_paths(self, batch_path, processed_path, bypass_path):
        batch_path = os.path.expanduser(batch_path)
        processed_path = os.path.expanduser(processed_path)
        bypass_path = os.path.expanduser(bypass_path)
        return batch_path, processed_path, bypass_path

    def _select_file(self, files: List[str], mode: str, index: int, seed: int) -> Optional[str]:
        if not files:
            return None
        if mode == "random":
            rnd = random.Random(seed)
            return rnd.choice(files)
        if mode == "single_file":
            idx = max(0, min(index, len(files) - 1))
            return files[idx]
        return files[0]

    def process_next(self, batch_path: str, processed_path: str, bypass_path: str, mode: str = "incremental", index: int = 0, seed: int = 0, label: str = "", dry_run: str = "false"):
        batch_path, processed_path, bypass_path = self._normalize_paths(batch_path, processed_path, bypass_path)
        _ensure_dir(batch_path)
        _ensure_dir(processed_path)
        _ensure_dir(bypass_path)

        files = _list_files_in_dir(batch_path)
        if not files:
            raise RuntimeError(f"No files in batch path: {batch_path}")

        chosen = self._select_file(files, mode, index, seed)
        if chosen is None:
            raise RuntimeError("No file selected for processing.")

        claimed = _claim_file_atomic(chosen)
        if not claimed:
            files = _list_files_in_dir(batch_path)
            chosen = self._select_file(files, mode, index, seed)
            if chosen is None:
                raise RuntimeError("No file available to claim.")
            claimed = _claim_file_atomic(chosen)
            if not claimed:
                raise RuntimeError("Could not claim any file for processing (concurrency issue).")

        original_name = os.path.basename(chosen)
        ext = os.path.splitext(original_name)[1].lower()

        try:
            if ext in COMMON_IMAGE_EXTS or ext in HEIC_EXTS:
                images, mask = _load_with_inputimpl_or_pillow(claimed.replace(".processing", ""))
            elif ext in RAW_EXTS:
                try:
                    images, mask = _load_raw_image(claimed.replace(".processing", ""))
                except Exception as re:
                    logger.warning(f"RAW load failed for {chosen}: {re}")
                    if dry_run == "false":
                        _finalize_move(claimed, bypass_path, original_name)
                    raise RuntimeError(f"RAW load failed for {chosen}: {re}")
            else:
                logger.info(f"Bypassing unknown extension for {chosen}")
                if dry_run == "false":
                    _finalize_move(claimed, bypass_path, original_name)
                raise RuntimeError(f"Bypassed file {chosen} due to unsupported extension {ext}")

            if dry_run == "false":
                _finalize_move(claimed, processed_path, original_name)

            return (images, original_name)
        except Exception as e:
            try:
                if os.path.exists(claimed):
                    if dry_run == "false":
                        _finalize_move(claimed, bypass_path, original_name)
            except Exception as move_err:
                logger.warning(f"Failed to move failed file {claimed} to bypass: {move_err}")
            raise

NODE_CLASS_MAPPINGS = {
    "LoadAndProcessImageBatch": LoadAndProcessImageBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadAndProcessImageBatch": "COMFYJBB: Load & Process Image Batch",
}