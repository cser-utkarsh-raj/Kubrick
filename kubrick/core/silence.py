from __future__ import annotations

import math
from collections.abc import Iterable

from .models import TimeRange


def detect_silence_from_samples(
    samples: Iterable[float],
    sample_rate: int,
    *,
    threshold_db: float = -38.0,
    min_duration: float = 0.6,
) -> list[TimeRange]:
    """Detect contiguous low-energy intervals from normalized mono samples.

    The iterable is consumed exactly once, including EOF handling. This function
    deliberately reports evidence only; editing policy belongs elsewhere.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be > 0")
    if min_duration < 0:
        raise ValueError("min_duration must be >= 0")
    if threshold_db >= 0:
        raise ValueError("threshold_db must be < 0")

    threshold = 10 ** (threshold_db / 20.0)
    intervals: list[TimeRange] = []
    start_index: int | None = None
    last_index = -1

    for index, raw in enumerate(samples):
        last_index = index
        sample = abs(float(raw))
        if not math.isfinite(sample):
            sample = 0.0
        below = sample <= threshold
        if below and start_index is None:
            start_index = index
        elif not below and start_index is not None:
            end_index = index
            if (end_index - start_index) / sample_rate >= min_duration:
                intervals.append(TimeRange(start_index / sample_rate, end_index / sample_rate))
            start_index = None

    if start_index is not None:
        end_index = last_index + 1
        if (end_index - start_index) / sample_rate >= min_duration:
            intervals.append(TimeRange(start_index / sample_rate, end_index / sample_rate))

    return intervals


def compress_pause(interval: TimeRange, *, keep_duration: float) -> TimeRange:
    """Return a retained pause centered inside a detected silence interval."""
    if keep_duration < 0:
        raise ValueError("keep_duration must be >= 0")
    if keep_duration >= interval.duration:
        return interval
    center = (interval.start + interval.end) / 2
    half = keep_duration / 2
    return TimeRange(max(interval.start, center - half), min(interval.end, center + half))
