from __future__ import annotations

import pytest

from kubrick.core import PROFILES, SilencePolicy
from kubrick.core.models import EditDecision, TimeRange
from kubrick.editor import analyzer
from kubrick.speech import SpeechEvidenceAggregator, SpeechSegment, Word


def _segments() -> list[SpeechSegment]:
    return [
        SpeechSegment(
            text="hello",
            start=0.5,
            end=1.4,
            words=(Word("hello", 0.5, 1.4, 0.95),),
        ),
        SpeechSegment(
            text="world",
            start=3.1,
            end=4.0,
            words=(Word("world", 3.1, 4.0, 0.90),),
        ),
    ]


def test_silence_only_mode_is_safe_and_explicit() -> None:
    silence = TimeRange(1.5, 3.0)
    evidence = SpeechEvidenceAggregator(10.0).analyze([silence])

    assert len(evidence) == 1
    assert evidence[0].silence == silence
    assert evidence[0].context.before is None
    assert evidence[0].context.after is None
    assert evidence[0].quality.whisper_available is False
    assert evidence[0].quality.fallback_mode is True


def test_whisper_context_is_attached_to_silence() -> None:
    evidence = SpeechEvidenceAggregator(10.0).analyze(
        [TimeRange(1.5, 3.0)],
        _segments(),
    )

    item = evidence[0]
    assert item.context.before is not None
    assert item.context.before.text == "hello"
    assert item.context.before.timestamp == pytest.approx(1.4)
    assert item.context.after is not None
    assert item.context.after.text == "world"
    assert item.context.after.timestamp == pytest.approx(3.1)
    assert item.context.same_segment is False
    assert item.quality.whisper_available is True
    assert item.quality.fallback_mode is False
    assert item.quality.confidence_score == pytest.approx(0.925)
    assert item.quality.timestamps_reliable is True


def test_context_preserves_segment_identity_and_detects_fillers() -> None:
    segments = [
        SpeechSegment(
            text="um",
            start=1.0,
            end=1.4,
            words=(Word("um", 1.0, 1.4, 0.96),),
        ),
        SpeechSegment(
            text="continue",
            start=3.0,
            end=3.8,
            words=(Word("continue", 3.0, 3.8, 0.91),),
        ),
    ]
    item = SpeechEvidenceAggregator(10.0).analyze([TimeRange(1.5, 2.5)], segments)[0]

    assert item.context.before is not None
    assert item.context.before.segment_id == 0
    assert item.context.after is not None
    assert item.context.after.segment_id == 1
    assert item.context.filler_detected is True


def test_invalid_or_out_of_bounds_silence_is_skipped() -> None:
    aggregator = SpeechEvidenceAggregator(10.0)
    assert aggregator.analyze([TimeRange(0.0, 0.0)]) == []
    assert aggregator.analyze([TimeRange(9.0, 10.0), TimeRange(10.0, 10.0)]) == [
        # A valid one-second EOF silence remains valid.
        aggregator.analyze([TimeRange(9.0, 10.0)])[0]
    ]


def test_invalid_source_duration_is_rejected() -> None:
    with pytest.raises(ValueError, match="source_duration"):
        SpeechEvidenceAggregator(-1.0)


def test_unreliable_word_timestamps_are_reported() -> None:
    segments = [
        SpeechSegment(
            text="a b",
            start=1.0,
            end=3.0,
            words=(
                Word("a", 1.0, 2.0, 0.9),
                Word("b", 1.5, 3.0, 0.8),
            ),
        )
    ]
    item = SpeechEvidenceAggregator(10.0).analyze([TimeRange(3.5, 4.0)], segments)[0]
    assert item.quality.timestamps_reliable is False


def test_analyzer_integrates_aggregator_without_changing_silence_decisions(monkeypatch) -> None:
    silences = [TimeRange(2.0, 4.0), TimeRange(7.0, 8.0)]
    expected = SilencePolicy(PROFILES["natural"]).decide(silences)

    monkeypatch.setattr(analyzer, "probe_duration", lambda path: 10.0)
    monkeypatch.setattr(analyzer, "detect_silence", lambda *args, **kwargs: list(silences))
    monkeypatch.setattr(analyzer, "transcribe", lambda *args, **kwargs: _segments())

    report = analyzer.analyze("fake.mp4", analyzer.AnalyzerConfig(speech=True))

    assert report.evidence
    assert [item.silence for item in report.evidence] == silences
    assert report.decisions == expected
    assert report.metadata["speech_evidence"]["available"] is True
    assert report.metadata["speech_evidence"]["segments"] == 2


def test_analyzer_falls_back_when_optional_whisper_is_missing(monkeypatch) -> None:
    silences = [TimeRange(2.0, 4.0)]
    expected = SilencePolicy(PROFILES["natural"]).decide(silences)

    monkeypatch.setattr(analyzer, "probe_duration", lambda path: 10.0)
    monkeypatch.setattr(analyzer, "detect_silence", lambda *args, **kwargs: list(silences))
    monkeypatch.setattr(
        analyzer,
        "transcribe",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("Speech features require faster-whisper. Install with: python -m pip install -e '.[speech]'")
        ),
    )

    report = analyzer.analyze("fake.mp4", analyzer.AnalyzerConfig(speech=True))

    assert report.decisions == expected
    assert report.evidence[0].quality.fallback_mode is True
    assert report.metadata["speech_evidence"]["available"] is False


def test_analysis_report_evidence_defaults_to_empty() -> None:
    from kubrick.core.models import AnalysisReport

    report = AnalysisReport(10.0, [], [])
    assert report.evidence == []


def test_core_and_speech_imports_are_acyclic() -> None:
    import kubrick.core
    import kubrick.speech

    assert kubrick.core.AnalysisReport is not None
    assert kubrick.speech.SpeechEvidenceAggregator is not None


# Keep this import-level assertion explicit: Phase 1 must not change decisions.
def _decision_signature(decisions: list[EditDecision]) -> list[tuple]:
    return [(d.source.start, d.source.end, d.kind, d.confidence, d.target_duration, d.reason) for d in decisions]


def test_decision_signature_is_policy_only() -> None:
    silences = [TimeRange(10.0, 12.0)]
    baseline = SilencePolicy(PROFILES["natural"]).decide(silences)
    enriched = SpeechEvidenceAggregator(20.0).analyze(silences, _segments())

    assert enriched[0].context.before is not None
    assert _decision_signature(baseline) == _decision_signature(
        SilencePolicy(PROFILES["natural"]).decide([item.silence for item in enriched])
    )
