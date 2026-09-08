from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kubrick.core import AnalysisReport, PROFILES, SilencePolicy
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
        metadata["visual"] = {
            "scene_changes": [scene.time for scene in visuals.scenes],
            "blackouts": [{"start": x.start, "end": x.end} for x in visuals.blackouts],
            "frozen_frames": [{"start": x.start, "end": x.end} for x in visuals.frozen_frames],
        }

    return AnalysisReport(
        duration=duration,
        silences=silences,
        decisions=decisions,
        metadata=metadata,
    )
