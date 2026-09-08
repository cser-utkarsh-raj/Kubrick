from __future__ import annotations

import json
import subprocess
from pathlib import Path

from kubrick.core.models import KeepSegment


class FFmpegError(RuntimeError):
    pass


def probe_duration(path: str | Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise FFmpegError(proc.stderr.strip() or "ffprobe failed")
    try:
        value = float(json.loads(proc.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FFmpegError("Could not read media duration") from exc
    if value <= 0:
        raise FFmpegError("Media duration is not positive")
    return value


def render_keep_segments(
    input_path: str | Path,
    output_path: str | Path,
    segments: list[KeepSegment],
    *,
    crf: int = 18,
    preset: str = "medium",
    audio_bitrate: str = "192k",
) -> None:
    if not segments:
        raise ValueError("No segments to render")
    if not 0 <= crf <= 51:
        raise ValueError("crf must be 0..51")
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filters: list[str] = []
    for i, segment in enumerate(segments):
        s, e = segment.source.start, segment.source.end
        filters.append(
            f"[0:v]trim=start={s:.6f}:end={e:.6f},setpts=PTS-STARTPTS[v{i}]"
        )
        filters.append(
            f"[0:a]atrim=start={s:.6f}:end={e:.6f},asetpts=PTS-STARTPTS[a{i}]"
        )
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(segments)))
    filters.append(f"{concat_inputs}concat=n={len(segments)}:v=1:a=1[v][a]")

    cmd = [
        "ffmpeg", "-hide_banner", "-y", "-i", str(input_path),
        "-filter_complex", ";".join(filters),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-c:a", "aac", "-b:a", audio_bitrate,
        "-movflags", "+faststart", str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-20:])
        raise FFmpegError(tail or "FFmpeg render failed")
