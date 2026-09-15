from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SpeechDependencyError(RuntimeError):
    """Raised when an optional speech dependency is not installed."""


@dataclass(frozen=True, slots=True)
class Word:
    text: str
    start: float
    end: float
    probability: float | None = None


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    text: str
    start: float
    end: float
    words: tuple[Word, ...] = ()


def transcribe(path: str | Path, *, model_size: str = "small", language: str | None = None) -> list[SpeechSegment]:
    """Transcribe locally with word timing and conservative VAD.

    faster-whisper exposes word-level timestamps and Silero VAD; Kubrick uses
    these as evidence for future semantic editing rather than blindly deleting
    every VAD gap.

    The dependency is intentionally optional. Callers can catch
    ``SpeechDependencyError`` and continue with deterministic media evidence.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SpeechDependencyError(
            "Speech features require faster-whisper. Install with: "
            "python -m pip install -e '.[speech]'"
        ) from exc

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        str(path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,
    )
    result: list[SpeechSegment] = []
    for segment in segments:
        words = tuple(
            Word(w.word, float(w.start), float(w.end), getattr(w, "probability", None))
            for w in (segment.words or [])
        )
        result.append(SpeechSegment(segment.text.strip(), float(segment.start), float(segment.end), words))
    return result
