"""Domain models used by Kubrick's analysis and editing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Decision(StrEnum):
    KEEP = "keep"
    CUT = "cut"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Half-open media interval in seconds."""

    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if self.end < self.start:
            raise ValueError("end must be >= start")

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class SilenceInterval(TimeRange):
    """Detected low-energy audio interval."""

    peak_db: float | None = None


@dataclass(frozen=True, slots=True)
class EditDecision:
    """A reversible recommendation to keep, cut, or review an interval."""

    source: TimeRange
    decision: Decision
    replacement_duration: float | None = None
    confidence: float = 1.0
    reason: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.replacement_duration is not None and self.replacement_duration < 0:
            raise ValueError("replacement_duration must be >= 0")
