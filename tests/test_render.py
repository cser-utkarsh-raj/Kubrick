from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from kubrick.core import MediaClip, Project
from kubrick.editor import cut_range
from kubrick.media import probe_duration, render_project


pytestmark = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and FFprobe are required for render integration tests",
)


def _make_fixture(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=48000:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
    )


def test_render_project_produces_playable_mp4(tmp_path: Path) -> None:
    source = tmp_path / "fixture.mp4"
    output = tmp_path / "rendered.mp4"
    _make_fixture(source)
    project = Project(video=[MediaClip(str(source), 0, 1.5, 0)])

    render_project(project, output, crf=28, preset="ultrafast")

    assert output.is_file()
    assert probe_duration(output) == pytest.approx(1.5, abs=0.08)


def test_render_project_handles_timeline_cut(tmp_path: Path) -> None:
    source = tmp_path / "fixture.mp4"
    output = tmp_path / "cut.mp4"
    _make_fixture(source)
    project = Project(video=[MediaClip(str(source), 0, 2, 0)])
    edited = cut_range(project, 0.8, 1.2)

    render_project(edited, output, crf=28, preset="ultrafast")

    assert output.is_file()
    assert probe_duration(output) == pytest.approx(1.6, abs=0.08)
