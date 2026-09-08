from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kubrick.core import AnalysisReport, PROFILES, SilencePolicy
from kubrick.core.models import DecisionKind, EditDecision, TimeRange
from kubrick.media import analyze_visuals, probe_duration
from kubrick.media.silencedetect import detect_silence


@dataclass(frozen=True, slots=True)
class AnalyzerConfig:
    profile: str = "natural"
    noise_db: float = -38.0
    scene_threshold: float = 0.35
    visual: bool = True

    def __post_init__(self) -> None:
        if self.profile not in PROFILES:
            raise ValueError(f"Unknown profile: {self.profile}")
        if self.noise_db >= 0:
            raise ValueError("noise_db must be negative")
        if not 0 < self.scene_threshold <= 1:
            raise ValueError("scene_threshold must be between 0 and 1")


def _visual_review_decisions(blackouts: list[TimeRange], freezes: list[TimeRange]) -> list[EditDecision]:
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


def analyze(path: str | Path, config: AnalyzerConfig = AnalyzerConfig()) -> AnalysisReport:
    profile = PROFILES[config.profile]
    duration = probe_duration(path)
    silences = detect_silence(
        path,
        noise_db=config.noise_db,
        min_duration=profile.min_silence,
        duration=duration,
    )
    decisions = SilencePolicy(profile).decide(silences)

    metadata = {
        "profile": profile.name,
        "noise_db": config.noise_db,
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
        metadata=metadata,
    )
