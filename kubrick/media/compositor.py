from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from kubrick.core.project import Project
from kubrick.media.ffmpeg import FFmpegError, _run, has_audio_stream, probe_duration


_SAFE_FFMPEG_FILTER = re.compile(r"^[A-Za-z0-9_=.\-+/:,@% ]+$")


def _duration(clip) -> float:
    if clip.duration is not None:
        return clip.duration
    return max(0.0, probe_duration(clip.path) - clip.source_start) / clip.speed


def _text_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_project(
    project: Project,
    output_path: str | Path,
    *,
    crf: int = 18,
    preset: str = "medium",
    audio_bitrate: str = "192k",
) -> None:
    """Render a Project to MP4 using one synchronized FFmpeg graph.

    The model intentionally stays small: a main video track, optional audio
    clips, and timed text/image/shape overlays. Every operation is non-destructive.
    """
    project.validate()
    if not 0 <= crf <= 51:
        raise ValueError("crf must be 0..51")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    video = sorted(project.video, key=lambda c: c.timeline_start)
    if any(c.duration is None for c in video):
        raise ValueError("Project video clips must have explicit source_end values")
    total_duration = max(c.timeline_start + _duration(c) for c in video)

    inputs: list[str] = ["ffmpeg", "-hide_banner", "-y"]
    input_kinds: list[str] = []
    for clip in video:
        inputs += ["-i", str(clip.path)]
        input_kinds.append("video")
    for clip in project.audio:
        inputs += ["-i", str(clip.path)]
        input_kinds.append("audio")
    overlay_input_indices: list[int] = []
    for overlay in project.overlays:
        if overlay.kind == "image":
            inputs += ["-loop", "1", "-i", overlay.value]
            overlay_input_indices.append(len(input_kinds))
            input_kinds.append("image")

    filters: list[str] = []
    video_labels: list[str] = []
    audio_labels: list[str] = []

    for index, clip in enumerate(video):
        duration = _duration(clip)
        filters.append(
            f"[{index}:v]trim=start={clip.source_start:.6f}:end={clip.source_end:.6f},"
            f"setpts=PTS-STARTPTS,setpts=PTS/{clip.speed:.6f}[v{index}]"
        )
        current = f"[v{index}]"
        for filter_index, expression in enumerate(clip.filters):
            if not _SAFE_FFMPEG_FILTER.match(expression):
                raise ValueError(f"Unsafe filter expression: {expression!r}")
            label = f"vf{index}_{filter_index}"
            filters.append(f"{current}{expression}[{label}]")
            current = f"[{label}]"
        if clip.timeline_start > 0:
            label = f"vt{index}"
            delay_ms = int(round(clip.timeline_start * 1000))
            filters.append(f"{current}tpad=start_mode=add:start_duration={clip.timeline_start:.6f}[{label}]")
            current = f"[{label}]"
        video_labels.append(current)

        if has_audio_stream(clip.path):
            filters.append(
                f"[{index}:a]atrim=start={clip.source_start:.6f}:end={clip.source_end:.6f},"
                f"asetpts=PTS-STARTPTS,atempo={_atempo_chain(clip.speed)},"
                f"volume={clip.volume:.4f}[a{index}]"
            )
        else:
            filters.append(f"anullsrc=r=48000:cl=stereo:d={duration:.6f}[a{index}]")
        audio_labels.append(f"[a{index}]")

    if len(video_labels) == 1 and video[0].timeline_start == 0:
        current_video = video_labels[0]
    else:
        concat_labels = "".join(video_labels)
        filters.append(f"{concat_labels}concat=n={len(video_labels)}:v=1:a=0[basev]")
        current_video = "[basev]"

    # Keep a single, deterministic timeline: overlays are composited after the main track.
    image_pos = 0
    for overlay in sorted(project.overlays, key=lambda item: item.start):
        end = overlay.end if overlay.end is not None else total_duration
        if end <= overlay.start:
            continue
        label = f"ov{image_pos}"
        if overlay.kind == "text":
            text = _text_escape(overlay.value)
            expression = (
                f"drawtext=text='{text}':x={overlay.x}:y={overlay.y}:fontsize={overlay.font_size}:"
                f"fontcolor={overlay.color}@{overlay.opacity:.3f}:"
                f"enable='between(t,{overlay.start:.6f},{end:.6f})'"
            )
            filters.append(f"{current_video}{expression}[{label}]")
        elif overlay.kind == "image":
            input_index = overlay_input_indices[image_pos]
            scale = ""
            if overlay.width and overlay.height:
                scale = f",scale={overlay.width}:{overlay.height}:force_original_aspect_ratio=decrease"
            filters.append(
                f"[{input_index}:v]format=rgba{scale},setpts=PTS-STARTPTS[img{image_pos}]"
            )
            filters.append(
                f"{current_video}[img{image_pos}]overlay=x={overlay.x}:y={overlay.y}:"
                f"enable='between(t,{overlay.start:.6f},{end:.6f})'[${label}]".replace("[$", "[")
            )
        else:
            width = overlay.width or project.width or 1920
            height = overlay.height or project.height or 1080
            filters.append(
                f"color=c={overlay.value}@{overlay.opacity:.3f}:s={width}x{height}:d={end-overlay.start:.6f},"
                f"format=rgba,setpts=PTS-STARTPTS[shape{image_pos}]"
            )
            filters.append(
                f"{current_video}[shape{image_pos}]overlay=x={overlay.x}:y={overlay.y}:"
                f"enable='between(t,{overlay.start:.6f},{end:.6f})'[{label}]"
            )
        current_video = f"[{label}]"
        image_pos += 1

    # External audio is mixed on top of the synchronized main audio track.
    audio_inputs = list(audio_labels)
    for offset, clip in enumerate(project.audio):
        input_index = len(video) + offset
        duration = _duration(clip)
        end = clip.source_end if clip.source_end is not None else clip.source_start + duration
        chain = (
            f"[{input_index}:a]atrim=start={clip.source_start:.6f}:end={end:.6f},"
            f"asetpts=PTS-STARTPTS,volume={clip.volume:.4f}"
        )
        if clip.fade_in:
            chain += f",afade=t=in:st=0:d={clip.fade_in:.6f}"
        if clip.fade_out:
            fade_start = max(0.0, duration - clip.fade_out)
            chain += f",afade=t=out:st={fade_start:.6f}:d={clip.fade_out:.6f}"
        delay = int(round(clip.timeline_start * 1000))
        chain += f",adelay={delay}:all=1,atrim=duration={total_duration:.6f}[exta{offset}]"
        filters.append(chain)
        audio_inputs.append(f"[exta{offset}]")

    if len(audio_inputs) == 1:
        current_audio = audio_inputs[0]
    else:
        filters.append(
            f"{''.join(audio_inputs)}amix=inputs={len(audio_inputs)}:duration=first:dropout_transition=0:normalize=0[aout]"
        )
        current_audio = "[aout]"

    filters.append(f"{current_video}format=yuv420p[vout]")
    graph = ";\n".join(filters)

    with tempfile.NamedTemporaryFile("w", suffix=".ffscript", encoding="utf-8", delete=False) as handle:
        handle.write(graph)
        script = Path(handle.name)
    try:
        _run([
            *inputs,
            "-filter_complex_script", str(script),
            "-map", "[vout]", "-map", current_audio,
            "-t", f"{total_duration:.6f}",
            "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-c:a", "aac", "-b:a", audio_bitrate,
            "-movflags", "+faststart", str(output),
        ])
    finally:
        script.unlink(missing_ok=True)


def _atempo_chain(speed: float) -> str:
    """FFmpeg atempo accepts 0.5..2.0 per filter; chain for wider ranges."""
    value = speed
    parts: list[str] = []
    while value > 2.0:
        parts.append("atempo=2.0")
        value /= 2.0
    while value < 0.5:
        parts.append("atempo=0.5")
        value /= 0.5
    parts.append(f"atempo={value:.6f}")
    return ",".join(parts)
