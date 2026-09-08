from __future__ import annotations

from pathlib import Path

import pytest

from kubrick.core import AudioClip, MediaClip, Overlay, Project, PRESETS
from kubrick.editor import add_filter, cut_range, merge_clips, trim_clip


def test_project_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"placeholder")
    project = Project(
        name="Demo",
        video=[MediaClip(str(source), 1, 5, 0)],
        audio=[AudioClip(str(source), 0, 2, 1, 0.5)],
        overlays=[Overlay("text", "Hello", 0, 2, x="10", y="20")],
        preset="clean",
    )
    path = tmp_path / "demo.kubrick.json"
    project.save(path)
    loaded = Project.load(path)
    assert loaded.to_dict() == project.to_dict()


def test_trim_is_non_destructive() -> None:
    clip = MediaClip("input.mp4", 0, 10)
    trimmed = trim_clip(clip, 2, 7)
    assert (trimmed.source_start, trimmed.source_end) == (2, 7)
    assert (clip.source_start, clip.source_end) == (0, 10)


def test_merge_places_clips_back_to_back() -> None:
    first = MediaClip("a.mp4", 0, 4)
    second = MediaClip("b.mp4", 2, 7)
    project = merge_clips(first, second)
    assert [clip.timeline_start for clip in project.video] == [0, 4]


def test_cut_removes_range_and_closes_gap() -> None:
    project = Project(video=[MediaClip("a.mp4", 0, 10)])
    cut = cut_range(project, 3, 7)
    assert [(c.source_start, c.source_end, c.timeline_start) for c in cut.video] == [
        (0, 3, 0),
        (7, 10, 3),
    ]


def test_filter_is_non_destructive() -> None:
    project = Project(video=[MediaClip("a.mp4", 0, 3)])
    filtered = add_filter(project, "eq=contrast=1.05")
    assert filtered.video[0].filters == ("eq=contrast=1.05",)
    assert project.video[0].filters == ()


def test_presets_are_named_and_useful() -> None:
    assert {"clean", "gentle", "tight", "punchy", "mono-voice"}.issubset(PRESETS)
    assert PRESETS["clean"].profile == "natural"


def test_invalid_project_has_no_video(tmp_path: Path) -> None:
    project = Project()
    with pytest.raises(ValueError, match="at least one video clip"):
        project.validate()
