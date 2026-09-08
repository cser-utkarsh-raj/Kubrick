from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EditingProfile:
    name: str
    min_silence: float
    keep_pause: float
    cut_threshold: float
    review_threshold: float

    def __post_init__(self) -> None:
        if self.min_silence <= 0:
            raise ValueError("min_silence must be > 0")
        if self.keep_pause < 0:
            raise ValueError("keep_pause must be >= 0")
        if not 0 <= self.cut_threshold <= 1 or not 0 <= self.review_threshold <= 1:
            raise ValueError("thresholds must be between 0 and 1")


PROFILES = {
    "gentle": EditingProfile("gentle", 1.20, 0.45, 0.98, 0.88),
    "natural": EditingProfile("natural", 0.65, 0.28, 0.995, 0.90),
    "tight": EditingProfile("tight", 0.45, 0.18, 0.997, 0.93),
}
