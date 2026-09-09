from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def qt_app():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
    app.quit()


def test_timeline_groups_clips_into_shared_tracks(qt_app) -> None:
    from kubrick.core import AudioClip, MediaClip, Overlay, Project
    from kubrick.ui.timeline import TimelineWidget

    project = Project(
        video=[MediaClip("video.mp4", 0, 4), MediaClip("video.mp4", 4, 8, 4)],
        audio=[AudioClip("music.wav", 0, 4, 3)],
        overlays=[Overlay("text", "hello", 2, 6)],
    )
    widget = TimelineWidget()
    widget.set_project(project)

    assert widget._rows() == ["video", "audio", "text"]
    assert widget._items("video") == [
        (0, 0, 4, "video.mp4"),
        (1, 4, 8, "video.mp4"),
    ]
    assert widget._items("audio") == [(0, 3, 7, "music.wav")]
    assert widget._time_for_x(widget._x_for_time(4.5)) == pytest.approx(4.5)
    widget.close()


def test_timeline_has_content_width_for_long_projects(qt_app) -> None:
    from kubrick.core import MediaClip, Project
    from kubrick.ui.timeline import TimelineWidget

    widget = TimelineWidget()
    widget.set_project(Project(video=[MediaClip("video.mp4", 0, 120)]))
    assert widget.minimumWidth() >= int(widget.LEFT + 120 * widget.zoom)
    widget.close()
