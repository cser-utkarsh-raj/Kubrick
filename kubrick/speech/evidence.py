"""Structured speech evidence used by Kubrick's editorial pipeline.

These models describe evidence only. They deliberately contain no editing
policy or automatic-cut decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kubrick.core.models import TimeRange


@dataclass(frozen=True, slots=True)
class WordContext:
    """The word immediately adjacent to a silence, when known."""

    text: str
    timestamp: float
    confidence: float | None = None
    segment_id: int | None = None


@dataclass(frozen=True, slots=True)
class SpeechContext:
    """Speech surrounding a silence region."""

    before: WordContext | None = None
    after: WordContext | None = None
    same_segment: bool = False
    filler_detected: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceQuality:
    """Reliability metadata for the evidence attached to a silence."""

    whisper_available: bool = False
    timestamps_reliable: bool = True
    confidence_score: float = 0.0
    fallback_mode: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0 and 1")
        if self.fallback_mode and self.whisper_available:
            raise ValueError("fallback_mode cannot be true when Whisper is available")


@dataclass(frozen=True, slots=True)
class SilenceEvidence:
    """Enriched evidence for one FFmpeg-detected silence interval."""

    silence: TimeRange
    context: SpeechContext = field(default_factory=SpeechContext)
    quality: EvidenceQuality = field(default_factory=EvidenceQuality)
