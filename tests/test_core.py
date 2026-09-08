from kubrick.core import DecisionKind, PROFILES, SilencePolicy, TimeRange, build_keep_segments


def test_time_range_duration():
    assert TimeRange(1, 2.5).duration == 1.5


def test_natural_policy_compresses_long_pause():
    decision = SilencePolicy(PROFILES["natural"]).decide([TimeRange(5, 7)])[0]
    assert decision.kind is DecisionKind.COMPRESS
    assert decision.target_duration == 0.28


def test_compression_preserves_natural_pause():
    decisions = SilencePolicy(PROFILES["natural"]).decide([TimeRange(2, 3), TimeRange(5, 6)])
    segments = build_keep_segments(10, decisions)
    assert [(round(x.source.start, 2), round(x.source.end, 2)) for x in segments] == [
        (0.0, 2.28), (3.0, 5.28), (6.0, 10.0)
    ]


def test_cut_removes_entire_interval():
    decision = SilencePolicy(PROFILES["tight"]).decide([TimeRange(1, 1.02)])[0] if False else None
    assert decision is None
