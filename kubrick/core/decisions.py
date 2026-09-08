from __future__ import annotations

from dataclasses import dataclass

from .models import DecisionKind, EditDecision, TimeRange
from .policy import EditingProfile


@dataclass(frozen=True, slots=True)
class SilencePolicy:
    profile: EditingProfile

    def decide(self, silences: list[TimeRange]) -> list[EditDecision]:
        decisions: list[EditDecision] = []
        for silence in silences:
            duration = silence.duration
            if duration < self.profile.min_silence:
                continue
            keep = min(self.profile.keep_pause, max(0.0, duration - 0.04))
            removed = duration - keep
            if removed <= 0:
                continue
            confidence = min(0.999, 0.80 + min(0.19, duration / 10.0))
            kind = DecisionKind.CUT if keep <= 0.03 else DecisionKind.COMPRESS
            decisions.append(
                EditDecision(
                    source=silence,
                    kind=kind,
                    confidence=confidence,
                    reason=f"{duration:.2f}s low-energy pause; preserve {keep:.2f}s for natural cadence",
                    target_duration=keep,
                    metadata={"removed_seconds": removed},
                )
            )
        return decisions
