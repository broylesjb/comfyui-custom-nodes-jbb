"""Shim package to expose the nodes in the `comfyui-loadheicimagefrompath` folder
under the importable package name `comfyui_loadheicimagefrompath`."""
import importlib.util
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_hyphen_dir = _pkg_dir.parent / "comfyui-loadheicimagefrompath"
_nodes_py = _hyphen_dir / "nodes.py"
if not _nodes_py.exists():
    raise ImportError(f"Could not find {str(_nodes_py)}")

spec = importlib.util.spec_from_file_location(__name__ + ".nodes", str(_nodes_py))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

for k, v in mod.__dict__.items():
    if not k.startswith("_"):
        globals()[k] = v

__all__ = [k for k in globals().keys() if not k.startswith("_")]
