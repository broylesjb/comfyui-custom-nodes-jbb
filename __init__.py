"""
comfyui-custom-nodes-jbb — root package entrypoint for ComfyUI custom node loader.

Aggregates NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS from all sub-packages
so ComfyUI 0.27.0+ can load the entire suite when the repository is cloned directly
into ComfyUI's custom_nodes/ directory.
"""

from importlib import import_module

NODE_CLASS_MAPPINGS: dict = {}
NODE_DISPLAY_NAME_MAPPINGS: dict = {}


def _merge_module_mappings(module_path: str, register_preview_route: bool = False) -> None:
    try:
        node_module = import_module(module_path, package=__name__)
    except Exception:
        return

    class_mappings = getattr(node_module, "NODE_CLASS_MAPPINGS", {})
    display_mappings = getattr(node_module, "NODE_DISPLAY_NAME_MAPPINGS", {})
    if not isinstance(class_mappings, dict):
        return
    if not isinstance(display_mappings, dict):
        display_mappings = {}

    for key, value in class_mappings.items():
        NODE_CLASS_MAPPINGS.setdefault(key, value)

    for key in class_mappings.keys():
        if key in display_mappings:
            NODE_DISPLAY_NAME_MAPPINGS.setdefault(key, display_mappings[key])
        else:
            NODE_DISPLAY_NAME_MAPPINGS.setdefault(key, key)

    if register_preview_route:
        try:
            register_route = getattr(node_module, "_register_preview_route_if_possible", None)
            if callable(register_route):
                register_route()
        except Exception:
            pass


_merge_module_mappings(".nodes.comfyjbb_load_process_batch.nodes")
_merge_module_mappings(".nodes.comfyui_loadheicimagefrompath.nodes", register_preview_route=True)
_merge_module_mappings(".nodes.comfyui_loadimagefrompath.nodes")
_merge_module_mappings(".nodes.comfyui_raw_image_frompath.nodes")

# Expose the HEIC frontend extension (drag-and-drop HEIC/HEIF upload handling)
WEB_DIRECTORY = "nodes/comfyui_loadheicimagefrompath/web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
