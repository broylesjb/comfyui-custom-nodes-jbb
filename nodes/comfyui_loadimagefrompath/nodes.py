# Load Image (from path) custom node for ComfyUI
# Package: comfyui_loadimagefrompath
# This nodes.py provides a LoadImageFromPath node that preserves core LoadImage behavior
# and adds an optional `image_path` string to load arbitrary file paths. It also uses
# a COMBO config matching the existing nodes in this repo (upload + refresh behavior).

import os
import hashlib
import json
from PIL import Image, ImageOps, ImageSequence

import torch
import numpy as np

import folder_paths
import node_helpers
from comfy.comfy_types import IO, ComfyNodeABC, InputTypeDict, FileLocator
from comfy_api.latest import InputImpl


class LoadImageFromPath(ComfyNodeABC):
    @classmethod
    def INPUT_TYPES(s) -> InputTypeDict:
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        files = folder_paths.filter_files_content_types(files, ["image"])

        # COMBO config matching existing nodes in this repo
        combo_config = {
            "image_upload": True,
            "image_folder": "input",
            "remote": {
                "route": "/internal/files/input",
                "refresh_button": True,
                "control_after_refresh": "first"
            }
        }

        return {
            "required": {
                "image": (sorted(files), combo_config),
            },
            "optional": {
                "image_path": (IO.STRING,),
            }
        }

    CATEGORY = "COMFYJBB"
    ESSENTIALS_CATEGORY = "Basics"
    SEARCH_ALIASES = ["load image", "open image", "import image", "image input", "upload image", "read image", "image loader"]

    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "load_image"

    def _load_from_path(self, image_path):
        dtype = comfy.model_management.intermediate_dtype()
        device = comfy.model_management.intermediate_device()

        # Try video-like loaders first
        try:
            components = InputImpl.VideoFromFile(image_path).get_components()
            if components.images.shape[0] > 0:
                images = components.images.to(device=device, dtype=dtype)
                mask = (1.0 - components.alpha[..., -1]).to(device=device, dtype=dtype) if components.alpha is not None else torch.zeros((components.images.shape[1], components.images.shape[2]), dtype=dtype, device=device)
                return images, mask
        except Exception:
            pass

        img = node_helpers.pillow(Image.open, image_path)

        output_images = []
        output_masks = []
        w, h = None, None

        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]

            if image.size[0] != w or image.size[1] != h:
                continue

            arr = np.array(image).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr)[None,]
            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1.0 - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

            output_images.append(tensor.to(dtype=dtype))
            output_masks.append(mask.unsqueeze(0).to(dtype=dtype))

        if len(output_images) == 0:
            raise RuntimeError(f"Unable to load image(s) from path: {image_path}")

        output_image = torch.cat(output_images, dim=0)
        output_mask = torch.cat(output_masks, dim=0)

        return output_image.to(device=device, dtype=dtype), output_mask.to(device=device, dtype=dtype)

    def load_image(self, image, image_path=None):
        if image_path is not None and isinstance(image_path, str) and image_path.strip() != "":
            resolved = os.path.expanduser(image_path)
            if not os.path.isabs(resolved):
                resolved = os.path.join(folder_paths.get_input_directory(), resolved)
            if not os.path.exists(resolved):
                raise RuntimeError(f"Image path not found: {resolved}")
            return self._load_from_path(resolved)

        image_path_annotated = folder_paths.get_annotated_filepath(image)
        return self._load_from_path(image_path_annotated)

    @classmethod
    def IS_CHANGED(s, image, image_path=None):
        path = None
        if image_path is not None and isinstance(image_path, str) and image_path.strip() != "":
            path = os.path.expanduser(image_path)
            if not os.path.isabs(path):
                path = os.path.join(folder_paths.get_input_directory(), path)
        else:
            path = folder_paths.get_annotated_filepath(image)

        m = hashlib.sha256()
        with open(path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(s, image, image_path=None):
        if image_path is not None and isinstance(image_path, str) and image_path.strip() != "":
            path = os.path.expanduser(image_path)
            if not os.path.isabs(path):
                path = os.path.join(folder_paths.get_input_directory(), path)
            if not os.path.exists(path):
                return f"Invalid image file: {path}"
            return True

        if not folder_paths.exists_annotated_filepath(image):
            return f"Invalid image file: {image}"
        return True


NODE_CLASS_MAPPINGS = {
    "LoadImageFromPath": LoadImageFromPath,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageFromPath": "COMFYJBB: Load Image (From Path optional)",
}
