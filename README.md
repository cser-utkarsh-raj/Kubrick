# KUBRICK

> **Cut the noise. Reveal the story.**

**Kubrick** is a precision-first local video editing engine for real footage. It combines deterministic media analysis with a small, editable project model and FFmpeg compositor so common editing jobs can be automated without hiding the edit from the user.

Lectures. Tutorials. Presentations. Interviews. Courses. Explainers. Creator recordings.

[![CI](https://github.com/cser-utkarsh-raj/Kubrick/actions/workflows/ci.yml/badge.svg)](https://github.com/cser-utkarsh-raj/Kubrick/actions/workflows/ci.yml)

---

## What Kubrick is becoming

Kubrick is deliberately **not** trying to become a giant Premiere clone.

The target is a focused editor that does the boring work extremely well:

- cut and trim clips
- merge clips into a clean timeline
- remove dead air automatically
- preserve A/V sync while editing
- apply reusable visual presets and FFmpeg filters
- mix extra audio with volume and fades
- place timed text, images and shapes over footage
- save the whole edit as a portable JSON project
- render the project locally with FFmpeg
- inspect automatic decisions before committing them

The design principle is simple:

> **Be aggressive with objective friction. Be conservative with human meaning.**

---

## Automatic editing pipeline

```text
SOURCE FOOTAGE
      │
      ├── Audio ───── silence / pauses
      ├── Speech ──── fillers / false starts / repetition   (optional)
      └── Visual ──── scenes / blackouts / freezes
                    │
                    ▼
             EDITORIAL POLICY
                    │
          KEEP / COMPRESS / CUT / REVIEW
                    │
                    ▼
            EDITABLE PROJECT
          clips + filters + layers
                    │
                    ▼
             FFmpeg COMPOSITOR
                    │
                    ▼
             SYNCHRONIZED MP4
```

The important distinction is that **analysis and rendering are separate**. Kubrick can propose an automatic edit, save it as a project, let a UI modify it, and only then render the result.

## Core editing engine

### Timeline operations

The Python API now exposes non-destructive operations for:

```python
from kubrick.core import MediaClip, Project
from kubrick.editor import add_filter, cut_range, merge_clips, trim_clip

clip = MediaClip("camera.mp4", source_start=0, source_end=30)
trimmed = trim_clip(clip, 3, 24)
project = merge_clips(trimmed, MediaClip("broll.mp4", 0, 8))
project = add_filter(project, "eq=contrast=1.04:saturation=1.03")
project = cut_range(project, 12, 14)
```

Source files are never modified by these operations.

### Project model

A `.kubrick.json` project can contain:

- sequential main video clips
- external audio clips
- video filter chains
- timed text overlays
- timed image overlays
- timed shape overlays
- output dimensions/FPS metadata
- a named editing preset

Projects are plain JSON, making them easy to inspect, version, generate or integrate into other tooling.

### Presets

Built-in presets currently include:

| Preset | Purpose |
|---|---|
| **clean** | Natural automatic cleanup for spoken footage |
| **gentle** | Minimal intervention and longer pauses |
| **tight** | Faster pacing and stronger dead-air removal |
| **punchy** | Clean preset plus a restrained visual contrast/saturation lift |
| **mono-voice** | Speech-forward output with mild gain |

Presets are intentionally small and composable rather than opaque AI “styles”.

### Rendering

The compositor uses one FFmpeg filter graph for the final A/V output. It supports:

- arbitrary clip trims
- clip concatenation
- playback speed changes
- per-clip volume
- FFmpeg video filters
- external audio layers
- audio fades and timeline offsets
- text overlays
- image overlays
- color/shape overlays
- H.264 + AAC MP4 output
- fast-start MP4s

The existing automatic renderer continues to use the same synchronized keep-timeline principle, so automatic silence removal cannot independently desynchronize audio and video.

## Automatic intelligence

Kubrick's automatic editor is deterministic-first.

### Audio

- FFmpeg `silencedetect`
- configurable noise threshold
- EOF-open silence handling
- `gentle`, `natural`, and `tight` editorial profiles
- natural pause compression instead of blunt silence deletion
- overlap-safe timeline construction

### Speech — optional

With the speech extra installed, local `faster-whisper` inference can provide:

- word-level timestamps
- speech segments
- filler evidence
- false-start evidence
- repetition evidence
- extended-pause evidence
- confidence-aware editorial candidates

Speech findings are evidence, not automatic permission to delete.

### Visual — Phase 3 foundation

FFmpeg-backed visual analysis currently provides:

- scene-change detection
- blackout detection
- freeze detection
- visual continuity evidence
- confidence-scored review decisions
- technical take scoring based on measurable visual faults

A scene change, blackout or freeze is deliberately not converted into a blind destructive cut.

Semantic slide understanding and semantic multi-take selection remain future work.

## Desktop application

Kubrick is a **native desktop application**, not a browser video editor. The current PySide6 interface exposes the automatic analysis workflow and synchronized rendering.

```bash
python -m pip install -e ".[gui]"
kubrick-gui
```

FFmpeg and FFprobe must be available on your system `PATH`.

The desktop UI is the next major expansion area: synchronized video preview, waveform/transcript timeline, edit markers, non-destructive approve/reject controls, and direct access to the project compositor.

## CLI

### Analyze footage

```bash
python -m pip install -e .
kubrick analyze input.mp4 --profile natural --json analysis.json
```

### Automatically tighten and render

```bash
kubrick render input.mp4 output.mp4 --profile natural
```

### Create an editable automatic project

```bash
kubrick new-project input.mp4 edit.kubrick.json --preset clean
```

### Render an editable project

```bash
kubrick render-project edit.kubrick.json output.mp4
```

Optional local speech intelligence:

```bash
python -m pip install -e ".[speech]"
```

## Architecture

```text
Kubrick/
├── kubrick/
│   ├── core/       models, policy, project model, presets, timeline
│   ├── media/      FFmpeg probing, silence + visual analysis, compositor
│   ├── speech/     optional local transcription + editorial evidence
│   ├── editor/     analysis, automatic projects, operations, rendering
│   └── ui/         native PySide6 application + branding
├── index.py        lightweight Vercel homepage/API handler
├── index.html      public product/status page
├── tests/          behavioral + regression coverage
└── .github/        CI across supported Python versions
```

### Local-first boundary

The heavy media path stays local. Vercel is only a lightweight HTTP surface for the public product page and health endpoint; it is **not** the video-processing runtime.

## Quality bar

Kubrick is not successful because it found the most things to delete.

A release must satisfy:

1. **A/V never drifts because of an edit.**
2. **Every destructive automatic decision has evidence.**
3. **Natural speech rhythm survives automatic editing.**
4. **Low-confidence findings remain reviewable.**
5. **Visual anomalies do not become blind automatic cuts.**
6. **The same input/settings produce deterministic analysis.**
7. **Projects remain editable instead of becoming one opaque render command.**
8. **The core workflow remains useful without a cloud dependency.**

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m compileall -q kubrick
ruff check .
```

CI runs tests, compilation and linting across Python 3.11–3.13.

## Roadmap

### Phase 1 — Precision foundation — **complete**

- [x] media probing
- [x] silence analysis
- [x] editing profiles
- [x] natural pause compression
- [x] synchronized A/V rendering
- [x] metadata preservation
- [x] JSON reports
- [x] native desktop UI
- [x] application branding

### Phase 2 — Speech intelligence — **foundation complete**

- [x] local faster-whisper integration
- [x] word-level timing
- [x] conservative VAD
- [x] filler / false-start / repetition evidence
- [x] confidence-aware editorial candidates
- [ ] word-aware boundary refinement
- [ ] semantic retake selection

### Phase 3 — Visual intelligence — **foundation complete**

- [x] scene-change detection
- [x] blackout detection
- [x] freeze detection
- [x] visual continuity evidence
- [x] technical take scoring
- [ ] slide-content understanding
- [ ] semantic multi-take selection

### Phase 4 — Editor core — **in progress**

- [x] editable project model
- [x] cut / trim / merge operations
- [x] video filters
- [x] external audio layers
- [x] text / image / shape overlays
- [x] reusable presets
- [x] project JSON save/load
- [x] project compositor
- [ ] synchronized preview player
- [ ] waveform timeline
- [ ] transcript timeline
- [ ] visual edit markers
- [ ] approve / reject / modify controls
- [ ] undo / redo history

### Phase 5 — Release quality

- [ ] captions
- [ ] richer audio cleanup
- [ ] packaged Windows/macOS/Linux releases
- [ ] GPU acceleration where it materially improves throughput
- [ ] installer + first-run FFmpeg checks
- [ ] end-to-end fixture videos in CI

## Status

**Active development — v0.3.0**

Kubrick has moved beyond a silence-only prototype: it now has an editable project representation and a local FFmpeg compositor for practical multi-layer edits. The next priority is connecting that engine to a genuinely rich, non-destructive desktop timeline.

## License

License will be finalized before the first public release.
