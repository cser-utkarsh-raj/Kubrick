# KUBRICK

> **Cut the noise. Reveal the story.**

**Kubrick** is a precision-first automatic video editor for real spoken footage. It is built to turn long, imperfect recordings into tighter, more watchable edits without making people sound like robots.

Lectures. Tutorials. Presentations. Interviews. Courses. Explainers. Creator recordings.

[![CI](https://github.com/cser-utkarsh-raj/Kubrick/actions/workflows/ci.yml/badge.svg)](https://github.com/cser-utkarsh-raj/Kubrick/actions/workflows/ci.yml)

---

## Why Kubrick exists

Most automatic editors have one of two problems: they barely edit anything, or they cut so aggressively that the speaker loses their natural rhythm.

Kubrick takes a different approach:

> **Be aggressive with objective friction. Be conservative with human meaning.**

The engine builds evidence first, turns that evidence into explainable editorial decisions, and keeps destructive actions inspectable before rendering.

```text
SOURCE FOOTAGE
      │
      ├── Audio evidence ── silence / pauses / speech
      ├── Speech evidence ── fillers / false starts / repetition
      └── Visual evidence ── scenes / blackouts / freezes
                    │
                    ▼
             EDITORIAL POLICY
                    │
          KEEP / COMPRESS / CUT / REVIEW
                    │
                    ▼
             ONE SHARED TIMELINE
                    │
                    ▼
             SYNCHRONIZED OUTPUT
```

## What works today

### Precision editing

- FFprobe media validation and duration probing
- FFmpeg-powered silence detection
- configurable `gentle`, `natural`, and `tight` editing profiles
- natural pause compression rather than blunt silence deletion
- full-interval cuts where evidence supports them
- overlap-safe timeline construction
- synchronized video + audio rendering
- source metadata and chapter preservation
- machine-readable JSON analysis reports
- end-of-file silence handling

### Local speech intelligence

When the speech extra is installed, Kubrick can use local `faster-whisper` inference with conservative VAD to produce:

- word-level timestamps
- speech segments
- filler-word evidence
- false-start evidence
- repetition evidence
- extended-pause evidence
- confidence-aware editorial candidates

Speech findings are evidence, not automatic permission to delete. Ambiguous material stays reviewable.

### Visual editorial intelligence — Phase 3

Kubrick now has a deterministic visual evidence layer powered by FFmpeg:

- **Scene-change detection** for hard visual transitions
- **Slide-change boundary awareness** through scene-change evidence, without pretending a hard cut is automatically a slide
- **Blackout detection** for accidental black frames and continuity breaks
- **Freeze detection** for stalled or frozen footage
- **Confidence-scored visual review decisions** surfaced beside normal editorial decisions
- **Technical take scoring** that can select the cleanest candidate based on detected visual faults
- visual evidence stored alongside the editorial analysis report
- configurable scene sensitivity

The important safety boundary is intentional: visual evidence can trigger review, but a scene change, blackout, or freeze is not blindly turned into a destructive cut.

## Desktop application

Kubrick is a **native desktop application**, not a browser video editor. The main interface is built with PySide6 and is designed around a focused editorial workflow:

1. Choose a source recording.
2. Select an editing profile.
3. Analyze the footage.
4. Inspect the detected editorial decisions.
5. Render a tightened copy.

The interface is intentionally dark, cinematic, and information-dense without turning the editor into a dashboard full of noise.

### Launch

```bash
python -m pip install -e ".[gui]"
kubrick-gui
```

FFmpeg and FFprobe must be available on your system `PATH`.

## CLI

```bash
# Install the core engine
python -m pip install -e .

# Analyze a recording
kubrick analyze input.mp4 --profile natural --json analysis.json

# Render the editorial plan
kubrick render input.mp4 output.mp4 --profile natural
```

Optional local speech analysis:

```bash
python -m pip install -e ".[speech]"
```

## Editing profiles

| Profile | Behaviour | Best for |
|---|---|---|
| **Gentle** | Removes only the clearest dead air | interviews, thoughtful talks |
| **Natural** | Tightens pacing while retaining human rhythm | tutorials, lectures, explainers |
| **Tight** | More aggressive compression and cleanup | highly edited creator footage |

**Natural is the default** because Kubrick optimizes for watchability, not maximum removal.

## Architecture

```text
Kubrick/
├── kubrick/
│   ├── core/       models, policy, decisions, timeline
│   ├── media/      FFmpeg probing, silence + visual analysis, rendering
│   ├── speech/     optional local transcription + editorial evidence
│   ├── editor/     analysis, rendering + take scoring
│   └── ui/         native PySide6 application + branding
├── api/            lightweight Vercel health/API entrypoint
├── tests/          behavioral + regression coverage
└── .github/        CI across supported Python versions
```

### Local-first architecture

The video-processing engine is local-first. Footage does not need to be uploaded to a remote AI service for the core workflow, and the core engine does not require a paid AI API.

The `/api` surface is intentionally lightweight. **Vercel is not the video-processing runtime**; it exists only to provide a small HTTP surface around the application. Heavy media work remains on the desktop/local engine.

## Vercel API

The repository includes an explicit Python entrypoint at `api/index.py` and declares it in `pyproject.toml` so Vercel does not have to guess which Python function to build.

The endpoint is a health/status surface. It is not intended to receive or render large video files.

## Roadmap

### Phase 1 — Precision foundation — **complete**

- [x] media probing
- [x] silence analysis
- [x] editing profiles
- [x] natural pause compression
- [x] synchronized A/V rendering
- [x] metadata preservation
- [x] JSON reports
- [x] regression coverage
- [x] native desktop UI
- [x] application branding

### Phase 2 — Speech intelligence — **foundation complete**

- [x] local faster-whisper integration
- [x] word-level timing
- [x] conservative VAD
- [x] filler evidence
- [x] false-start evidence
- [x] repetition evidence
- [x] pause evidence
- [x] confidence-aware editorial candidates
- [ ] word-aware boundary refinement
- [ ] correction / semantic retake selection

### Phase 3 — Visual editorial intelligence — **foundation complete**

- [x] deterministic scene-change detection
- [x] slide-change boundary awareness
- [x] blackout detection
- [x] freeze detection
- [x] visual continuity evidence
- [x] confidence-scored review decisions
- [x] technical take scoring / selection
- [x] visual evidence in analysis reports
- [ ] slide-content understanding
- [ ] semantic multi-take selection

### After Phase 3

- [ ] waveform + transcript timeline
- [ ] before/after preview
- [ ] non-destructive edit review
- [ ] captions
- [ ] richer audio cleanup
- [ ] packaged Windows/macOS/Linux releases
- [ ] GPU-accelerated analysis where it materially improves throughput

## Quality bar

Kubrick is not successful because it found the most things to delete.

A release must satisfy these principles:

1. **A/V never drifts because of an edit.**
2. **Every destructive decision has evidence.**
3. **Natural speech rhythm survives automatic editing.**
4. **Low-confidence findings remain reviewable.**
5. **Visual anomalies do not become blind automatic cuts.**
6. **Repeated analysis is deterministic for the same input and settings.**
7. **The output is measurably tighter without becoming unpleasant to watch.**
8. **The core workflow remains useful without a cloud dependency.**

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m compileall -q kubrick
ruff check .
```

CI runs tests, compilation, and linting across Python 3.11–3.13.

## Status

**Active development — v0.3.0**

Kubrick now has a coherent local editing foundation across audio, speech, and visual evidence. The next major milestone is a rich, non-destructive editorial timeline that lets users see exactly why every suggested change exists before rendering.

## License

License will be finalized before the first public release.
