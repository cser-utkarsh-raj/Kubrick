from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kubrick.media import detect_blackouts, detect_frozen_frames, probe_duration


@dataclass(frozen=True, slots=True)
class TakeScore:
    path: Path
    duration: float
    blackout_seconds: float
    frozen_seconds: float
    score: float
    reasons: tuple[str, ...]


def _ratio(seconds: float, duration: float) -> float:
    return seconds / duration if duration > 0 else 1.0


def score_take(path: str | Path) -> TakeScore:
    """Score a take on technical continuity quality, never on semantic content."""
    source = Path(path)
    duration = probe_duration(source)
    blackouts = detect_blackouts(source)
    freezes = detect_frozen_frames(source)
    blackout_seconds = sum(x.duration for x in blackouts)
    frozen_seconds = sum(x.duration for x in freezes)

    penalty = min(1.0, _ratio(blackout_seconds, duration) * 2.0 + _ratio(frozen_seconds, duration) * 1.5)
    score = max(0.0, 1.0 - penalty)
    reasons: list[str] = []
    if blackouts:
        reasons.append(f"{len(blackouts)} blackout interval(s)")
    if freezes:
        reasons.append(f"{len(freezes)} frozen interval(s)")
    if not reasons:
        reasons.append("no detected visual continuity faults")

    return TakeScore(source, duration, blackout_seconds, frozen_seconds, score, tuple(reasons))


def select_best_take(paths: list[str | Path]) -> TakeScore:
    """Choose the technically cleanest take, preserving ties by input order."""
    if not paths:
        raise ValueError("at least one take is required")
    scores = [score_take(path) for path in paths]
    return max(scores, key=lambda item: item.score)
