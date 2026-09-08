from kubrick.core import DecisionKind, EditorialPolicy, TimeRange, build_timeline, decisions_from_findings
from kubrick.speech.editorial import EditorialFinding


def test_long_pause_is_compressed_not_deleted():
    findings = [EditorialFinding(TimeRange(5, 8), "pause", 0.9, "pause")]
    decisions = decisions_from_findings(findings)
    assert decisions[0].kind is DecisionKind.COMPRESS
    plan = build_timeline(10, decisions)
    assert [(x.source.start, x.source.end) for x in plan.keep] == [(0.0, 5.0), (5.28, 10.0)]


def test_semantic_finding_requires_review_by_default():
    finding = EditorialFinding(TimeRange(2, 2.3), "filler", 0.97, "filler")
    decisions = decisions_from_findings([finding])
    assert decisions[0].kind is DecisionKind.REVIEW


def test_high_confidence_short_filler_can_auto_cut():
    policy = EditorialPolicy(auto_cut_confidence=0.95)
    finding = EditorialFinding(TimeRange(2, 2.2), "filler", 0.99, "filler")
    decisions = decisions_from_findings([finding], policy)
    assert decisions[0].kind is DecisionKind.CUT


def test_overlapping_decisions_merge_safely():
    findings = [
        EditorialFinding(TimeRange(1, 3), "pause", 0.9, "pause"),
        EditorialFinding(TimeRange(2.8, 4), "pause", 0.9, "pause"),
    ]
    decisions = decisions_from_findings(findings)
    plan = build_timeline(5, decisions)
    assert plan.output_duration > 0
    assert all(a.source.end <= b.source.start for a, b in zip(plan.keep, plan.keep[1:]))
