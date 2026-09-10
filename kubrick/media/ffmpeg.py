from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from kubrick.core.models import KeepSegment


class FFmpegError(RuntimeError):
    pass


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-20:])
        raise FFmpegError(tail or "FFmpeg operation failed")
    return proc


def probe_duration(path: str | Path) -> float:
    proc = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path),
    ])
    try:
        value = float(json.loads(proc.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FFmpegError("Could not read media duration") from exc
    if value <= 0:
        raise FFmpegError("Media duration is not positive")
    return value


def has_audio_stream(path: str | Path) -> bool:
    proc = _run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=index", "-of", "csv=p=0", str(path),
    ])
    return bool(proc.stdout.strip())


def render_keep_segments(
    input_path: str | Path,
    output_path: str | Path,
    segments: list[KeepSegment],
    *,
    crf: int = 18,
    preset: str = "medium",
    audio_bitrate: str = "192k",
) -> None:
    """Render retained A/V intervals into a synchronized MP4."""
    if not segments:
        raise ValueError("No segments to render")
    if not 0 <= crf <= 51:
        raise ValueError("crf must be 0..51")
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if not has_audio_stream(input_path):
        raise FFmpegError("Input has no audio stream; Kubrick requires synchronized A/V media")
    duration = probe_duration(input_path)
    previous_end = 0.0
    for segment in segments:
        if segment.source.start < 0 or segment.source.end > duration + 1e-6:
            raise ValueError("Keep segment exceeds source duration")
        if segment.source.end <= segment.source.start:
            raise ValueError("Keep segment must have positive duration")
        if segment.source.start < previous_end - 1e-6:
            raise ValueError("Keep segments must be ordered and non-overlapping")
        previous_end = segment.source.end
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filters: list[str] = []
    for i, segment in enumerate(segments):
        s, e = segment.source.start, segment.source.end
        filters.append(f"[0:v]trim=start={s:.6f}:end={e:.6f},setpts=PTS-STARTPTS[v{i}]")
        filters.append(f"[0:a]atrim=start={s:.6f}:end={e:.6f},asetpts=PTS-STARTPTS[a{i}]")
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(segments)))
    filters.append(f"{concat_inputs}concat=n={len(segments)}:v=1:a=1[v][a]")

    with tempfile.NamedTemporaryFile("w", suffix=".ffscript", encoding="utf-8", delete=False) as script:
        script.write(";\n".join(filters))
        script_path = Path(script.name)

    try:
        _run([
            "ffmpeg", "-hide_banner", "-y", "-i", str(input_path),
            "-filter_complex_script", str(script_path),
            "-map", "[v]", "-map", "[a]",
            "-map_metadata", "0", "-map_chapters", "0",
            "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-c:a", "aac", "-b:a", audio_bitrate,
            "-movflags", "+faststart", str(output_path),
        ])
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    finally:
        script_path.unlink(missing_ok=True)
