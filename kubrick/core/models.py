from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DecisionKind(StrEnum):
    KEEP = "keep"
    COMPRESS = "compress"
    CUT = "cut"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class TimeRange:
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < 0 or self.end < self.start:
            raise ValueError("TimeRange requires 0 <= start <= end")

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class EditDecision:
    source: TimeRange
    kind: DecisionKind
    confidence: float
    reason: str
    target_duration: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.kind is DecisionKind.COMPRESS:
            if self.target_duration is None or self.target_duration < 0:
                raise ValueError("compress decisions require target_duration >= 0")
            if self.target_duration > self.source.duration:
                raise ValueError("target_duration cannot exceed source duration")


@dataclass(frozen=True, slots=True)
class KeepSegment:
    source: TimeRange


@dataclass(slots=True)
class AnalysisReport:
    duration: float
    silences: list[TimeRange]
    decisions: list[EditDecision]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def removed_duration(self) -> float:
        return sum(
            d.source.duration - (d.target_duration or 0)
            for d in self.decisions
            if d.kind is not DecisionKind.KEEP
        )

    @property
    def output_duration(self) -> float:
        return max(0.0, self.duration - self.removed_duration)
