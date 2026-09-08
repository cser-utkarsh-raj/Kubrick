from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kubrick.core import AnalysisReport, PROFILES, SilencePolicy
from kubrick.media import probe_duration
from kubrick.media.silencedetect import detect_silence


@dataclass(frozen=True, slots=True)
class AnalyzerConfig:
    profile: str = "natural"
    noise_db: float = -38.0

    def __post_init__(self) -> None:
        if self.profile not in PROFILES:
            raise ValueError(f"Unknown profile: {self.profile}")


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
    return AnalysisReport(
        duration=duration,
        silences=silences,
        decisions=decisions,
        metadata={"profile": profile.name, "noise_db": config.noise_db},
    )
