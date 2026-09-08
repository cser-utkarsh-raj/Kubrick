@echo off
setlocal
cd /d "%~dp0"

echo.
echo  KUBRICK - local desktop editor
 echo.

if not exist "pyproject.toml" (
  echo ERROR: pyproject.toml was not found.
  echo Run this file from the cloned Kubrick repository.
  pause
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11+ was not found on PATH.
  echo Install Python 3.11 or newer, then run this file again.
  pause
  exit /b 1
)

python -m pip install -e ".[gui]"
if errorlevel 1 (
  echo.
  echo ERROR: Kubrick dependencies could not be installed.
  pause
  exit /b 1
)

echo.
echo Starting Kubrick...
python -m kubrick.ui.app
if errorlevel 1 (
  echo.
  echo Kubrick exited with an error.
  pause
  exit /b 1
)
