# COMFYJBB: Load & Process Image Batch

This node processes files in a batch folder and routes loading by file extension:
- Images (.png/.jpg/.jpeg/.webp/.bmp) -> standard image loader
- HEIC (.heic) -> HEIC loader (via InputImpl/pillow-heif if available)
- RAW camera formats (.arw/.cr2/.cr3/.dng/.nef/.raf/.raw) -> rawpy (if installed)
- Other extensions are moved to the Bypass folder.

Defaults:
- Batch Path: /workspace/ComfyUI/InputBatch/
- Processed Path: /workspace/ComfyUI/InputBatch/processed/
- Bypass Path: /workspace/ComfyUI/InputBatch/Bypass/

Modes:
- incremental (default): treat the folder as a queue; process the first file each run.
- random: pick a random file from current listing (seed supported).
- single_file: pick a file by index (index is volatile when files are moved).

Note: The node attempts to claim files via an atomic rename to avoid concurrent processing conflicts. If rawpy or pillow-heif are not installed, the node will move RAW/HEIC files to bypass and log an error.
