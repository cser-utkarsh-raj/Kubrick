from __future__ import annotations

from dataclasses import replace

from kubrick.core.project import AudioClip, MediaClip, Overlay, Project


def _copy_project(project: Project, *, video=None, audio=None, overlays=None) -> Project:
    return Project(
        name=project.name,
        video=list(project.video if video is None else video),
        audio=list(project.audio if audio is None else audio),
        overlays=list(project.overlays if overlays is None else overlays),
        width=project.width,
        height=project.height,
        fps=project.fps,
        preset=project.preset,
    )


def trim_clip(clip: MediaClip, start: float, end: float) -> MediaClip:
    """Return a non-destructive trim of a source clip."""
    if start < clip.source_start or end <= start:
        raise ValueError("trim range must be inside the clip and have positive duration")
    if clip.source_end is not None and end > clip.source_end:
        raise ValueError("trim end exceeds the clip source range")
    return replace(clip, source_start=start, source_end=end)


def project_duration(project: Project) -> float:
    """Return the end of the main video timeline."""
    return max((clip.timeline_start + (clip.duration or 0.0) for clip in project.video), default=0.0)


def _audio_duration(clip: AudioClip) -> float:
    if clip.source_end is None:
        return 0.0
    return max(0.0, clip.source_end - clip.source_start)


def _map_after_cut(value: float, start: float, end: float) -> float:
    if value <= start:
        return value
    if value >= end:
        return value - (end - start)
    return start


def cut_range(project: Project, start: float, end: float) -> Project:
    """Remove a timeline interval and keep video/audio/layers synchronized."""
    if end <= start or start < 0:
        raise ValueError("cut range must be positive")
    duration = project_duration(project)
    if end > duration + 1e-6:
        raise ValueError(f"cut end {end:.3f}s exceeds project duration {duration:.3f}s")

    removed = end - start
    out_video: list[MediaClip] = []
    for clip in project.video:
        clip_start = clip.timeline_start
        clip_end = clip_start + (clip.duration or 0.0)
        if end <= clip_start:
            out_video.append(replace(clip, timeline_start=clip_start - removed))
            continue
        if start >= clip_end:
            out_video.append(clip)
            continue
        left = max(clip_start, start)
        right = min(clip_end, end)
        source_left_end = clip.source_start + (left - clip_start) * clip.speed
        source_right_start = clip.source_start + (right - clip_start) * clip.speed
        if left > clip_start:
            out_video.append(replace(clip, source_end=source_left_end))
        if right < clip_end:
            out_video.append(
                replace(
                    clip,
                    source_start=source_right_start,
                    timeline_start=clip_start + (left - clip_start),
                )
            )

    out_audio: list[AudioClip] = []
    for clip in project.audio:
        clip_duration = _audio_duration(clip)
        clip_start = clip.timeline_start
        clip_end = clip_start + clip_duration
        if end <= clip_start:
            out_audio.append(replace(clip, timeline_start=clip_start - removed))
            continue
        if start >= clip_end:
            out_audio.append(clip)
            continue
        left = max(clip_start, start)
        right = min(clip_end, end)
        source_left_end = clip.source_start + (left - clip_start)
        source_right_start = clip.source_start + (right - clip_start)
        if left > clip_start:
            out_audio.append(replace(clip, source_end=source_left_end))
        if right < clip_end:
            out_audio.append(
                replace(
                    clip,
                    source_start=source_right_start,
                    timeline_start=clip_start + (left - clip_start),
                    fade_in=0.0,
                )
            )

    out_overlays: list[Overlay] = []
    for overlay in project.overlays:
        overlay_end = overlay.end if overlay.end is not None else duration
        if overlay_end <= start:
            out_overlays.append(overlay)
            continue
        if overlay.start >= end:
            out_overlays.append(
                replace(
                    overlay,
                    start=overlay.start - removed,
                    end=None if overlay.end is None else overlay.end - removed,
                )
            )
            continue
        new_start = _map_after_cut(overlay.start, start, end)
        new_end = _map_after_cut(overlay_end, start, end)
        if new_end > new_start + 1e-6:
            out_overlays.append(
                replace(
                    overlay,
                    start=new_start,
                    end=None if overlay.end is None else new_end,
                )
            )

    out_video.sort(key=lambda clip: clip.timeline_start)
    out_audio.sort(key=lambda clip: clip.timeline_start)
    return _copy_project(project, video=out_video, audio=out_audio, overlays=out_overlays)


def merge_clips(*clips: MediaClip) -> Project:
    """Create a project containing clips back-to-back in the supplied order."""
    if not clips:
        raise ValueError("merge_clips requires at least one clip")
    timeline = 0.0
    merged: list[MediaClip] = []
    for clip in clips:
        if clip.duration is None:
            raise ValueError("merge_clips requires bounded clips")
        merged.append(replace(clip, timeline_start=timeline))
        timeline += clip.duration
    return Project(name="Merged", video=merged)


def add_filter(project: Project, filter_expression: str, clip_index: int | None = None) -> Project:
    """Attach an FFmpeg video filter without changing the source media."""
    expression = filter_expression.strip()
    if not expression:
        raise ValueError("filter_expression cannot be empty")
    clips = list(project.video)
    indices = range(len(clips)) if clip_index is None else (clip_index,)
    for index in indices:
        if index < 0 or index >= len(clips):
            raise IndexError("clip_index out of range")
        clips[index] = replace(clips[index], filters=(*clips[index].filters, expression))
    return _copy_project(project, video=clips)


def add_audio(project: Project, clip: AudioClip) -> Project:
    """Add an external audio layer to the project."""
    return _copy_project(project, audio=[*project.audio, clip])


def add_overlay(project: Project, overlay: Overlay) -> Project:
    """Add a text, image, or shape layer."""
    return _copy_project(project, overlays=[*project.overlays, overlay])
