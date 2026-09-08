from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from kubrick.core import AudioClip, MediaClip, Overlay, Project
from kubrick.ui.timeline import TimelineWidget


def test_timeline_tracks_shared_project_clock(qtbot) -> None:
    project = Project(
        video=[MediaClip("video.mp4", 0, 10)],
        audio=[AudioClip("music.wav", 0, 4, 3)],
        overlays=[Overlay("text", "hello", 2, 6)],
    )
    widget = TimelineWidget()
    qtbot.addWidget(widget)
    widget.set_project(project)

    tracks = widget._tracks()
    assert [(item[0], item[1], item[2], item[3]) for item in tracks] == [
        ("VIDEO", 0, 0, 10),
        ("AUDIO", 0, 3, 7),
        ("TEXT", 0, 2, 6),
    ]
    assert widget._time_for_x(widget._x_for_time(4.5)) == pytest.approx(4.5)


def test_timeline_has_content_width_for_zoom(qtbot) -> None:
    widget = TimelineWidget()
    qtbot.addWidget(widget)
    widget.set_project(Project(video=[MediaClip("video.mp4", 0, 120)]))
    assert widget.minimumWidth() >= int(widget.LEFT + 120 * widget.zoom)
