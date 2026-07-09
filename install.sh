#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CUSTOM_NODES_DIR="${1:-$HOME/ComfyUI/custom_nodes/comfyui-custom-nodes-jbb}"
PYTHON_BIN="${2:-python}"

echo "Copying nodes to ${CUSTOM_NODES_DIR}"
mkdir -p "${CUSTOM_NODES_DIR}"
cp -r "${REPO_DIR}/nodes"/* "${CUSTOM_NODES_DIR}/"

echo "Installing optional requirements for batch node (if desired)"
if [ -f "${REPO_DIR}/nodes/comfyjbb_load_process_batch/requirements.txt" ]; then
  "${PYTHON_BIN}" -m pip install --upgrade pip
  "${PYTHON_BIN}" -m pip install -r "${REPO_DIR}/nodes/comfyjbb_load_process_batch/requirements.txt"
fi

echo "Done. Restart ComfyUI to load new custom nodes."
