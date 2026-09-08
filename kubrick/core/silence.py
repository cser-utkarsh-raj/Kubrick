"""Silence analysis utilities.

Kubrick keeps low-level detection deterministic. AI may later interpret the detected
intervals, but the media signal analysis remains reproducible and inspectable.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from .models import SilenceInterval


def detect_silence_from_samples(
    samples: Iterable[float],
    sample_rate: int,
    *,
    threshold_db: float = -38.0,
    min_duration: float = 0.6,
) -> list[SilenceInterval]:
    """Detect contiguous intervals whose peak level stays below ``threshold_db``.

    This first implementation operates on mono normalized samples in ``[-1, 1]``.
    It intentionally avoids making editing decisions: callers receive raw detected
    intervals and can apply policy such as pause compression separately.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be > 0")
    if min_duration < 0:
        raise ValueError("min_duration must be >= 0")
    if threshold_db >= 0:
        raise ValueError("threshold_db must be < 0")

    threshold = 10 ** (threshold_db / 20.0)
    in_silence = False
    start_index = 0
    intervals: list[SilenceInterval] = []

    for index, raw in enumerate(samples):
        sample = abs(float(raw))
        if not math.isfinite(sample):
            sample = 0.0

        below = sample <= threshold
        if below and not in_silence:
            in_silence = True
            start_index = index
        elif not below and in_silence:
            end_index = index
            duration = (end_index - start_index) / sample_rate
            if duration >= min_duration:
                intervals.append(
                    SilenceInterval(
                        start=start_index / sample_rate,
                        end=end_index / sample_rate,
                        peak_db=threshold_db,
                    )
                )
            in_silence = False

    if in_silence:
        end_index = sum(1 for _ in samples)  # only reached for non-reiterable callers
        duration = (end_index - start_index) / sample_rate
        if duration >= min_duration:
            intervals.append(
                SilenceInterval(
                    start=start_index / sample_rate,
                    end=end_index / sample_rate,
                    peak_db=threshold_db,
                )
            )

    return intervals


def compress_pause(
    interval: SilenceInterval,
    *,
    keep_duration: float,
) -> SilenceInterval:
    """Return a retained pause centered inside a detected silence interval."""
    if keep_duration < 0:
        raise ValueError("keep_duration must be >= 0")
    if keep_duration >= interval.duration:
        return interval

    center = (interval.start + interval.end) / 2
    half = keep_duration / 2
    return SilenceInterval(
        start=max(interval.start, center - half),
        end=min(interval.end, center + half),
        peak_db=interval.peak_db,
    )
