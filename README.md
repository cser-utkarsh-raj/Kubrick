# KUBRICK

> **Cut the noise. Reveal the story.**

**Kubrick** is a standalone `.dot` tool for precision-first automatic video editing. It is built for real spoken footage — lectures, tutorials, presentations, explainers, interviews, courses, and creator recordings — where bad pacing is obvious but robotic editing is worse.

[![CI](https://github.com/cser-utkarsh-raj/Kubrick/actions/workflows/ci.yml/badge.svg)](https://github.com/cser-utkarsh-raj/Kubrick/actions/workflows/ci.yml)

## What it is

Kubrick is a **desktop-first local video editor**, not a web wrapper and not a component of dotStudio.

It analyzes media, builds explainable editorial decisions, and renders a synchronized result with FFmpeg. Optional local speech intelligence adds word-level timing and conservative editorial evidence.

```text
                 KUBRICK
                    │
        ┌───────────┴───────────┐
        │                       │
   MEDIA EVIDENCE          SPEECH EVIDENCE
        │                       │
      FFmpeg              Whisper / VAD
        │                       │
        └───────────┬───────────┘
                    ↓
             EDITORIAL POLICY
                    │
          KEEP / COMPRESS / CUT / REVIEW
                    │
                    ↓
             SYNCHRONIZED RENDER
```

## The editing philosophy

Kubrick is **precision-first**.

> Edit aggressively where the footage is objectively weak; edit conservatively where human nuance matters.

The engine does not treat every silence, filler, or speech-model guess as permission to delete content. Ambiguous editorial findings remain reviewable.

## Current capabilities

### Media

- FFprobe duration validation
- FFmpeg silence detection
- configurable `gentle`, `natural`, and `tight` profiles
- natural pause compression
- full interval cuts
- safe merging of overlapping edit ranges
- synchronized video + audio rendering
- source metadata and chapter preservation
- JSON analysis reports
- EOF silence handling

### Speech

Optional local `faster-whisper` support provides:

- speech segments
- word-level timestamps
- conservative VAD
- filler-word evidence
- false-start evidence
- repetition evidence
- extended-pause evidence
- confidence-aware editorial decisions

Semantic findings are deliberately conservative: Kubrick can recommend a review without silently destroying a potentially meaningful sentence.

## Desktop UI

Kubrick includes a native **PySide6 desktop interface** with its own cinematic visual identity:

- dark editorial workspace
- Kubrick monolith-inspired mark
- source selection
- editing profile controls
- silence threshold controls
- analysis progress
- editorial decision table
- synchronized rendering workflow

The UI is packaged with the application and the branding SVG is included as package data.

### Run it locally

```bash
python -m pip install -e ".[gui]"
kubrick-gui
```

You also need **FFmpeg and FFprobe** available on your system `PATH`.

## CLI

```bash
# Core
python -m pip install -e .

# Analyze
kubrick analyze input.mp4 --profile natural --json analysis.json

# Render
kubrick render input.mp4 output.mp4 --profile natural
```

Optional speech support:

```bash
python -m pip install -e ".[speech]"
```

## Profiles

| Profile | Philosophy |
|---|---|
| **Gentle** | Remove only obvious dead air. |
| **Natural** | Tighten pacing while preserving human rhythm. **Default.** |
| **Tight** | More aggressive pacing for highly edited material. |

## Local-first by design

Kubrick's core workflow runs locally. Source footage does not need to be uploaded to a cloud service, and the core engine does not require a paid AI API or user account.

Speech intelligence is optional and can run locally when installed.

## Architecture

```text
Kubrick/
├── kubrick/
│   ├── core/       domain models, policies, decisions, timelines
│   ├── media/      FFmpeg probing, silence detection, rendering
│   ├── speech/     optional local transcription + editorial evidence
│   ├── editor/     analysis and rendering orchestration
│   └── ui/         PySide6 desktop application + branding
├── tests/          behavioral and regression tests
└── .github/        continuous integration
```

## `.dot` relationship

Kubrick is **one standalone tool in the `.dot` ecosystem**, alongside tools such as goPanda and NailedIt.

It is **not inside dotStudio**, does not depend on dotStudio, and is not planned as a dotStudio module.

```text
.dot
├── goPanda
├── NailedIt
├── Kubrick
├── MyMentor
├── TerraVault
└── dotStudio
```

Kubrick owns its own product identity, interface, release lifecycle, and distribution.

## Roadmap

### Phase 1 — Precision foundation

- [x] media duration probing
- [x] FFmpeg silence analysis
- [x] configurable editing profiles
- [x] pause compression
- [x] synchronized A/V rendering
- [x] JSON analysis
- [x] regression coverage
- [x] desktop UI
- [x] application branding

### Phase 2 — Speech intelligence

- [x] local faster-whisper integration
- [x] filler-word evidence
- [x] false-start evidence
- [x] repetition evidence
- [x] pause evidence
- [x] conservative editorial policy
- [ ] word-aware boundary refinement
- [ ] correction / retake selection

### Phase 3 — Visual editorial intelligence

- [ ] scene-change detection
- [ ] slide-change awareness
- [ ] visual continuity checks
- [ ] take selection
- [ ] confidence-scored review timeline

### Phase 4 — Product polish

- [ ] waveform + transcript timeline
- [ ] before/after preview
- [ ] non-destructive edit review
- [ ] captions
- [ ] richer audio cleanup
- [ ] packaged Windows/macOS/Linux releases

## Quality bar

Kubrick is not considered finished because a model can find more things to cut.

The quality bar is:

1. **No broken A/V synchronization.**
2. **No unexplained destructive edits.**
3. **Natural pacing survives automatic editing.**
4. **Ambiguous decisions are reviewable.**
5. **Real recordings improve perceptibly.**
6. **The application remains useful without a cloud dependency.**

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m compileall -q kubrick
ruff check .
```

CI runs the test suite, package compilation, and lint checks across Python 3.11–3.13.

## Status

**Active development — v0.2.1.**

The foundation is functional. The next major milestone is turning the existing evidence pipeline into a genuinely trustworthy automatic editor on real footage.

## License

License will be finalized before the first public release.
