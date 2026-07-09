param(
  [string]$CustomNodesDir = "D:\ComfyUI\custom_nodes\comfyui-custom-nodes-jbb",
  [string]$PythonExe = "python"
)

$RepoRoot = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent

Write-Host "Copying nodes to $CustomNodesDir"
New-Item -ItemType Directory -Force -Path $CustomNodesDir | Out-Null
Copy-Item -Path (Join-Path $RepoRoot 'nodes\*') -Destination $CustomNodesDir -Recurse -Force

$req = Join-Path $RepoRoot 'nodes\\comfyjbb_load_process_batch\\requirements.txt'
if (Test-Path $req) {
  Write-Host "Installing optional requirements using $PythonExe"
  & $PythonExe -m pip install --upgrade pip
  & $PythonExe -m pip install -r $req
}

Write-Host "Done. Restart ComfyUI."
