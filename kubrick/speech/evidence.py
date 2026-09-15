"""
Speech Evidence Models for Kubrick.

This module defines the data structures for correlating silence detection
with speech transcription evidence. It does NOT make editorial decisions.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from kubrick.core.models import TimeRange


@dataclass(frozen=True)
class WordContext:
    """Contextual information about a single word adjacent to a silence."""
    text: str
    timestamp: float  # End time if before silence, Start time if after
    confidence: float
    segment_id: Optional[int] = None


@dataclass(frozen=True)
class SpeechContext:
    """
    Surrounding speech context for a silence region.
    
    Attributes:
        before: The last word spoken before the silence.
        after: The first word spoken after the silence.
        same_segment: True if 'before' and 'after' belong to the same Whisper segment.
        filler_detected: True if 'before' or 'after' text matches common fillers (um, uh).
    """
    before: Optional[WordContext] = None
    after: Optional[WordContext] = None
    same_segment: bool = False
    filler_detected: bool = False


@dataclass(frozen=True)
class EvidenceQuality:
    """
    Metrics describing the reliability of the available evidence.
    
    Attributes:
        whisper_available: Whether transcription data was provided.
        timestamps_reliable: Whether word timestamps seem valid (no overlaps/negatives).
        confidence_score: Aggregate confidence of surrounding words (0.0-1.0).
        fallback_mode: True if operating in silence-only mode due to missing data.
    """
    whisper_available: bool = False
    timestamps_reliable: bool = True
    confidence_score: float = 0.0
    fallback_mode: bool = False


@dataclass(frozen=True)
class SilenceEvidence:
    """
    Enriched evidence for a candidate silence region.
    
    This object combines the raw silence detection with optional speech context.
    It is the input to the Editorial Policy.
    
    Attributes:
        silence: The original detected silence time range.
        context: Surrounding speech information (words, segments).
        quality: Reliability metrics of the evidence.
    """
    silence: TimeRange
    context: SpeechContext = field(default_factory=SpeechContext)
    quality: EvidenceQuality = field(default_factory=EvidenceQuality)
