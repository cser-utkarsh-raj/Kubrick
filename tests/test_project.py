from __future__ import annotations

import json
from pathlib import Path

import pytest

from kubrick.core import AudioClip, MediaClip, Overlay, Project, PRESETS
from kubrick.editor import (
    add_audio,
    add_filter,
    add_overlay,
    cut_range,
    merge_clips,
    project_duration,
    trim_clip,
)


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
    assert loaded.schema_version == 1


def test_project_save_is_atomic_and_leaves_no_temp_file(tmp_path: Path) -> None:
    path = tmp_path / "demo.kubrick.json"
    Project(video=[MediaClip("input.mp4", 0, 2)]).save(path)
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1
    assert list(tmp_path.glob(".*.tmp")) == []


def test_unknown_future_schema_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "future.kubrick.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 999,
                "name": "future",
                "video": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsupported project schema version"):
        Project.load(path)


def test_validate_rejects_gapped_main_timeline(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"placeholder")
    project = Project(
        video=[
            MediaClip(str(source), 0, 2, 0),
            MediaClip(str(source), 2, 4, 3),
        ]
    )
    with pytest.raises(ValueError, match="continuous timeline"):
        project.validate()


def test_validate_rejects_overlay_beyond_timeline(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"placeholder")
    project = Project(
        video=[MediaClip(str(source), 0, 2, 0)],
        overlays=[Overlay("text", "Too late", 1, 3)],
    )
    with pytest.raises(ValueError, match="overlay extends"):
        project.validate()


def test_audio_duration() -> None:
    audio = AudioClip("music.wav", 2, 7, 5)
    assert audio.duration == 5
    assert audio.timeline_end == 10


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


def test_cut_shifts_audio_and_overlays() -> None:
    project = Project(
        video=[MediaClip("a.mp4", 0, 10)],
        audio=[AudioClip("music.wav", 0, 10, 8)],
        overlays=[Overlay("text", "end", 8, 10)],
    )
    cut = cut_range(project, 3, 5)
    assert cut.audio[0].timeline_start == 6
    assert (cut.audio[0].source_start, cut.audio[0].source_end) == (0, 10)
    assert (cut.overlays[0].start, cut.overlays[0].end) == (6, 8)


def test_cut_rejects_out_of_range() -> None:
    project = Project(video=[MediaClip("a.mp4", 0, 10)])
    with pytest.raises(ValueError, match="exceeds project duration"):
        cut_range(project, 2, 11)


def test_filter_is_non_destructive() -> None:
    project = Project(video=[MediaClip("a.mp4", 0, 3)])
    filtered = add_filter(project, "eq=contrast=1.05")
    assert filtered.video[0].filters == ("eq=contrast=1.05",)
    assert project.video[0].filters == ()


def test_layers_can_be_added_non_destructively() -> None:
    project = Project(video=[MediaClip("a.mp4", 0, 3)])
    audio = AudioClip("music.wav", 0, 2, 0, 0.5)
    overlay = Overlay("text", "Hello", 0, 2)
    with_audio = add_audio(project, audio)
    with_overlay = add_overlay(with_audio, overlay)
    assert with_audio.audio == [audio]
    assert with_overlay.overlays == [overlay]
    assert project.audio == []
    assert project.overlays == []


def test_project_duration() -> None:
    project = Project(video=[MediaClip("a.mp4", 0, 4, 0), MediaClip("a.mp4", 5, 8, 4)])
    assert project_duration(project) == 7


def test_presets_are_named_and_useful() -> None:
    assert {"clean", "gentle", "tight", "punchy", "mono-voice"}.issubset(PRESETS)
    assert PRESETS["clean"].profile == "natural"


def test_invalid_project_has_no_video(tmp_path: Path) -> None:
    project = Project()
    with pytest.raises(ValueError, match="at least one video clip"):
        project.validate()
