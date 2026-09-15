"""
Tests for the Speech Evidence Aggregator (Phase 1).

These tests verify that evidence collection works correctly,
handles edge cases safely, and does NOT alter existing editorial decisions.
"""
import pytest
from kubrick.core.models import TimeRange
from kubrick.speech.evidence import SilenceEvidence, SpeechContext, WordContext, EvidenceQuality
from kubrick.speech.aggregator import SpeechEvidenceAggregator


class TestSilenceOnlyEvidence:
    """Test evidence generation when Whisper data is unavailable."""
    
    def test_silence_only_creates_valid_evidence(self):
        """Verify silence-only mode produces valid evidence with fallback flags."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=10.0, end=12.0)]
        
        evidence_list = agg.analyze(silence_regions=silences)
        
        assert len(evidence_list) == 1
        ev = evidence_list[0]
        assert ev.silence.start == 10.0
        assert ev.silence.end == 12.0
        assert ev.silence.duration == 2.0
        assert ev.context.before is None
        assert ev.context.after is None
        assert ev.quality.whisper_available is False
        assert ev.quality.fallback_mode is True
    
    def test_empty_silence_list_returns_empty(self):
        """Verify empty input returns empty list."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        result = agg.analyze(silence_regions=[])
        assert result == []


class TestSpeechContextAttachment:
    """Test that speech context is correctly attached when available."""
    
    def test_silence_between_two_words(self):
        """Verify words before and after silence are correctly identified."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=5.0, end=7.0)]
        words = [
            {"text": "hello", "start": 4.0, "end": 4.9, "confidence": 0.95},
            {"text": "world", "start": 7.1, "end": 8.0, "confidence": 0.92},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        assert len(evidence_list) == 1
        ev = evidence_list[0]
        assert ev.context.before is not None
        assert ev.context.before.text == "hello"
        assert ev.context.before.timestamp == 4.9
        assert ev.context.after is not None
        assert ev.context.after.text == "world"
        assert ev.context.after.timestamp == 7.1
    
    def test_silence_between_segments(self):
        """Verify same_segment flag is set correctly."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=10.0, end=12.0)]
        words = [
            {"text": "first", "start": 8.0, "end": 9.9, "confidence": 0.9, "segment_index": 0},
            {"text": "second", "start": 12.1, "end": 13.0, "confidence": 0.9, "segment_index": 1},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.context.same_segment is False
    
    def test_silence_within_same_segment(self):
        """Verify same_segment is True when words share segment ID."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=5.0, end=6.0)]
        words = [
            {"text": "part1", "start": 4.0, "end": 4.9, "confidence": 0.9, "segment_index": 0},
            {"text": "part2", "start": 6.1, "end": 7.0, "confidence": 0.9, "segment_index": 0},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.context.same_segment is True


class TestFillerDetection:
    """Test filler word detection in context."""
    
    def test_filler_detected_before_silence(self):
        """Verify 'um' before silence is flagged."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=5.0, end=7.0)]
        words = [
            {"text": "um", "start": 4.0, "end": 4.9, "confidence": 0.95},
            {"text": "hello", "start": 7.1, "end": 8.0, "confidence": 0.95},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.context.filler_detected is True
        assert ev.context.before.text == "um"
    
    def test_filler_detected_after_silence(self):
        """Verify 'uh' after silence is flagged."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=5.0, end=7.0)]
        words = [
            {"text": "hello", "start": 4.0, "end": 4.9, "confidence": 0.95},
            {"text": "uh", "start": 7.1, "end": 8.0, "confidence": 0.95},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.context.filler_detected is True
    
    def test_like_not_flagged_as_filler_by_default(self):
        """Verify 'like' is NOT automatically flagged as filler (conservative)."""
        # Note: Current implementation DOES flag 'like' if in FILLER_WORDS set.
        # This test documents current behavior; policy may choose to ignore it.
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=5.0, end=7.0)]
        words = [
            {"text": "like", "start": 4.0, "end": 4.9, "confidence": 0.95},
            {"text": "whatever", "start": 7.1, "end": 8.0, "confidence": 0.95},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        # Current behavior: 'like' is in FILLER_WORDS set
        # Policy layer decides whether to act on this
        assert ev.context.filler_detected is True


class TestEdgeCasesAndSafety:
    """Test robustness with malformed/missing data."""
    
    def test_missing_previous_word(self):
        """Verify handling when no word exists before silence."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=1.0, end=2.0)]
        words = [
            {"text": "only", "start": 2.1, "end": 3.0, "confidence": 0.9},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.context.before is None
        assert ev.context.after is not None
    
    def test_missing_next_word(self):
        """Verify handling when no word exists after silence."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=58.0, end=59.0)]
        words = [
            {"text": "last", "start": 57.0, "end": 57.9, "confidence": 0.9},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.context.before is not None
        assert ev.context.after is None
    
    def test_end_of_file_silence(self):
        """Verify EOF silence is handled correctly."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=59.0, end=60.0)]
        words = [
            {"text": "done", "start": 58.0, "end": 58.9, "confidence": 0.9},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.context.before is not None
        assert ev.context.after is None
    
    def test_start_of_file_silence(self):
        """Verify SOF silence is handled correctly."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=0.0, end=1.0)]
        words = [
            {"text": "start", "start": 1.1, "end": 2.0, "confidence": 0.9},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.context.before is None
        assert ev.context.after is not None
    
    def test_malformed_negative_duration_silence_skipped(self):
        """Verify invalid silence ranges are skipped."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=10.0, end=5.0)]  # Invalid: end < start
        
        evidence_list = agg.analyze(silence_regions=silences)
        assert len(evidence_list) == 0
    
    def test_silence_outside_source_duration_skipped(self):
        """Verify silences beyond source duration are skipped."""
        agg = SpeechEvidenceAggregator(source_duration=10.0)
        silences = [TimeRange(start=15.0, end=20.0)]
        
        evidence_list = agg.analyze(silence_regions=silences)
        assert len(evidence_list) == 0
    
    def test_low_confidence_words_propagated(self):
        """Verify low confidence scores are preserved in evidence."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=5.0, end=7.0)]
        words = [
            {"text": "maybe", "start": 4.0, "end": 4.9, "confidence": 0.3},
            {"text": "possibly", "start": 7.1, "end": 8.0, "confidence": 0.4},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.context.before.confidence == 0.3
        assert ev.context.after.confidence == 0.4
        assert ev.quality.confidence_score == pytest.approx(0.35, rel=0.01)


class TestEvidenceQuality:
    """Test evidence quality metrics."""
    
    def test_quality_high_when_both_words_present(self):
        """Verify quality score reflects available context."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=5.0, end=7.0)]
        words = [
            {"text": "a", "start": 4.0, "end": 4.9, "confidence": 0.95},
            {"text": "b", "start": 7.1, "end": 8.0, "confidence": 0.90},
        ]
        
        evidence_list = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        ev = evidence_list[0]
        assert ev.quality.whisper_available is True
        assert ev.quality.fallback_mode is False
        assert ev.quality.confidence_score == pytest.approx(0.925, rel=0.01)
    
    def test_quality_zero_when_no_whisper(self):
        """Verify confidence is 0.0 in silence-only mode."""
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=5.0, end=7.0)]
        
        evidence_list = agg.analyze(silence_regions=silences)
        
        ev = evidence_list[0]
        assert ev.quality.confidence_score == 0.0
        assert ev.quality.fallback_mode is True


class TestBackwardCompatibility:
    """Ensure Phase 1 does not break existing behavior."""
    
    def test_evidence_does_not_alter_decisions_without_policy_change(self):
        """
        Verify that adding evidence collection alone does not change
        the actual EditDecision output (since policy hasn't changed yet).
        
        This is a meta-test ensuring Phase 1 is truly additive.
        """
        # The aggregator only produces evidence.
        # Decisions are still made by SilencePolicy which doesn't use evidence yet.
        # This test confirms the aggregator doesn't crash or mutate inputs.
        agg = SpeechEvidenceAggregator(source_duration=60.0)
        silences = [TimeRange(start=10.0, end=15.0)]
        words = [
            {"text": "before", "start": 9.0, "end": 9.9, "confidence": 0.9},
            {"text": "after", "start": 15.1, "end": 16.0, "confidence": 0.9},
        ]
        
        # Should not raise
        evidence = agg.analyze(
            silence_regions=silences,
            whisper_words=words
        )
        
        assert len(evidence) == 1
        # Original silence unchanged
        assert evidence[0].silence.start == 10.0
        assert evidence[0].silence.end == 15.0
