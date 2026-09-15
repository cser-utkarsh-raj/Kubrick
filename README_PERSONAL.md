# Kubrick Studio - Personal Edition

**Precision-first local video editing engine with automatic silence removal**

## 🎬 What is Kubrick?

Kubrick is a lightweight, local-first video editor that automatically removes dead air, pauses, and filler words from tutorial/lecture/presentation videos. It uses FFmpeg for processing and optional Whisper AI for transcription-based editing.

### Key Features

- ✂️ **Automatic Silence Detection** - Finds and removes silent segments
- 🎯 **Smart Editing Profiles** - Gentle, Natural, Tight presets
- 🔒 **100% Local & Private** - No cloud uploads, all processing on your machine
- 📊 **Non-Destructive Editing** - Edit projects before rendering
- 🖥️ **Dual Interface** - CLI for automation, GUI for visual editing
- 🧠 **AI-Powered** (optional) - Whisper transcription for intelligent cuts

---

## ⚡ Quick Start

### Prerequisites

1. **Python 3.11+** 
2. **FFmpeg** - [Download here](https://ffmpeg.org/download.html)

### Installation

```bash
# Clone or download this repository
cd kubrick

# Install with all features (GUI + AI transcription)
pip install -e ".[all]"

# Or minimal installation (CLI only)
pip install -e .
```

### Launch the Studio Launcher

```bash
python kubrick_studio.py
```

This provides a user-friendly menu to:
- Launch the GUI editor
- Use CLI commands interactively  
- Run system diagnostics
- Test end-to-end functionality
- Open your workspace folder

---

## 📖 Usage

### Command Line (CLI)

#### Automatically edit and render a video:
```bash
kubrick render input.mp4 output.mp4 --profile natural
```

#### Analyze without rendering:
```bash
kubrick analyze video.mp4 --profile tight --json report.json
```

#### Create an editable project:
```bash
kubrick new-project source.mp4 myproject.kubrick.json
```

#### Validate a project:
```bash
kubrick validate-project myproject.kubrick.json
```

#### Render a project:
```bash
kubrick render-project myproject.kubrick.json final.mp4
```

### Editing Profiles

| Profile | Best For | Behavior |
|---------|----------|----------|
| `gentle` | Podcasts, interviews | Minimal cuts, preserves natural pauses |
| `natural` | Tutorials, lectures (default) | Balanced silence removal |
| `tight` | Fast-paced content | Aggressive cutting, maximum time savings |

### GUI Editor

Launch via the studio launcher (option 1) or directly:

```bash
kubrick-gui
```

**Features:**
- Visual timeline with clip management
- Real-time preview player
- Drag-and-drop layers (text, images, audio)
- In/Out point selection
- Undo/Redo history
- Auto-edit button for one-click optimization
- Export settings control

---

## 🧪 Testing

Run the full test suite:

```bash
python -m pytest tests/ -v
```

Run quick end-to-end test:

```bash
python kubrick_studio.py
# Select option 4
```

---

## 🛠️ Troubleshooting

### "FFmpeg not found"
Install FFmpeg:
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` or `sudo dnf install ffmpeg`

### "PySide6 import error"
Install GUI dependencies:
```bash
pip install "pyside6>=6.8"
```

### "faster-whisper not available"
Install AI transcription (optional):
```bash
pip install "faster-whisper>=1.2"
```

### GUI won't start on Linux
Install system dependencies:
```bash
sudo apt install libegl1 libxcb-xinerama0 libxcb-cursor0
```

---

## 📁 Project Structure

```
kubrick/
├── kubrick_studio.py      # Personal launcher (YOU ARE HERE)
├── index.py               # Web server entry point
├── pyproject.toml         # Package configuration
├── kubrick/
│   ├── core/              # Project models & state
│   ├── editor/            # Editing operations
│   ├── media/             # FFmpeg integration
│   ├── speech/            # Whisper transcription
│   └── ui/                # PySide6 GUI
└── tests/                 # Test suite
```

---

## 🎯 Workflow Example

### Scenario: Edit a 30-minute lecture recording

1. **Analyze first** (see what will be cut):
   ```bash
   kubrick analyze lecture.mp4 --profile natural
   ```

2. **Create editable project** (for manual adjustments):
   ```bash
   kubrick new-project lecture.mp4 lecture.kubrick.json
   ```

3. **Open in GUI** for fine-tuning:
   ```bash
   kubrick-gui
   # File → Open → lecture.kubrick.json
   # Adjust clips, add overlays, etc.
   # File → Save
   ```

4. **Render final version**:
   ```bash
   kubrick render-project lecture.kubrick.json lecture_edited.mp4
   ```

### One-liner for quick edits:
```bash
kubrick render lecture.mp4 lecture_edited.mp4 --profile natural
```

---

## 📝 Technical Details

### How Silence Detection Works

Kubrick uses FFmpeg's `silencedetect` filter to identify low-energy audio segments:
- Configurable noise threshold (default: -38dB)
- Minimum silence duration (default: 0.65s)
- Intelligently preserves brief pauses for natural cadence

### Rendering Pipeline

1. **Analysis** - Detect silences and plan cuts
2. **Decision Engine** - Apply profile rules to determine trim points
3. **Project Generation** - Create non-destructive edit decision list
4. **FFmpeg Processing** - Execute cuts with high-quality encoding

### Performance

- Processes ~1 minute of video per 5-10 seconds (depends on hardware)
- Multi-threaded encoding via FFmpeg
- GPU acceleration available if FFmpeg compiled with NVENC/VAAPI

---

## 🤝 Contributing

This is a personal production setup. To extend:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit changes

---

## 📄 License

This is a **personal production instance**. All rights reserved.

For licensing questions or commercial use inquiries, contact the maintainer.

---

## 🙏 Credits

Built with:
- [FFmpeg](https://ffmpeg.org/) - Media processing backbone
- [PySide6](https://doc.qt.io/qtforpython-6/) - GUI framework
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - AI transcription
- [NumPy](https://numpy.org/) - Audio analysis

Inspired by professional film editing workflows and modern creator tools.

---

**Made with ❤️ for creators who value their time**

*Last updated: 2025*
