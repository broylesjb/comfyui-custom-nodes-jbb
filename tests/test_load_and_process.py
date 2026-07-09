import sys
import types
import importlib.util
from pathlib import Path
import numpy as np
import pytest

# Try to import runtime dependencies; skip if not available (Pillow/torch are needed)
try:
    from PIL import Image as PILImage
    import PIL
    import torch
except Exception as e:
    pytest.skip(f"Skipping tests because required runtime packages are missing: {e}", allow_module_level=True)

# --- Mock minimal comfy/comfy_api modules so tests run without ComfyUI installed ---
comfy_types = types.ModuleType("comfy.comfy_types")
comfy_types.IO = types.SimpleNamespace(STRING="STRING", BOOL="BOOL")
comfy_types.ComfyNodeABC = object
comfy_types.InputTypeDict = dict
sys.modules["comfy.comfy_types"] = comfy_types

model_management = types.ModuleType("comfy.model_management")
model_management.intermediate_dtype = lambda: torch.float32
model_management.intermediate_device = lambda: "cpu"
sys.modules["comfy.model_management"] = model_management

# Create top-level comfy module and attach attributes expected by nodes.py
comfy_module = types.ModuleType("comfy")
comfy_module.model_management = model_management
comfy_module.comfy_types = comfy_types
sys.modules["comfy"] = comfy_module

comfy_api_latest = types.ModuleType("comfy_api.latest")
class _DummyVideoFromFile:
    def __init__(self, path):
        self.path = path
    def get_components(self):
        raise RuntimeError("No video components available")
class _DummyInputImpl:
    VideoFromFile = _DummyVideoFromFile
comfy_api_latest.InputImpl = _DummyInputImpl
sys.modules["comfy_api.latest"] = comfy_api_latest
# --- End mocks ---

# Provide a minimal folder_paths mock used inside the node modules (ComfyUI normally provides this)
_folder_paths = types.SimpleNamespace(
    get_input_directory=lambda: Path.cwd(),
    get_output_directory=lambda: Path.cwd(),
    get_annotated_filepath=lambda fn: Path(fn),
    exists_annotated_filepath=lambda fn: Path(fn).exists(),
    filter_files_content_types=lambda files, types: files,
)
sys.modules["folder_paths"] = _folder_paths

# Provide a minimal node_helpers mock used inside the node modules
_node_helpers = types.ModuleType("node_helpers")
def _pillow_loader(func, path_or_image, *args, **kwargs):
    """
    Support two common call patterns from nodes:
    - node_helpers.pillow(Image.open, path)         -> func expects a path (open it)
    - node_helpers.pillow(ImageOps.exif_transpose, image) -> func expects an Image (apply directly)
    """
    # If func is PIL.Image.open: ensure we pass a path or file-like, not an Image instance.
    if func is PILImage.open:
        if isinstance(path_or_image, PIL.Image.Image):
            return path_or_image
        return PILImage.open(path_or_image)
    # Otherwise func expects a PIL Image; open if a path was provided.
    if isinstance(path_or_image, PIL.Image.Image):
        img = path_or_image
    else:
        img = PILImage.open(path_or_image)
    return func(img, *args, **kwargs)

_node_helpers.pillow = _pillow_loader
_node_helpers.get_safe_filename = lambda p: Path(p).name
_node_helpers.save_image = lambda img, path: img.save(path)
sys.modules["node_helpers"] = _node_helpers

# Dynamically load the node module from its hyphenated folder and make imports resolvable
_nodes_py = Path(__file__).resolve().parents[1] / "nodes" / "comfyjbb_load_process_batch" / "nodes.py"
spec = importlib.util.spec_from_file_location("comfyjbb_load_process_batch_nodes", str(_nodes_py))
node_module = importlib.util.module_from_spec(spec)
# ensure the node folder and repo root are importable (so imports like `import folder_paths`/`import node_helpers` work)
repo_root = str(Path(__file__).resolve().parents[1])
node_dir = str(_nodes_py.parent)
sys.path.insert(0, node_dir)
sys.path.insert(0, repo_root)
spec.loader.exec_module(node_module)
LoadAndProcessImageBatch = node_module.LoadAndProcessImageBatch

import node_helpers  # resolves to our mock
from PIL import Image as PILImage  # available for tests

def _make_png(path: str):
    PILImage.new("RGB", (16, 16), (10, 20, 30)).save(path)

def test_process_png_dry_run(tmp_path: Path):
    batch = tmp_path / "batch"
    processed = tmp_path / "processed"
    bypass = tmp_path / "bypass"
    batch.mkdir()
    processed.mkdir()
    bypass.mkdir()

    img_path = batch / "test.png"
    _make_png(str(img_path))

    node = LoadAndProcessImageBatch()

    images, fname, status = node.process_next(str(batch), str(processed), str(bypass),
                                               mode="single_file", index=0, seed=0, label="", dry_run=True)

    assert fname == "test.png"
    assert status == "processed"
    assert images is not None

def test_process_non_image_bypassed(tmp_path: Path):
    batch = tmp_path / "batch"
    processed = tmp_path / "processed"
    bypass = tmp_path / "bypass"
    batch.mkdir()
    processed.mkdir()
    bypass.mkdir()

    txt_path = batch / "hello.txt"
    txt_path.write_text("not-an-image")

    node = LoadAndProcessImageBatch()

    images, fname, status = node.process_next(str(batch), str(processed), str(bypass),
                                               mode="single_file", index=0, seed=0, label="", dry_run=False)

    assert not (batch / "hello.txt").exists()
    assert (bypass / "hello.txt").exists()
    assert fname == "hello.txt"
    assert status.startswith("bypassed")
    assert images is None

# --- Tests that use example HEIC and NEF files from the examples folder ---
EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "nodes" / "comfyjbb_load_process_batch" / "examples"

def test_process_heic_example(tmp_path: Path, monkeypatch):
    heic_path = EXAMPLES_DIR / "TEST.heic"
    if not heic_path.exists():
        pytest.skip("No TEST.heic example available")

    def fake_pillow(func, path, *args, **kwargs):
        return PILImage.new("RGB", (32, 32), (100, 150, 200))

    monkeypatch.setattr(node_helpers, "pillow", fake_pillow)

    batch = tmp_path / "batch"
    processed = tmp_path / "processed"
    bypass = tmp_path / "bypass"
    batch.mkdir()
    processed.mkdir()
    bypass.mkdir()

    target = batch / "TEST.heic"
    import shutil
    shutil.copy2(str(heic_path), str(target))

    node = LoadAndProcessImageBatch()

    images, fname, status = node.process_next(str(batch), str(processed), str(bypass),
                                               mode="single_file", index=0, seed=0, label="", dry_run=True)

    assert fname == "TEST.heic"
    assert status == "processed"
    assert images is not None

def test_process_nef_example(tmp_path: Path, monkeypatch):
    nef_path = EXAMPLES_DIR / "TEST.NEF"
    if not nef_path.exists():
        pytest.skip("No TEST.NEF example available")

    class DummyRaw:
        def postprocess(self, use_camera_wb=True, output_bps=8):
            arr = np.zeros((16, 16, 3), dtype=np.uint8)
            arr[:, :] = [50, 100, 150]
            return arr

    dummy_rawpy = types.ModuleType("rawpy")
    def imread(path):
        return DummyRaw()
    dummy_rawpy.imread = imread
    sys.modules["rawpy"] = dummy_rawpy

    batch = tmp_path / "batch"
    processed = tmp_path / "processed"
    bypass = tmp_path / "bypass"
    batch.mkdir()
    processed.mkdir()
    bypass.mkdir()

    target = batch / "TEST.NEF"
    import shutil
    shutil.copy2(str(nef_path), str(target))

    node = LoadAndProcessImageBatch()

    images, fname, status = node.process_next(str(batch), str(processed), str(bypass),
                                               mode="single_file", index=0, seed=0, label="", dry_run=True)

    assert fname == "TEST.NEF"
    assert status == "processed"
    assert images is not None
