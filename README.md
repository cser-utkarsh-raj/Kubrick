# Kubrick

> **Precision-first local video editing.** Tighten real footage without making it sound edited.

Kubrick is a Python-first, local video editing engine for spoken footage: lectures, tutorials, presentations, explainers, interviews and creator recordings.

It is being built as the intelligent editing engine inside **dotStudio**, one of the core products in the `.dot` architecture.

## The promise

Kubrick does **not** try to replace a human editor with one giant AI prompt.

Its rule is simple:

> **Edit aggressively where the footage is objectively weak; edit conservatively where human nuance matters.**

Every proposed edit is represented as an inspectable decision. Deterministic media operations stay deterministic. AI is reserved for contextual judgment where it provides a real advantage.

## What Kubrick actually does

### Editing engine

- Detects dead air and long low-energy pauses locally.
- Compresses pauses instead of blindly deleting them.
- Preserves a configurable natural pause after speech.
- Keeps audio and video on one shared edit-decision timeline.
- Renders synchronized cuts through FFmpeg.
- Produces reproducible machine-readable decisions.
- Handles end-of-file silence correctly.
- Merges overlapping edit ranges safely.

### Speech-aware layer

Optional local `faster-whisper` integration provides word-level timing and speech segments. Its VAD can be tuned for conservative or tighter speech detection; Kubrick keeps this layer optional so the basic editor does not require a model download. citeturn0search1turn0search4

Planned speech-aware decisions include:

- filler-word suggestions
- false-start detection
- repeated-take detection
- self-correction detection
- intentional-pause preservation
- confidence-based review queues

### Editorial intelligence

The long-term goal is context-aware editing, not maximum compression:

- slide/scene awareness
- visual continuity checks
- semantic keep/cut recommendations
- explainable edit reasons
- multiple profiles for lectures, tutorials, documentaries and short-form
- optional Gemini-assisted editorial review

## Quality model

Kubrick separates three kinds of work:

| Layer | Responsibility | Default approach |
|---|---|---|
| Media | decode, trim, concat, encode | FFmpeg |
| Signal | silence / speech evidence | FFmpeg + optional local VAD |
| Judgment | context and ambiguity | rules first, AI when useful |

This prevents an AI model from being responsible for tasks that a deterministic media tool can perform more reliably.

## Current profiles

- **Gentle** — only obvious dead air.
- **Natural** — meaningful tightening while retaining human rhythm.
- **Tight** — faster pacing for short-form or highly edited material.

The `natural` profile is the intended default for your lecture/tutorial workflow.

## Local-first

Kubrick is designed to keep source media on your computer by default.

There is no required cloud upload, no required paid API and no required account for the core editing engine. FFmpeg performs the final media processing locally. Speech intelligence is optional and local when installed.

## Current CLI

```bash
# Install the core
python -m pip install -e .

# Analyze a video
kubrick analyze input.mp4 --profile natural --json analysis.json

# Render a tightened copy
kubrick render input.mp4 output.mp4 --profile natural
```

For speech-aware features:

```bash
python -m pip install -e ".[speech]"
```

For the desktop UI:

```bash
python -m pip install -e ".[gui]"
kubrick-gui
```

FFmpeg and FFprobe must be available on the system `PATH`.

## Architecture

```text
Kubrick
│
├── core/       domain models, policies, timelines, decisions
├── media/      FFmpeg probing and deterministic rendering
├── speech/     optional local transcription + word timing
├── editor/     analysis orchestration and rendering
├── ui/         optional PySide6 desktop interface
└── tests/      behavioral and regression coverage
```

## Development philosophy

1. **Measure before editing.**
2. **Prefer deterministic evidence over model guesses.**
3. **Never destroy source media.**
4. **Make every automatic edit explainable.**
5. **Use conservative defaults.**
6. **Keep ambiguous edits reviewable.**
7. **Validate on real recordings, not synthetic demos.**
8. **Optimize for perceived quality, not seconds removed.**

## Roadmap

### Phase 1 — precision foundation

- [x] media duration probing
- [x] FFmpeg silence analysis
- [x] configurable editing profiles
- [x] pause compression decisions
- [x] synchronized deterministic rendering
- [x] JSON analysis output
- [x] regression tests

### Phase 2 — speech intelligence

- [x] optional faster-whisper integration
- [ ] word-aware cut boundaries
- [ ] filler-word suggestions
- [ ] false-start detection
- [ ] repeated-sentence detection
- [ ] correction/retake detection

### Phase 3 — editorial intelligence

- [ ] scene and slide awareness
- [ ] confidence-scored review queue
- [ ] explainable AI recommendations
- [ ] visual continuity checks
- [ ] take selection

### Phase 4 — dotStudio integration

- [ ] project timeline
- [ ] waveform and transcript views
- [ ] non-destructive edit review
- [ ] preview rendering
- [ ] captions
- [ ] asset and B-roll workflows
- [ ] publishing pipeline

## Status

**Active development — v0.2 foundation.**

The core is intentionally being built before the polished editor UI. The first quality gate is simple: Kubrick must make a real recording noticeably better without producing robotic pacing, broken synchronization or unexplained destructive edits.

## Relationship to .dot

```text
.dot
├── dotRoute
├── dotBot
└── dotStudio
      └── Kubrick
```

Kubrick is not intended to become another standalone generic AI wrapper. It is the precision editing engine inside dotStudio.

## License

License will be finalized before the first public release.
