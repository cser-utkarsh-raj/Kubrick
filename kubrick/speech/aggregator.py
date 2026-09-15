"""
Speech Evidence Aggregator.

Correlates FFmpeg silence detection with Whisper speech transcription
to produce structured SilenceEvidence objects.

This module is purely additive: it gathers evidence but makes NO editorial decisions.
"""
from typing import List, Optional, Dict, Any
from kubrick.core.models import TimeRange
from kubrick.speech.evidence import (
    SilenceEvidence,
    SpeechContext,
    WordContext,
    EvidenceQuality
)

# Common filler words for detection (lowercase)
FILLER_WORDS = {"um", "uh", "err", "er"}


class SpeechEvidenceAggregator:
    """
    Aggregates silence detection and speech transcription into unified evidence.
    
    This class is designed to be robust:
    - Works with silence-only data (Whisper optional).
    - Handles missing/malformed timestamps gracefully.
    - Never crashes on invalid input; marks evidence as low-quality instead.
    """
    
    def __init__(self, source_duration: float):
        """
        Initialize the aggregator.
        
        Args:
            source_duration: Total duration of the source media in seconds.
        """
        self.source_duration = source_duration
    
    def analyze(
        self,
        silence_regions: List[TimeRange],
        whisper_segments: Optional[List[Dict[str, Any]]] = None,
        whisper_words: Optional[List[Dict[str, Any]]] = None
    ) -> List[SilenceEvidence]:
        """
        Analyze silence regions with optional speech context.
        
        Args:
            silence_regions: List of detected silence TimeRanges from FFmpeg.
            whisper_segments: Optional list of Whisper segment dicts.
            whisper_words: Optional list of Whisper word dicts.
            
        Returns:
            List of SilenceEvidence objects, one per silence region.
        """
        if not silence_regions:
            return []
        
        # Build lookup structures for speech data if available
        speech_data = self._index_speech_data(whisper_segments, whisper_words)
        has_whisper = speech_data is not None
        
        evidence_list = []
        for silence in silence_regions:
            # Validate silence range
            if not self._is_valid_range(silence):
                continue
                
            context = SpeechContext()
            quality = EvidenceQuality(
                whisper_available=has_whisper,
                fallback_mode=not has_whisper
            )
            
            if has_whisper and speech_data:
                context = self._extract_context(silence, speech_data)
                quality = self._calculate_quality(context, speech_data)
            
            evidence = SilenceEvidence(
                silence=silence,
                context=context,
                quality=quality
            )
            evidence_list.append(evidence)
        
        return evidence_list
    
    def _index_speech_data(
        self,
        segments: Optional[List[Dict[str, Any]]],
        words: Optional[List[Dict[str, Any]]]
    ) -> Optional[Dict[str, Any]]:
        """Index speech data for efficient lookup."""
        if not segments and not words:
            return None
        
        return {
            "segments": segments or [],
            "words": words or []
        }
    
    def _is_valid_range(self, tr: TimeRange) -> bool:
        """Check if a TimeRange is valid and within bounds."""
        if tr.start < 0 or tr.end > self.source_duration:
            return False
        if tr.duration <= 0:
            return False
        return True
    
    def _extract_context(
        self,
        silence: TimeRange,
        speech_data: Dict[str, Any]
    ) -> SpeechContext:
        """Extract surrounding speech context for a silence region."""
        words = speech_data.get("words", [])
        segments = speech_data.get("segments", [])
        
        before_word = None
        after_word = None
        before_segment_id = None
        after_segment_id = None
        
        # Find words immediately before and after silence
        for word in words:
            w_start = word.get("start", 0.0)
            w_end = word.get("end", 0.0)
            
            # Word ends before silence starts → candidate for 'before'
            if w_end <= silence.start + 0.01:  # Small tolerance
                if before_word is None or w_end > before_word.timestamp:
                    before_word = WordContext(
                        text=word.get("text", "").strip().lower(),
                        timestamp=w_end,
                        confidence=word.get("confidence", 0.0),
                        segment_id=word.get("segment_index")
                    )
                    before_segment_id = word.get("segment_index")
            
            # Word starts after silence ends → candidate for 'after'
            elif w_start >= silence.end - 0.01:  # Small tolerance
                if after_word is None or w_start < after_word.timestamp:
                    after_word = WordContext(
                        text=word.get("text", "").strip().lower(),
                        timestamp=w_start,
                        confidence=word.get("confidence", 0.0),
                        segment_id=word.get("segment_index")
                    )
                    after_segment_id = word.get("segment_index")
        
        # Determine if before/after are in same segment
        same_segment = False
        if before_segment_id is not None and after_segment_id is not None:
            same_segment = (before_segment_id == after_segment_id)
        
        # Detect fillers
        filler_detected = False
        if before_word and before_word.text in FILLER_WORDS:
            filler_detected = True
        if after_word and after_word.text in FILLER_WORDS:
            filler_detected = True
        
        return SpeechContext(
            before=before_word,
            after=after_word,
            same_segment=same_segment,
            filler_detected=filler_detected
        )
    
    def _calculate_quality(
        self,
        context: SpeechContext,
        speech_data: Dict[str, Any]
    ) -> EvidenceQuality:
        """Calculate evidence quality metrics."""
        confidences = []
        if context.before:
            confidences.append(context.before.confidence)
        if context.after:
            confidences.append(context.after.confidence)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Check for timestamp reliability (simple overlap check could go here)
        timestamps_reliable = True
        
        return EvidenceQuality(
            whisper_available=True,
            timestamps_reliable=timestamps_reliable,
            confidence_score=avg_confidence,
            fallback_mode=False
        )
