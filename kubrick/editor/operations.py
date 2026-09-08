from __future__ import annotations

from dataclasses import replace

from kubrick.core.project import MediaClip, Project


def trim_clip(clip: MediaClip, start: float, end: float) -> MediaClip:
    """Return a non-destructive trim of a source clip."""
    if start < clip.source_start or end <= start:
        raise ValueError("trim range must be inside the clip and have positive duration")
    if clip.source_end is not None and end > clip.source_end:
        raise ValueError("trim end exceeds the clip source range")
    return replace(clip, source_start=start, source_end=end)


def cut_range(project: Project, start: float, end: float) -> Project:
    """Remove a timeline interval while preserving the remaining clip media."""
    if end <= start or start < 0:
        raise ValueError("cut range must be positive")
    out: list[MediaClip] = []
    for clip in project.video:
        duration = clip.duration
        if duration is None:
            raise ValueError("cut_range requires bounded video clips")
        clip_start, clip_end = clip.timeline_start, clip.timeline_start + duration
        if end <= clip_start or start >= clip_end:
            out.append(clip)
            continue
        left = max(clip_start, start)
        right = min(clip_end, end)
        source_left_end = clip.source_start + (left - clip_start) * clip.speed
        source_right_start = clip.source_start + (right - clip_start) * clip.speed
        if left > clip_start:
            out.append(replace(clip, source_end=source_left_end))
        if right < clip_end:
            shift = end - start if right == clip_end else right - left
            new_start = clip.timeline_start + (right - clip_start) - (end - start if right == clip_end else 0)
            out.append(replace(clip, source_start=source_right_start, timeline_start=max(0.0, new_start)))
    out.sort(key=lambda c: c.timeline_start)
    return Project(project.name, out, list(project.audio), list(project.overlays), project.width, project.height, project.fps, project.preset)


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
    return Project(project.name, clips, list(project.audio), list(project.overlays), project.width, project.height, project.fps, project.preset)
