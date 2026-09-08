"""Convert editorial decisions into a safe, ordered source timeline."""

from __future__ import annotations

from dataclasses import dataclass

from .models import DecisionKind, EditDecision, KeepSegment, TimeRange

_EPS = 1e-6


@dataclass(frozen=True, slots=True)
class TimelinePlan:
    duration: float
    keep: tuple[KeepSegment, ...]

    @property
    def output_duration(self) -> float:
        return sum(segment.source.duration for segment in self.keep)


def build_timeline(duration: float, decisions: list[EditDecision]) -> TimelinePlan:
    """Build a non-overlapping keep timeline from editorial decisions.

    CUT removes an interval. COMPRESS retains only the requested duration from
    the beginning of the interval. REVIEW and KEEP never modify media.
    Decisions outside the media bounds are clipped safely.
    """
    if duration < 0:
        raise ValueError("duration must be >= 0")

    removed: list[TimeRange] = []
    for decision in decisions:
        if decision.kind not in (DecisionKind.CUT, DecisionKind.COMPRESS):
            continue
        start = max(0.0, min(duration, decision.source.start))
        end = max(start, min(duration, decision.source.end))
        if end - start <= _EPS:
            continue
        if decision.kind is DecisionKind.CUT:
            kept_pause = 0.0
        else:
            kept_pause = min(decision.target_duration or 0.0, end - start)
        cut_start = start + kept_pause
        if cut_start < end - _EPS:
            removed.append(TimeRange(cut_start, end))

    removed.sort(key=lambda x: (x.start, x.end))
    merged: list[TimeRange] = []
    for item in removed:
        if not merged or item.start > merged[-1].end + _EPS:
            merged.append(item)
        else:
            merged[-1] = TimeRange(merged[-1].start, max(merged[-1].end, item.end))

    keep: list[KeepSegment] = []
    cursor = 0.0
    for cut in merged:
        if cut.start > cursor + _EPS:
            keep.append(KeepSegment(TimeRange(cursor, cut.start)))
        cursor = max(cursor, cut.end)
    if cursor < duration - _EPS:
        keep.append(KeepSegment(TimeRange(cursor, duration)))

    return TimelinePlan(duration, tuple(keep))
