from __future__ import annotations

from dataclasses import dataclass
import re
from .transcribe import SpeechSegment, Word

_FILLERS = re.compile(r"^(uh+|um+|erm+|hmm+|like|you know|basically|actually)$", re.I)

@dataclass(frozen=True, slots=True)
class SpeechEdit:
    start: float
    end: float
    kind: str
    confidence: float
    reason: str


def filler_edits(segments: list[SpeechSegment]) -> list[SpeechEdit]:
    edits: list[SpeechEdit] = []
    for segment in segments:
        for word in segment.words:
            text = word.text.strip(" ,.!?\t\n")
            if _FILLERS.fullmatch(text):
                confidence = word.probability if word.probability is not None else 0.75
                edits.append(SpeechEdit(word.start, word.end, "filler", min(0.99, max(0.0, confidence)), f"Possible filler word: {text}"))
    return edits


def false_start_edits(segments: list[SpeechSegment]) -> list[SpeechEdit]:
    """Flag likely false starts without deleting them automatically."""
    edits: list[SpeechEdit] = []
    for a, b in zip(segments, segments[1:]):
        gap = b.start - a.end
        if gap < 1.2 and len(a.text.split()) <= 6 and a.text and b.text:
            a_words = [re.sub(r"\W", "", w.text.lower()) for w in a.words]
            b_words = [re.sub(r"\W", "", w.text.lower()) for w in b.words[:3]]
            if a_words and any(w and w in b_words for w in a_words):
                edits.append(SpeechEdit(a.start, a.end, "false_start", 0.72, "Short preceding utterance overlaps vocabulary with the following take"))
    return edits


def speech_edit_candidates(segments: list[SpeechSegment]) -> list[SpeechEdit]:
    return filler_edits(segments) + false_start_edits(segments)
