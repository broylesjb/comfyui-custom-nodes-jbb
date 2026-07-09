@echo off
REM install.bat - copy nodes to ComfyUI custom_nodes and optionally install requirements
REM Usage: install.bat [destination_custom_nodes_dir] [python_exe]
SETLOCAL

SET REPO_DIR=%~dp0
SET DEST=%1
IF "%DEST%"=="" (
  SET DEST=%USERPROFILE%\ComfyUI\custom_nodes\comfyui-custom-nodes-jbb
)

SET PYEXE=%2
IF "%PYEXE%"=="" (
  SET PYEXE=python
)

echo Copying nodes to "%DEST%"
mkdir "%DEST%" 2>NUL
xcopy "%REPO_DIR%\nodes\*" "%DEST%\" /E /I /Y >nul

IF EXIST "%REPO_DIR%\nodes\\comfyjbb_load_process_batch\\requirements.txt" (
  echo Installing optional requirements for batch node...
  "%PYEXE%" -m pip install --upgrade pip
  "%PYEXE%" -m pip install -r "%REPO_DIR%\nodes\\comfyjbb_load_process_batch\\requirements.txt"
)

echo Done. Restart ComfyUI to load new custom nodes.
ENDLOCAL
