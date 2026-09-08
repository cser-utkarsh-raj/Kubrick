"""Turn speech evidence into conservative, reviewable edit decisions."""

from __future__ import annotations

from dataclasses import dataclass

from kubrick.core.models import DecisionKind, EditDecision, TimeRange
from kubrick.speech.editorial import EditorialFinding


@dataclass(frozen=True, slots=True)
class EditorialPolicy:
    natural_pause: float = 0.28
    long_pause: float = 0.45
    long_pause_threshold: float = 2.5
    auto_cut_confidence: float = 0.985
    review_confidence: float = 0.75
    max_auto_cut_duration: float = 1.2


def decisions_from_findings(
    findings: list[EditorialFinding],
    policy: EditorialPolicy = EditorialPolicy(),
) -> list[EditDecision]:
    """Convert findings to conservative decisions.

    Pauses are safe to compress; semantic findings remain REVIEW by default.
    This intentionally prevents an imperfect transcription model from silently
    deleting meaningful speech.
    """
    decisions: list[EditDecision] = []
    for finding in findings:
        if finding.kind == "pause":
            target = policy.long_pause if finding.range.duration >= policy.long_pause_threshold else policy.natural_pause
            target = min(target, finding.range.duration)
            decisions.append(EditDecision(finding.range, DecisionKind.COMPRESS, finding.confidence, finding.reason, target))
        elif finding.kind in {"filler", "false_start", "repetition"}:
            confidence = finding.confidence
            if confidence >= policy.auto_cut_confidence and finding.range.duration <= policy.max_auto_cut_duration:
                decisions.append(EditDecision(finding.range, DecisionKind.CUT, confidence, finding.reason))
            elif confidence >= policy.review_confidence:
                decisions.append(EditDecision(finding.range, DecisionKind.REVIEW, confidence, finding.reason))
    return sorted(decisions, key=lambda d: (d.source.start, d.source.end))
