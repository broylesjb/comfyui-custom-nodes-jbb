# apply_packaging_and_ci.ps1
# Run from repo root. Creates packaging/CI/installer files, branch, commit & push.
Param(
  [string]$BranchName = "chore/packaging-and-ci",
  [string]$Remote = "origin"
)

# Safety: confirm location
Write-Host "Running in: $(Get-Location)"
if (-not (Test-Path .git)) {
  Write-Error "This does not appear to be a git repository root (no .git). Aborting."
  exit 1
}

# Create files
# .gitattributes
$g = @'
* text=auto
*.py     text eol=lf
*.md     text eol=lf
*.yml    text eol=lf
*.yaml   text eol=lf
*.sh     text eol=lf
*.ps1    text eol=crlf
*.bat    text eol=crlf
'@
Set-Content -Path .\.gitattributes -Value $g -Encoding utf8

# LICENSE (MIT)
$lic = @'
MIT License

Copyright (c) 2026 Composed Solutions LLC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'@
Set-Content -Path .\LICENSE -Value $lic -Encoding utf8

# CI workflow
New-Item -ItemType Directory -Force -Path .github\workflows | Out-Null
$ci = @'
name: CI — pytest

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pillow pytest numpy
          # optional: install torch CPU wheel in CI if needed (uncomment if you want to test with torch)
          # pip install --index-url https://download.pytorch.org/whl/cpu torch

      - name: Run tests
        run: |
          pytest -q
'@
Set-Content -Path .\.github\workflows\pytest.yml -Value $ci -Encoding utf8

# install.sh
$sh = @'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CUSTOM_NODES_DIR="${1:-$HOME/ComfyUI/custom_nodes/comfyui-custom-nodes-jbb}"
PYTHON_BIN="${2:-python}"

echo "Copying nodes to ${CUSTOM_NODES_DIR}"
mkdir -p "${CUSTOM_NODES_DIR}"
cp -r "${REPO_DIR}/nodes"/* "${CUSTOM_NODES_DIR}/"

echo "Installing optional requirements for batch node (if desired)"
if [ -f "${REPO_DIR}/nodes/comfyjbb-load-process-batch/requirements.txt" ]; then
  "${PYTHON_BIN}" -m pip install --upgrade pip
  "${PYTHON_BIN}" -m pip install -r "${REPO_DIR}/nodes/comfyjbb-load-process-batch/requirements.txt"
fi

echo "Done. Restart ComfyUI to load new custom nodes."
'@
Set-Content -Path .\install.sh -Value $sh -Encoding utf8

# install.ps1
$ps1 = @'
param(
  [string]$CustomNodesDir = "D:\ComfyUI\custom_nodes\comfyui-custom-nodes-jbb",
  [string]$PythonExe = "python"
)

$RepoRoot = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent

Write-Host "Copying nodes to $CustomNodesDir"
New-Item -ItemType Directory -Force -Path $CustomNodesDir | Out-Null
Copy-Item -Path (Join-Path $RepoRoot 'nodes\*') -Destination $CustomNodesDir -Recurse -Force

$req = Join-Path $RepoRoot 'nodes\comfyjbb-load-process-batch\requirements.txt'
if (Test-Path $req) {
  Write-Host "Installing optional requirements using $PythonExe"
  & $PythonExe -m pip install --upgrade pip
  & $PythonExe -m pip install -r $req
}

Write-Host "Done. Restart ComfyUI."
'@
Set-Content -Path .\install.ps1 -Value $ps1 -Encoding utf8

# pyproject.toml
$py = @'
[project]
name = "comfyui-custom-nodes-jbb"
version = "0.1.0"
description = "COMFYJBB custom nodes for ComfyUI"
readme = "README.md"
authors = [ { name="Composed Solutions LLC" } ]
license = { text = "MIT" }
requires-python = ">=3.10"

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
'@
Set-Content -Path .\pyproject.toml -Value $py -Encoding utf8

# Create shim packages under nodes/
New-Item -ItemType Directory -Force -Path .\nodes\comfyjbb_load_process_batch | Out-Null
$shim1 = @'
"""Shim package to expose the nodes in the `comfyjbb-load-process-batch` folder
under the importable package name `comfyjbb_load_process_batch`."""
import importlib.util
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_hyphen_dir = _pkg_dir.parent / "comfyjbb-load-process-batch"
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
'@
Set-Content -Path .\nodes\comfyjbb_load_process_batch\__init__.py -Value $shim1 -Encoding utf8

New-Item -ItemType Directory -Force -Path .\nodes\comfyui_loadheicimagefrompath | Out-Null
$shim2 = @'
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
'@
Set-Content -Path .\nodes\comfyui_loadheicimagefrompath\__init__.py -Value $shim2 -Encoding utf8

New-Item -ItemType Directory -Force -Path .\nodes\comfyui_loadimagefrompath | Out-Null
$shim3 = @'
"""Shim package to expose the nodes in the `comfyui-loadimagefrompath` folder
under the importable package name `comfyui_loadimagefrompath`."""
import importlib.util
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_hyphen_dir = _pkg_dir.parent / "comfyui-loadimagefrompath"
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
'@
Set-Content -Path .\nodes\comfyui_loadimagefrompath\__init__.py -Value $shim3 -Encoding utf8

New-Item -ItemType Directory -Force -Path .\nodes\comfyui_raw_image_frompath | Out-Null
$shim4 = @'
"""Shim package to expose the nodes in the `comfyui-raw-image-frompath` folder
under the importable package name `comfyui_raw_image_frompath`."""
import importlib.util
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_hyphen_dir = _pkg_dir.parent / "comfyui-raw-image-frompath"
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
'@
Set-Content -Path .\nodes\comfyui_raw_image_frompath\__init__.py -Value $shim4 -Encoding utf8

# Git operations: create branch, add, commit, push
git checkout -b $BranchName

git add .gitattributes LICENSE .github\workflows\pytest.yml install.sh install.ps1 pyproject.toml nodes\comfyjbb_load_process_batch\__init__.py nodes\comfyui_loadheicimagefrompath\__init__.py nodes\comfyui_loadimagefrompath\__init__.py nodes\comfyui_raw_image_frompath\__init__.py

git commit -m "Add packaging metadata, CI, installer scripts, gitattributes, LICENSE, and import shims"

git push $Remote $BranchName

Write-Host "Done. Branch pushed: $Remote/$BranchName"
Write-Host "Next: create a PR from this branch to main (see instructions in script output)."