# 🚀 Kubrick Studio - Quick Start Guide

**Your personal video editing studio is ready!**

---

## One Command to Rule Them All

```bash
./run_kubrick_studio.sh
# OR
python kubrick_studio.py
```

This launches the **Kubrick Studio Launcher** with:
- ✅ Automatic system checks
- ✅ Dependency validation  
- ✅ Interactive menu
- ✅ Built-in testing

---

## Menu Options

When you launch, you'll see:

```
╔═══════════════════════════════════════════════════════╗
║           KUBRICK STUDIO - Personal Edition           ║
╚═══════════════════════════════════════════════════════╝

Options:
  1. Launch GUI Editor       → Visual timeline editing
  2. Use CLI                 → Command-line power mode
  3. Run Diagnostics         → Check all systems
  4. Quick Test              → End-to-end verification
  5. Open Workspace          → Your project folder
  0. Exit                    → Goodbye!
```

---

## Fastest Way to Edit a Video

### Method A: One-Liner (CLI)
```bash
kubrick render my_video.mp4 edited.mp4 --profile natural
```

### Method B: Interactive (Launcher)
```bash
python kubrick_studio.py
# Choose option 2 for CLI mode
# Type: render my_video.mp4 edited.mp4 --profile natural
```

### Method C: Visual (GUI)
```bash
python kubrick_studio.py
# Choose option 1
# Import video → Click "Auto Edit" → Render
```

---

## Editing Profiles Cheat Sheet

| Command | Removes | Best For |
|---------|---------|----------|
| `--profile gentle` | Only long silences (>2s) | Podcasts, interviews |
| `--profile natural` | Moderate pauses (default) | Tutorials, lectures |
| `--profile tight` | All dead air | TikTok, Reels, YouTube Shorts |

---

## Common Tasks

### See what will be cut (without rendering)
```bash
kubrick analyze video.mp4 --profile natural
```

### Create editable project for fine-tuning
```bash
kubrick new-project video.mp4 project.kubrick.json
```

### Validate project before rendering
```bash
kubrick validate-project project.kubrick.json
```

### Render with custom quality
```bash
kubrick render-project project.kubrick.json output.mp4 --crf 18
```
Lower CRF = higher quality (18-28 recommended)

---

## Troubleshooting in 30 Seconds

**Problem**: "FFmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from ffmpeg.org and add to PATH
```

**Problem**: "PySide6 import error"
```bash
pip install "pyside6>=6.8"
```

**Problem**: GUI won't open on Linux
```bash
sudo apt install libegl1 libxcb-xinerama0
```

**Problem**: Want to test everything works
```bash
python kubrick_studio.py
# Select option 3 (Diagnostics)
# Select option 4 (Quick Test)
```

---

## Your Workspace

Projects are saved in: `~/KubrickProjects/`

Open it anytime via launcher option 5.

---

## Pro Tips

1. **Always analyze first** - See what will be cut before committing
2. **Use projects for important edits** - Non-destructive = safety net
3. **Tight profile for social media** - Maximum engagement
4. **Gentle profile for podcasts** - Keep it conversational
5. **Run diagnostics monthly** - Keep everything healthy

---

## Next Steps

1. ✅ Run `python kubrick_studio.py`
2. ✅ Try option 4 (Quick Test) to verify everything works
3. ✅ Drop a video in `~/KubrickProjects/`
4. ✅ Edit it with option 1 (GUI) or option 2 (CLI)
5. 🎬 Enjoy your time back!

---

**Need help?** Run diagnostics (option 3) first - it catches 90% of issues.

**Made for you. Made to work. Made to last.** ❤️
