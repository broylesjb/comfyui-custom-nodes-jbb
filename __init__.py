"""
comfyui-custom-nodes-jbb — root package entrypoint for ComfyUI custom node loader.

Aggregates NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS from all sub-packages
so ComfyUI 0.27.0+ can load the entire suite when the repository is cloned directly
into ComfyUI's custom_nodes/ directory.
"""

NODE_CLASS_MAPPINGS: dict = {}
NODE_DISPLAY_NAME_MAPPINGS: dict = {}

try:
    from nodes.comfyjbb_load_process_batch.nodes import (
        NODE_CLASS_MAPPINGS as _m,
        NODE_DISPLAY_NAME_MAPPINGS as _d,
    )
    NODE_CLASS_MAPPINGS.update(_m)
    NODE_DISPLAY_NAME_MAPPINGS.update(_d)
except Exception:
    pass

try:
    from nodes.comfyui_loadheicimagefrompath.nodes import (
        NODE_CLASS_MAPPINGS as _m,
        NODE_DISPLAY_NAME_MAPPINGS as _d,
    )
    NODE_CLASS_MAPPINGS.update(_m)
    NODE_DISPLAY_NAME_MAPPINGS.update(_d)
    try:
        from nodes.comfyui_loadheicimagefrompath.nodes import _register_preview_route_if_possible
        _register_preview_route_if_possible()
    except Exception:
        pass
except Exception:
    pass

try:
    from nodes.comfyui_loadimagefrompath.nodes import (
        NODE_CLASS_MAPPINGS as _m,
        NODE_DISPLAY_NAME_MAPPINGS as _d,
    )
    NODE_CLASS_MAPPINGS.update(_m)
    NODE_DISPLAY_NAME_MAPPINGS.update(_d)
except Exception:
    pass

try:
    from nodes.comfyui_raw_image_frompath.nodes import NODE_CLASS_MAPPINGS as _m
    NODE_CLASS_MAPPINGS.update(_m)
except Exception:
    pass

# Expose the HEIC frontend extension (drag-and-drop HEIC/HEIF upload handling)
WEB_DIRECTORY = "nodes/comfyui_loadheicimagefrompath/web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
