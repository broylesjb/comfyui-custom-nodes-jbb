# comfyui-custom-nodes-jbb

This repository contains a collection of custom ComfyUI nodes and helpers developed as the "COMFYJBB" node suite. The nodes focus on flexible image loading and batch processing, with support for HEIC/HEIF and a set of RAW camera formats where optional dependencies are installed.

This README documents what is included in the repo, how the custom nodes work, installation steps for adding the suite to your ComfyUI installation, dependency notes, usage hints, and troubleshooting steps.

---

## Included nodes (summary)

- COMFYJBB: Load & Process Image Batch
  - Location: `nodes/comfyjbb_load_process_batch/nodes.py` (also exposed in top-level `nodes/nodes.py` mapping)
  - What it does: scans a configured batch directory and processes files one at a time (queue semantics). It routes files by extension to the appropriate loader:
    - Common images (.png, .jpg, .jpeg, .webp, .bmp) — loaded by Pillow or ComfyUI InputImpl if available
    - HEIC (.heic) — attempted via ComfyUI InputImpl, otherwise falls back to pillow-heif if present
    - RAW camera files (.arw, .cr2, .cr3, .dng, .nef, .raf, .raw) — loaded with `rawpy` when available
    - Other extensions — moved to a Bypass folder and skipped
  - Key features: incremental/random/single-file selection modes; atomic "claiming" of files via rename to avoid concurrent processing; moves processed files to a processed folder and bypassed files to bypass folder; returns image tensor and filename.
  - Defaults: batch path and processed/bypass defaults are set to `/workspace/ComfyUI/InputBatch/...` but are configurable in the node.
  - Dependencies (optional): `rawpy`, `pillow-heif` (listed in `nodes/comfyjbb_load_process_batch/requirements.txt`).

- ComfyUI Load Image (HEIC)
  - Location: `nodes/comfyui_loadheicimagefrompath/`
  - What it does: a replacement/enhanced "Load Image" node that additionally supports `.heic`/`.heif` files and integrates with ComfyUI's input directory handling. Provides similar outputs to the standard "Load Image" node (IMAGE, MASK).
  - Usage notes: drag-and-drop is the most reliable way to upload HEIC files into ComfyUI's input folder; file picker upload may be filtered by UI.
  - Dependencies (optional): `pillow-heif` or other HEIC handling library in the same Python env as ComfyUI.

- ComfyUI Load Image from Path
  - Location: `nodes/comfyui_loadimagefrompath/`
  - What it does: simple helper node to load image files by name/path from ComfyUI's configured input or project folders. Useful when composing workflows that need programmatic image lookup.

- ComfyUI RAW Image from Path
  - Location: `nodes/comfyui_raw_image_frompath/`
  - What it does: loads RAW camera files using `rawpy` and returns an image array/tensor suitable for downstream nodes.
  - Dependencies: requires `rawpy` to be installed in the same Python environment as ComfyUI.

- Top-level helper (legacy mapping)
  - Location: `nodes/nodes.py`
  - What it does: provides a mapping for the node class to display name and may expose the Load & Process Image Batch node at a top-level import path used by some installations.

---

## Installation (recommended)

Choose one of the following methods depending on how you manage your ComfyUI installation.

Option A — Manual copy (simple)
1. Locate your ComfyUI installation directory. Example paths (your path may differ):
   - Windows: `D:\ComfyUI\custom_nodes\`
   - Linux: `/home/<you>/ComfyUI/custom_nodes/`
2. Copy the entire repository (or only the `nodes/` subfolders) into the ComfyUI `custom_nodes` directory. Example (PowerShell):

   pwsh (PowerShell)
   cd C:\path\to\this\repo
   xcopy /E /I nodes C:\path\to\ComfyUI\custom_nodes\comfyui-custom-nodes-jbb

   or on Linux/macOS (bash)
   cp -r nodes "$HOME/ComfyUI/custom_nodes/comfyui-custom-nodes-jbb"

3. Ensure the copied folders (e.g. `comfyjbb-load-process-batch`, `comfyui-loadheicimagefrompath`, ...) are present inside `custom_nodes`.
4. Install optional dependencies into the same Python environment used by ComfyUI (see Dependencies below).
5. Restart ComfyUI — the new nodes should appear in the node list under their categories (see node README files for category names).

Option B — Git clone into custom_nodes (recommended for easy updates)
1. In your ComfyUI `custom_nodes` folder run:

   pwsh
   cd C:\path\to\ComfyUI\custom_nodes
   git clone https://github.com/Composed-Solutions-LLC/comfyui-custom-nodes-jbb.git

2. Install optional dependencies into the ComfyUI Python environment.
3. Restart ComfyUI.

Option C — Development (symlink)
- On Linux/macOS, you can create a symbolic link from the repo working directory to your ComfyUI `custom_nodes` folder so changes are picked up without re-copying.

---

## Dependencies

- Required at runtime by ComfyUI core: none of the nodes strictly require extra packages to avoid import errors; they attempt to use optional packages when available.
- Optional (recommended for full feature set):
  - `pillow` (PIL) — standard image handling (most ComfyUI installs already have this)
  - `pillow-heif` — HEIC/HEIF read support if InputImpl or system support is absent
  - `rawpy` — for RAW camera formats
  - `numpy` — array handling (typical in ComfyUI)
  - `torch` — used by the batch node to return tensors; ComfyUI typically provides torch in its environment

To install optional requirements for the batch node (PowerShell/batch environment used by ComfyUI):

pwsh
# use the same Python interpreter/environment that runs ComfyUI
python -m pip install --upgrade pip
python -m pip install -r nodes/comfyjbb_load_process_batch/requirements.txt

If you do not want to install optional libs, the nodes will try to handle missing libs gracefully and will move files to a bypass folder or raise a runtime message, but the core image-loading paths (PNG/JPG) should still work via Pillow.

---

## Running tests (developer)

This repo contains pytest tests located in `tests/`. To run tests locally in a Python venv (not the ComfyUI runtime), use:

pwsh
cd <repo-root>
python -m venv .venv
.venv\Scripts\Activate.ps1    # PowerShell on Windows
python -m pip install --upgrade pip
python -m pip install Pillow pytest numpy
# Optional: install CPU-only torch if you want the tests to use torch
pip install torch --index-url https://download.pytorch.org/whl/cpu
pytest -q

Note: tests mock ComfyUI internals so you do not need a running ComfyUI to run them.

---

## Usage notes & node-specific guidance

- Load & Process Image Batch
  - Set `batch_path` to a folder where you will place images to be processed.
  - `mode` controls how the next file is selected: `incremental` (first), `random` (seedable), `single_file` (by index).
  - `dry_run=true` will process without moving files — useful for testing with the node outputs only.
  - If `rawpy` or `pillow-heif` are missing, RAW and HEIC files will be bypassed and moved to the Bypass folder; ensure you install those libs into the ComfyUI Python environment for full behavior.

- HEIC loader node
  - Drag & drop HEIC files into ComfyUI's input folder, or use the node's UI to choose images located in the input folder.
  - If you see UI issues with drag & drop being interpreted as workflow drops, try selecting the node first and then dropping files onto it.

---

## Troubleshooting

- Node does not appear in ComfyUI UI after installation: Restart ComfyUI; verify the folder is inside `<ComfyUI>/custom_nodes/` and not nested incorrectly.
- ImportError / ModuleNotFoundError errors: Ensure optional dependencies are installed into the same Python environment that ComfyUI runs in.
- Files are immediately moved to Bypass: Check the ComfyUI server logs — nodes will move files when optional loaders are missing or when a file extension isn't supported.

---

## Contributing

Contributions welcome. Please open issues or pull requests. If you add new nodes, update this README and the `nodes/` subfolder README files.

---

## License

See the top-level `LICENSE` file in this repository.

