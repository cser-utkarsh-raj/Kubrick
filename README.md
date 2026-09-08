# Kubrick

> Precision-first video editing automation for clean, natural, reviewable cuts.

Kubrick is a Python-first local video editing engine designed to turn raw spoken-footage recordings into tighter, cleaner edits without flattening natural human delivery.

## Current direction

Kubrick is not a generic AI video generator and not a one-click "remove every silence" tool. Its core principle is:

**Edit aggressively where the footage is objectively weak; edit conservatively where human nuance matters.**

The system is designed around explicit, inspectable edit decisions rather than destructive black-box processing.

## Planned capabilities

### Core editing engine
- Silence and dead-air analysis
- Configurable pause compression
- Audio/video synchronization through a shared edit decision list
- Exact cut-boundary calculation
- Crossfade and room-tone aware transitions
- Deterministic FFmpeg rendering

### Speech-aware editing
- Local transcription integration
- Filler-word detection
- False-start detection
- Repeated-take / repeated-sentence detection
- Correction and retake detection
- Natural-pause preservation
- Confidence-based recommendations

### Editorial intelligence
- Scene and slide-change awareness
- Context-aware keep/cut decisions
- Human-review queue for ambiguous edits
- Explainable recommendations
- Multiple editing profiles for lectures, tutorials, documentaries and short-form content

### Deliverables
- Preview renders
- Final MP4 output
- Subtitle files
- Machine-readable edit decision lists
- Reproducible project metadata

## Design principles

1. **Local-first** — source media stays on the user's machine by default.
2. **Deterministic media processing** — use proven media tooling for operations that do not require AI.
3. **AI only where it adds judgment** — semantic understanding, not needless API calls.
4. **Non-destructive decisions** — every cut is inspectable and reversible.
5. **Natural speech first** — the goal is invisible editing, not maximum compression.
6. **Provider-agnostic** — AI, transcription and TTS components remain replaceable.
7. **Quality gates** — high-confidence edits can be automated; ambiguous edits require review.
8. **Test against real footage** — editing quality is validated on actual recordings, not synthetic demos.

## Initial stack

- Python
- FFmpeg
- PySide6 (desktop UI target)
- SQLite (project metadata)
- Local speech-to-text integration
- Optional Gemini integration for semantic editorial analysis

## Status

**Early development.** The repository starts intentionally small. The first milestone is a reliable silence/dead-air analysis and synchronized cut pipeline before adding higher-level AI editing.

## Relationship to .dot

Kubrick is the intelligent editing engine planned for **dotStudio**, the media/creation product within the .dot core architecture.

## License

License will be finalized once the core architecture stabilizes.
