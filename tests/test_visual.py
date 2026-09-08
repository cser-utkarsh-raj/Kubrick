from kubrick.core.models import TimeRange
from kubrick.media.visual import (
    _BLACK_END,
    _BLACK_START,
    SceneChange,
    parse_interval_log,
)


def test_parse_visual_intervals_pairs_diagnostics() -> None:
    stderr = """
    [blackdetect @ 0x0] black_start:1.250 black_end:2.750 black_duration:1.500
    [blackdetect @ 0x0] black_start:5.000 black_end:6.000 black_duration:1.000
    """
    assert parse_interval_log(
        stderr,
        start_pattern=_BLACK_START,
        end_pattern=_BLACK_END,
    ) == [TimeRange(1.25, 2.75), TimeRange(5.0, 6.0)]


def test_parse_visual_intervals_ignores_unclosed_interval() -> None:
    stderr = "[blackdetect @ 0x0] black_start:9.000\n"
    assert parse_interval_log(
        stderr,
        start_pattern=_BLACK_START,
        end_pattern=_BLACK_END,
    ) == []


def test_scene_change_is_immutable_evidence() -> None:
    change = SceneChange(12.5)
    assert change.time == 12.5
