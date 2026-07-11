import importlib.util
import sys
import types
from pathlib import Path


def _load_root_package_with_mocks(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]

    torch = types.ModuleType("torch")
    torch.float32 = "float32"
    torch.Tensor = object
    torch.from_numpy = lambda arr: arr
    torch.zeros = lambda *args, **kwargs: None
    torch.cat = lambda tensors, dim=0: tensors[0] if tensors else None
    monkeypatch.setitem(sys.modules, "torch", torch)

    comfy_types = types.ModuleType("comfy.comfy_types")
    comfy_types.IO = types.SimpleNamespace(STRING="STRING", BOOL="BOOL")
    comfy_types.ComfyNodeABC = object
    comfy_types.InputTypeDict = dict
    comfy_types.FileLocator = dict
    monkeypatch.setitem(sys.modules, "comfy.comfy_types", comfy_types)

    model_management = types.ModuleType("comfy.model_management")
    model_management.intermediate_dtype = lambda: torch.float32
    model_management.intermediate_device = lambda: "cpu"
    monkeypatch.setitem(sys.modules, "comfy.model_management", model_management)

    comfy_module = types.ModuleType("comfy")
    comfy_module.model_management = model_management
    comfy_module.comfy_types = comfy_types
    monkeypatch.setitem(sys.modules, "comfy", comfy_module)

    comfy_api_latest = types.ModuleType("comfy_api.latest")

    class _DummyVideoFromFile:
        def __init__(self, path):
            self.path = path

        def get_components(self):
            raise RuntimeError("No video components available")

    class _DummyInputImpl:
        VideoFromFile = _DummyVideoFromFile

    comfy_api_latest.InputImpl = _DummyInputImpl
    monkeypatch.setitem(sys.modules, "comfy_api.latest", comfy_api_latest)

    folder_paths = types.SimpleNamespace(
        get_input_directory=lambda: str(repo_root),
        get_output_directory=lambda: str(repo_root),
        get_annotated_filepath=lambda fn: str(repo_root / fn),
        exists_annotated_filepath=lambda fn: True,
        filter_files_content_types=lambda files, types_: files,
    )
    monkeypatch.setitem(sys.modules, "folder_paths", folder_paths)

    node_helpers = types.ModuleType("node_helpers")
    node_helpers.pillow = lambda func, path_or_image, *args, **kwargs: path_or_image
    monkeypatch.setitem(sys.modules, "node_helpers", node_helpers)

    rawpy = types.ModuleType("rawpy")
    rawpy.HighlightMode = types.SimpleNamespace(
        Clip=1,
        Ignore=2,
        Blend=3,
        ReconstructDefault=4,
    )
    monkeypatch.setitem(sys.modules, "rawpy", rawpy)

    # Simulate ComfyUI's own top-level `nodes` module to ensure relative imports are used.
    monkeypatch.setitem(sys.modules, "nodes", types.ModuleType("nodes"))

    spec = importlib.util.spec_from_file_location(
        "comfyui_custom_nodes_jbb",
        str(repo_root / "__init__.py"),
        submodule_search_locations=[str(repo_root)],
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "comfyui_custom_nodes_jbb", module)
    spec.loader.exec_module(module)
    return module


def test_root_exports_all_expected_node_mappings(monkeypatch):
    module = _load_root_package_with_mocks(monkeypatch)

    expected_keys = {
        "LoadAndProcessImageBatch",
        "LoadImagePlusHEIC",
        "LoadImageFromPath",
        "Load Raw Image",
    }

    assert set(module.NODE_CLASS_MAPPINGS.keys()) == expected_keys
    assert set(module.NODE_DISPLAY_NAME_MAPPINGS.keys()) == expected_keys
    assert module.NODE_CLASS_MAPPINGS["LoadImagePlusHEIC"].__name__ == "LoadImagePlusHEIC"
