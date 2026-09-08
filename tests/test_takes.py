import pytest

from kubrick.editor.takes import _ratio, select_best_take


def test_ratio_handles_zero_duration() -> None:
    assert _ratio(1.0, 0.0) == 1.0


def test_select_best_take_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one take"):
        select_best_take([])
