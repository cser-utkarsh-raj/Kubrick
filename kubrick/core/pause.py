from __future__ import annotations

from .models import TimeRange


def refine_pause_with_speech(
    pause: TimeRange,
    speech_start: float | None,
    speech_end: float | None,
    *,
    min_boundary_gap: float = 0.06,
) -> TimeRange:
    """Move a silence boundary away from speech when signal and VAD disagree."""
    start = pause.start
    end = pause.end
    if speech_end is not None and speech_end > start and speech_end < end:
        start = min(end, speech_end + min_boundary_gap)
    if speech_start is not None and speech_start < end and speech_start > start:
        end = max(start, speech_start - min_boundary_gap)
    return TimeRange(start, end)


def retain_natural_pause(pause: TimeRange, keep_duration: float) -> TimeRange:
    if keep_duration < 0:
        raise ValueError("keep_duration must be >= 0")
    keep = min(pause.duration, keep_duration)
    center = (pause.start + pause.end) / 2
    half = keep / 2
    return TimeRange(max(pause.start, center - half), min(pause.end, center + half))
