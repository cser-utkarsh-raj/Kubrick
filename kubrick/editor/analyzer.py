from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kubrick.core import AnalysisReport, PROFILES, SilencePolicy
from kubrick.core.models import DecisionKind, EditDecision, TimeRange
from kubrick.media import analyze_visuals, probe_duration
from kubrick.media.silencedetect import detect_silence
from kubrick.speech import SilenceEvidence, SpeechDependencyError, SpeechEvidenceAggregator, transcribe


@dataclass(frozen=True, slots=True)
class AnalyzerConfig:
    profile: str = "natural"
    noise_db: float = -38.0
    scene_threshold: float = 0.35
    visual: bool = False
    speech: bool = False
    whisper_model: str = "small"
    language: str | None = None

    def __post_init__(self) -> None:
        if self.profile not in PROFILES:
            raise ValueError(f"Unknown profile: {self.profile}")
        if self.noise_db >= 0:
            raise ValueError("noise_db must be negative")
        if not 0 < self.scene_threshold <= 1:
            raise ValueError("scene_threshold must be between 0 and 1")
        if not self.whisper_model.strip():
            raise ValueError("whisper_model must not be empty")


def _visual_review_decisions(
    blackouts: list[TimeRange], freezes: list[TimeRange]
) -> list[EditDecision]:
    decisions: list[EditDecision] = []
    for interval in blackouts:
        decisions.append(
            EditDecision(
                source=interval,
                kind=DecisionKind.REVIEW,
                confidence=0.94,
                reason="Sustained black video detected; inspect before deciding whether it is intentional.",
                metadata={"visual_signal": "blackout"},
            )
        )
    for interval in freezes:
        decisions.append(
            EditDecision(
                source=interval,
                kind=DecisionKind.REVIEW,
                confidence=0.90,
                reason="Sustained frozen video detected; inspect for a stalled frame or intentional hold.",
                metadata={"visual_signal": "freeze"},
            )
        )
    return decisions


def _speech_evidence(
    path: str | Path,
    silences: list[TimeRange],
    duration: float,
    config: AnalyzerConfig,
) -> tuple[list[SilenceEvidence], dict[str, object]]:
    """Collect optional Whisper context without changing editorial decisions."""
    aggregator = SpeechEvidenceAggregator(duration)
    if not config.speech:
        return aggregator.analyze(silences), {
            "enabled": False,
            "available": False,
            "fallback_mode": False,
            "mode": "silence-only",
        }

    try:
        segments = transcribe(path, model_size=config.whisper_model, language=config.language)
    except SpeechDependencyError as exc:
        return aggregator.analyze(silences), {
            "enabled": True,
            "available": False,
            "fallback_mode": True,
            "mode": "silence-only-fallback",
            "reason": str(exc),
        }

    return aggregator.analyze(silences, segments), {
        "enabled": True,
        "available": True,
        "fallback_mode": False,
        "mode": "whisper",
        "segments": len(segments),
    }


def analyze(path: str | Path, config: AnalyzerConfig = AnalyzerConfig()) -> AnalysisReport:
    """Analyze pauses and attach optional speech evidence.

    Speech evidence is observational only. ``SilencePolicy`` remains the sole
    source of automatic silence decisions, preserving the existing behavior.
    """
    profile = PROFILES[config.profile]
    duration = probe_duration(path)
    silences = detect_silence(
        path,
        noise_db=config.noise_db,
        min_duration=profile.min_silence,
        duration=duration,
    )
    decisions = SilencePolicy(profile).decide(silences)
    evidence, speech_metadata = _speech_evidence(path, silences, duration, config)

    metadata = {
        "profile": profile.name,
        "noise_db": config.noise_db,
        "visual_enabled": config.visual,
        "speech_evidence": speech_metadata,
    }
    if config.visual:
        visuals = analyze_visuals(path, threshold=config.scene_threshold)
        decisions.extend(_visual_review_decisions(visuals.blackouts, visuals.frozen_frames))
        decisions.sort(key=lambda item: (item.source.start, item.source.end, item.kind.value))
        metadata["visual"] = {
            "scene_changes": [scene.time for scene in visuals.scenes],
            "blackouts": [{"start": x.start, "end": x.end} for x in visuals.blackouts],
            "frozen_frames": [{"start": x.start, "end": x.end} for x in visuals.frozen_frames],
            "scene_threshold": config.scene_threshold,
        }

    return AnalysisReport(
        duration=duration,
        silences=silences,
        decisions=decisions,
        evidence=evidence,
        metadata=metadata,
    )
