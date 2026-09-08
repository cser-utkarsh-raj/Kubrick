from __future__ import annotations

from .models import DecisionKind, EditDecision, KeepSegment, TimeRange


def _removed_ranges(duration: float, decisions: list[EditDecision]) -> list[TimeRange]:
    """Return only the media portions that should disappear.

    For a compressed pause, the beginning of the pause is retained so the edit
    sounds natural; only the excess tail is removed.
    """
    ranges: list[TimeRange] = []
    for decision in decisions:
        if decision.kind not in {DecisionKind.CUT, DecisionKind.COMPRESS}:
            continue
        source = decision.source
        start = max(0.0, min(duration, source.start))
        end = max(start, min(duration, source.end))
        target = 0.0 if decision.kind is DecisionKind.CUT else (decision.target_duration or 0.0)
        target = min(target, end - start)
        remove_start = start + target
        if remove_start < end - 0.001:
            ranges.append(TimeRange(remove_start, end))
    return ranges


def build_keep_segments(duration: float, decisions: list[EditDecision]) -> list[KeepSegment]:
    if duration < 0:
        raise ValueError("duration must be >= 0")
    cuts = sorted(_removed_ranges(duration, decisions), key=lambda r: r.start)
    merged: list[TimeRange] = []
    for item in cuts:
        if not merged or item.start > merged[-1].end + 1e-6:
            merged.append(item)
        else:
            merged[-1] = TimeRange(merged[-1].start, max(merged[-1].end, item.end))

    keep: list[KeepSegment] = []
    cursor = 0.0
    for cut in merged:
        if cut.start > cursor + 0.001:
            keep.append(KeepSegment(TimeRange(cursor, cut.start)))
        cursor = max(cursor, cut.end)
    if cursor < duration - 0.001:
        keep.append(KeepSegment(TimeRange(cursor, duration)))
    return keep
