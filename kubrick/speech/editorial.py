"""Deterministic speech-aware editorial evidence and decisions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .transcribe import SpeechSegment
from kubrick.core.models import TimeRange


@dataclass(frozen=True, slots=True)
class EditorialConfig:
    filler_words: tuple[str, ...] = ("um", "uh", "erm", "hmm", "like", "you know", "i mean")
    min_false_start_words: int = 2
    repetition_similarity: float = 0.88
    min_pause: float = 0.35
    keep_pause: float = 0.18


@dataclass(frozen=True, slots=True)
class EditorialFinding:
    range: TimeRange
    kind: str
    confidence: float
    reason: str
    replacement_duration: float | None = None


def _clean(text: str) -> str:
    return re.sub(r"[^a-z0-9' ]+", " ", text.lower()).strip()


def detect_fillers(segments: list[SpeechSegment], config: EditorialConfig = EditorialConfig()) -> list[EditorialFinding]:
    findings: list[EditorialFinding] = []
    fillers = {_clean(x) for x in config.filler_words}
    for segment in segments:
        for word in segment.words:
            token = _clean(word.text)
            if token in fillers:
                findings.append(EditorialFinding(TimeRange(word.start, word.end), "filler", 0.97, f"Filler word: {word.text.strip()}"))
    return findings


def detect_repetitions(segments: list[SpeechSegment], config: EditorialConfig = EditorialConfig()) -> list[EditorialFinding]:
    findings: list[EditorialFinding] = []
    for previous, current in zip(segments, segments[1:]):
        a, b = _clean(previous.text), _clean(current.text)
        if not a or not b:
            continue
        similarity = SequenceMatcher(None, a, b).ratio()
        if similarity >= config.repetition_similarity and current.start - previous.end <= 3.0:
            findings.append(EditorialFinding(TimeRange(previous.start, current.end), "repetition", similarity, "Adjacent speech is highly repetitive; review the weaker take."))
    return findings


def detect_false_starts(segments: list[SpeechSegment], config: EditorialConfig = EditorialConfig()) -> list[EditorialFinding]:
    findings: list[EditorialFinding] = []
    for segment in segments:
        words = list(segment.words)
        if len(words) < config.min_false_start_words + 1:
            continue
        for i in range(config.min_false_start_words, min(len(words), 8)):
            prefix = [_clean(w.text) for w in words[:i]]
            suffix = [_clean(w.text) for w in words[i:]]
            if prefix and suffix and prefix[-1] == suffix[0]:
                findings.append(EditorialFinding(TimeRange(words[0].start, words[i - 1].end), "false_start", 0.78, "Possible restarted phrase; review before cutting."))
                break
    return findings


def pause_findings(segments: list[SpeechSegment], config: EditorialConfig = EditorialConfig()) -> list[EditorialFinding]:
    findings: list[EditorialFinding] = []
    for previous, current in zip(segments, segments[1:]):
        pause = current.start - previous.end
        if pause >= config.min_pause:
            findings.append(EditorialFinding(TimeRange(previous.end, current.start), "pause", 0.90, "Extended inter-speech pause.", config.keep_pause))
    return findings


def build_editorial_findings(segments: list[SpeechSegment], config: EditorialConfig = EditorialConfig()) -> list[EditorialFinding]:
    findings: list[EditorialFinding] = []
    findings.extend(pause_findings(segments, config))
    findings.extend(detect_fillers(segments, config))
    findings.extend(detect_false_starts(segments, config))
    findings.extend(detect_repetitions(segments, config))
    return sorted(findings, key=lambda x: (x.range.start, x.range.end))
