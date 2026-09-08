from __future__ import annotations

import re
import tempfile
from pathlib import Path

from kubrick.core.project import Project
from kubrick.media.ffmpeg import _run, has_audio_stream, probe_duration


_SAFE_FFMPEG_FILTER = re.compile(r"^[A-Za-z0-9_=.\-+/:,@% ]+$")
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")


def _duration(clip) -> float:
    if clip.source_end is not None:
        return (clip.source_end - clip.source_start) / getattr(clip, "speed", 1.0)
    return max(0.0, probe_duration(clip.path) - clip.source_start) / getattr(clip, "speed", 1.0)


def _text_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def _shape_color(value: str) -> str:
    value = value.strip()
    if _HEX_COLOR.fullmatch(value):
        return "0x" + value[1:7]
    return value


def render_project(
    project: Project,
    output_path: str | Path,
    *,
    crf: int = 18,
    preset: str = "medium",
    audio_bitrate: str = "192k",
) -> None:
    """Render a small, practical multi-layer project through one FFmpeg graph."""
    project.validate()
    if not 0 <= crf <= 51:
        raise ValueError("crf must be 0..51")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    input_paths = {Path(clip.path).resolve() for clip in project.video}
    if output.resolve() in input_paths:
        raise ValueError("output_path must be different from the source video")

    video = sorted(project.video, key=lambda c: c.timeline_start)
    if any(c.duration is None for c in video):
        raise ValueError("Project video clips must have explicit source_end values")
    expected = 0.0
    for clip in video:
        if abs(clip.timeline_start - expected) > 1e-4:
            raise ValueError(
                "main video clips must be sequential; use merge_clips() to normalize them"
            )
        expected += _duration(clip)
    total_duration = expected

    inputs: list[str] = ["ffmpeg", "-hide_banner", "-y"]
    for clip in video:
        inputs += ["-i", str(clip.path)]
    for clip in project.audio:
        inputs += ["-i", str(clip.path)]

    image_inputs: dict[int, int] = {}
    next_input = len(video) + len(project.audio)
    for overlay_index, overlay in enumerate(project.overlays):
        if overlay.kind == "image":
            image_inputs[overlay_index] = next_input
            inputs += ["-loop", "1", "-i", overlay.value]
            next_input += 1

    filters: list[str] = []
    video_labels: list[str] = []
    audio_labels: list[str] = []

    for index, clip in enumerate(video):
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
        video_labels.append(current)

        if has_audio_stream(clip.path):
            filters.append(
                f"[{index}:a]atrim=start={clip.source_start:.6f}:end={clip.source_end:.6f},"
                f"asetpts=PTS-STARTPTS,{_atempo_chain(clip.speed)},volume={clip.volume:.4f}[a{index}]"
            )
        else:
            filters.append(
                f"anullsrc=r=48000:cl=stereo:d={_duration(clip):.6f}[a{index}]"
            )
        audio_labels.append(f"[a{index}]")

    if len(video_labels) == 1:
        current_video = video_labels[0]
    else:
        filters.append(
            f"{''.join(video_labels)}concat=n={len(video_labels)}:v=1:a=0[basev]"
        )
        current_video = "[basev]"

    for overlay_index, overlay in sorted(
        enumerate(project.overlays), key=lambda item: item[1].start
    ):
        end = min(
            overlay.end if overlay.end is not None else total_duration,
            total_duration,
        )
        if end <= overlay.start:
            continue
        label = f"ov{overlay_index}"
        if overlay.kind == "text":
            expression = (
                f"drawtext=text='{_text_escape(overlay.value)}':x={overlay.x}:y={overlay.y}:"
                f"fontsize={overlay.font_size}:fontcolor={overlay.color}@{overlay.opacity:.3f}:"
                f"enable='between(t,{overlay.start:.6f},{end:.6f})'"
            )
            filters.append(f"{current_video}{expression}[{label}]")
        elif overlay.kind == "image":
            input_index = image_inputs[overlay_index]
            scale = ""
            if overlay.width and overlay.height:
                scale = (
                    f",scale={overlay.width}:{overlay.height}:"
                    "force_original_aspect_ratio=decrease"
                )
            filters.append(
                f"[{input_index}:v]format=rgba{scale},setpts=PTS-STARTPTS[img{overlay_index}]"
            )
            filters.append(
                f"{current_video}[img{overlay_index}]overlay=x={overlay.x}:y={overlay.y}:"
                f"enable='between(t,{overlay.start:.6f},{end:.6f})'[{label}]"
            )
        else:
            width = overlay.width or project.width or 1920
            height = overlay.height or project.height or 1080
            color = _shape_color(overlay.value)
            filters.append(
                f"color=c={color}@{overlay.opacity:.3f}:s={width}x{height}:"
                f"d={max(0.01, end - overlay.start):.6f},format=rgba[shape{overlay_index}]"
            )
            filters.append(
                f"{current_video}[shape{overlay_index}]overlay=x={overlay.x}:y={overlay.y}:"
                f"enable='between(t,{overlay.start:.6f},{end:.6f})'[{label}]"
            )
        current_video = f"[{label}]"

    audio_inputs = list(audio_labels)
    for offset, clip in enumerate(project.audio):
        input_index = len(video) + offset
        source_end = clip.source_end if clip.source_end is not None else probe_duration(clip.path)
        duration = max(0.0, source_end - clip.source_start)
        chain = (
            f"[{input_index}:a]atrim=start={clip.source_start:.6f}:end={source_end:.6f},"
            f"asetpts=PTS-STARTPTS,volume={clip.volume:.4f}"
        )
        if clip.fade_in:
            chain += f",afade=t=in:st=0:d={min(clip.fade_in, duration):.6f}"
        if clip.fade_out:
            fade_start = max(0.0, duration - clip.fade_out)
            chain += (
                f",afade=t=out:st={fade_start:.6f}:"
                f"d={min(clip.fade_out, duration):.6f}"
            )
        delay = int(round(clip.timeline_start * 1000))
        chain += f",adelay={delay}:all=1,atrim=duration={total_duration:.6f}[exta{offset}]"
        filters.append(chain)
        audio_inputs.append(f"[exta{offset}]")

    if len(audio_inputs) == 1:
        current_audio = audio_inputs[0]
    else:
        filters.append(
            f"{''.join(audio_inputs)}amix=inputs={len(audio_inputs)}:duration=first:"
            "dropout_transition=0:normalize=0[aout]"
        )
        current_audio = "[aout]"

    filters.append(f"{current_video}format=yuv420p[vout]")
    graph = ";\n".join(filters)

    with tempfile.NamedTemporaryFile(
        "w", suffix=".ffscript", encoding="utf-8", delete=False
    ) as handle:
        handle.write(graph)
        script = Path(handle.name)
    try:
        _run(
            [
                *inputs,
                "-filter_complex_script",
                str(script),
                "-map",
                "[vout]",
                "-map",
                current_audio,
                "-t",
                f"{total_duration:.6f}",
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-c:a",
                "aac",
                "-b:a",
                audio_bitrate,
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
    finally:
        script.unlink(missing_ok=True)


def _atempo_chain(speed: float) -> str:
    """Build an atempo chain because each FFmpeg filter accepts 0.5..2.0."""
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
