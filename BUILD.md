# Building Kubrick for desktop

Kubrick is developed as a Python/PySide6 desktop application and can also be packaged as a native executable.

## Windows: run the editor in development mode

The install command must be run **inside the cloned Kubrick repository**, where `pyproject.toml` exists.

For example, if the repository is at `C:\Users\u_raj\Kubrick`:

```powershell
cd /d C:\Users\u_raj\Kubrick
dir pyproject.toml
python -m pip install -e ".[gui]"
python -m kubrick.ui.app
```

After the editable install, this should also work in a terminal where Python's Scripts directory is on `PATH`:

```powershell
kubrick-gui
```

If `python -m pip install -e ".[gui]"` says that the directory is not a Python project, check `cd` first. Running it from `C:\Users\u_raj` instead of `C:\Users\u_raj\Kubrick` produces that error because the parent folder has no `pyproject.toml`.

Development mode requires Python 3.11+ and FFmpeg/FFprobe on `PATH`.

### One-command Windows launcher

From the cloned repository, you can also double-click `run-kubrick.bat`. It changes into the repository automatically, verifies Python and `pyproject.toml`, installs the GUI extra, and starts the editor.

## Getting the repository

If Kubrick has not been cloned yet:

```powershell
git clone https://github.com/cser-utkarsh-raj/Kubrick.git
cd /d Kubrick
python -m pip install -e ".[gui]"
python -m kubrick.ui.app
```

## Editor workflow shortcuts

The desktop editor supports a small set of high-value shortcuts without turning into a keyboard-heavy NLE:

| Shortcut | Action |
|---|---|
| `Space` | Play / pause |
| `Left` / `Right` | Nudge 100 ms |
| `Shift + Left` / `Shift + Right` | Nudge 1 s |
| `I` | Set cut in-point to playhead |
| `O` | Set cut out-point to playhead |
| `Ctrl + Z` | Undo |
| `Ctrl + Shift + Z` | Redo |
| Click timeline | Seek |
| Drag audio/text/image/shape | Move the layer on the shared timeline |
| `Ctrl + mouse wheel` | Timeline zoom |

The main video track remains sequential; draggable secondary layers are constrained to the project duration.

## Windows executable

Kubrick uses Qt for Python's `pyside6-deploy` path for desktop packaging. The deployment tool can produce a Windows `.exe`, Linux `.bin`, or macOS `.app` and uses Nuitka underneath.

From the repository root:

```powershell
python -m pip install -e ".[gui]"
pyside6-deploy kubrick/ui/app.py --mode onefile --name Kubrick
```

For a standalone directory build:

```powershell
pyside6-deploy kubrick/ui/app.py --mode standalone --name Kubrick
```

## Important: FFmpeg is a runtime dependency

The application bundle contains the Kubrick/PySide6 side of the program, but **FFmpeg and FFprobe are media-engine dependencies**. For a public Windows release, Kubrick should ship them in a controlled `bin/` directory or use a first-run dependency installer. Do not assume a user's machine already has FFmpeg.

The release packaging target is:

```text
Kubrick.exe
bin/
  ffmpeg.exe
  ffprobe.exe
```

The application should resolve those binaries from its own bundle before falling back to `PATH`.

## What users should eventually get

The intended release experience is **not**:

```text
install Python
install packages
open CMD
run a command
```

It is:

```text
Download Kubrick.exe
        ↓
Double-click
        ↓
Kubrick editor opens
        ↓
Import video
        ↓
Auto Edit / Edit / Render
```

The CLI remains available for power users and automation.

## Practical hardware target

These are engineering targets rather than certified vendor requirements.

### Minimum practical

- Windows 10/11, macOS or modern Linux
- 64-bit 2-core CPU
- 4 GB RAM
- roughly 1 GB for application/dependencies plus free media working space
- no dedicated GPU required
- FFmpeg + FFprobe

### Recommended

- 4+ modern CPU cores
- 8–16 GB RAM
- SSD
- 1080p H.264/H.265 source for a comfortable baseline
- more RAM/CPU if local speech transcription is enabled

The application is lightweight compared with a full professional NLE. **Rendering is not lightweight**: H.264/H.265 encoding can consume significant CPU time, and temporary disk usage grows with project size.

## Current release reality

The repository now has a real interactive multi-track timeline, keyboard transport/edit controls, project validation, atomic project saves, relative-media resolution, real FFmpeg fixture coverage and a headless Qt startup gate. The remaining release blockers are **user-environment validation and packaging**, not the basic editing engine.

Before calling the Windows release complete, add and verify:

- bundled FFmpeg/FFprobe
- first-run dependency check
- Windows `.exe` build in CI
- installer/signing
- macOS `.app` packaging
- Linux package/AppImage
- crash-safe temporary-file cleanup around the full render lifecycle
- user testing with real Windows media and hardware
