# Building Kubrick for desktop

Kubrick is developed as a Python/PySide6 desktop application and can also be packaged as a native executable.

## Development mode

```bash
python -m pip install -e ".[gui]"
kubrick-gui
```

This is the easiest way to develop and test the editor. It requires Python 3.11+ and FFmpeg/FFprobe on `PATH`.

## Windows executable

Kubrick uses Qt for Python's `pyside6-deploy` path for desktop packaging. Qt documents that `pyside6-deploy` produces a Windows `.exe`, Linux `.bin`, and macOS `.app`. It wraps Nuitka for the application bundle. citeturn0search1

Install the deployment tool in the GUI environment, then from the repository root:

```powershell
python -m pip install -e ".[gui]"
pyside6-deploy kubrick/ui/app.py --mode onefile --name Kubrick
```

For a smaller startup footprint, use standalone mode instead of onefile:

```powershell
pyside6-deploy kubrick/ui/app.py --mode standalone --name Kubrick
```

### Important: FFmpeg is a runtime dependency

The application bundle contains the Kubrick/PySide6 side of the program, but **FFmpeg and FFprobe are media-engine dependencies**. For a public Windows release, Kubrick should ship them in a controlled `bin/` directory or use a first-run dependency installer. Do not assume a user's machine already has FFmpeg.

The release packaging task therefore remains:

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

The desktop editor is already usable for the core workflow, but packaging is not yet a signed, polished installer. Before calling Kubrick release-ready, add:

- bundled FFmpeg/FFprobe
- first-run dependency check
- Windows `.exe` build in CI
- installer/signing
- macOS `.app` packaging
- Linux package/AppImage
- end-to-end fixture renders
- crash-safe temporary-file cleanup
