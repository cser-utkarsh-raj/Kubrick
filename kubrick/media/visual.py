from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from kubrick.core.models import TimeRange

_SCENE_TIME = re.compile(r"pts_time:([0-9.]+)")
_BLACK_START = re.compile(r"black_start:\s*([0-9.]+)")
_BLACK_END = re.compile(r"black_end:\s*([0-9.]+)")
_FREEZE_START = re.compile(r"freeze_start:\s*([0-9.]+)")
_FREEZE_END = re.compile(r"freeze_end:\s*([0-9.]+)")


@dataclass(frozen=True, slots=True)
class SceneChange:
    """A visual cut detected from adjacent-frame difference."""

    time: float
    score: float | None = None


@dataclass(frozen=True, slots=True)
class VisualReport:
    """Deterministic visual evidence used by the editorial layer."""

    scenes: list[SceneChange]
    blackouts: list[TimeRange]
    frozen_frames: list[TimeRange]


def _run_filter(path: str | Path, filter_graph: str) -> str:
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-an",
            "-vf",
            filter_graph,
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        lines = [line.strip() for line in proc.stderr.splitlines() if line.strip()]
        raise RuntimeError(lines[-1] if lines else "FFmpeg visual analysis failed")
    return proc.stderr


def detect_scene_changes(
    path: str | Path,
    *,
    threshold: float = 0.35,
) -> list[SceneChange]:
    """Detect meaningful cuts without decoding frames in Python."""
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    stderr = _run_filter(path, f"select='gt(scene,{threshold})',showinfo")
    return [SceneChange(float(match.group(1))) for match in _SCENE_TIME.finditer(stderr)]


def parse_interval_log(
    stderr: str,
    *,
    start_pattern: re.Pattern[str],
    end_pattern: re.Pattern[str],
) -> list[TimeRange]:
    """Pair start/end diagnostics while tolerating an interval open at EOF."""
    start: float | None = None
    result: list[TimeRange] = []
    for line in stderr.splitlines():
        found_start = start_pattern.search(line)
        if found_start:
            start = float(found_start.group(1))
            continue
        found_end = end_pattern.search(line)
        if found_end and start is not None:
            end = float(found_end.group(1))
            if end >= start:
                result.append(TimeRange(start, end))
            start = None
    return result


def detect_blackouts(path: str | Path) -> list[TimeRange]:
    """Find sustained black frames, useful for continuity and bad-take warnings."""
    stderr = _run_filter(path, "blackdetect=d=0.25:pix_th=0.10")
    return parse_interval_log(stderr, start_pattern=_BLACK_START, end_pattern=_BLACK_END)


def detect_frozen_frames(path: str | Path) -> list[TimeRange]:
    """Find sustained frozen video, another strong continuity signal."""
    stderr = _run_filter(path, "freezedetect=n=0.003:d=0.50")
    return parse_interval_log(stderr, start_pattern=_FREEZE_START, end_pattern=_FREEZE_END)


def analyze_visuals(path: str | Path, *, threshold: float = 0.35) -> VisualReport:
    """Collect scene, blackout and freeze evidence in one deterministic pass API."""
    return VisualReport(
        scenes=detect_scene_changes(path, threshold=threshold),
        blackouts=detect_blackouts(path),
        frozen_frames=detect_frozen_frames(path),
    )
