from __future__ import annotations

from pathlib import Path

from kubrick.core import MediaClip, Project, build_keep_segments, get_preset
from .analyzer import AnalyzerConfig, analyze


def build_auto_project(input_path: str | Path, config: AnalyzerConfig = AnalyzerConfig()) -> Project:
    """Analyze footage and turn automatic timeline decisions into a project."""
    source = Path(input_path)
    report = analyze(source, config)
    segments = build_keep_segments(report.duration, report.decisions)
    clips: list[MediaClip] = []
    timeline = 0.0
    for segment in segments:
        clip = MediaClip(
            path=str(source),
            source_start=segment.source.start,
            source_end=segment.source.end,
            timeline_start=timeline,
        )
        clips.append(clip)
        timeline += clip.duration or 0.0
    return Project(name=f"Kubrick — {source.stem}", video=clips, preset=config.profile)


def build_preset_project(input_path: str | Path, preset_name: str = "clean") -> Project:
    """Build an automatic edit using one of Kubrick's named presets."""
    preset = get_preset(preset_name)
    project = build_auto_project(
        input_path,
        AnalyzerConfig(
            profile=preset.profile,
            noise_db=preset.noise_db,
            scene_threshold=preset.scene_threshold,
        ),
    )
    if preset.video_filters:
        project.video = [
            MediaClip(
                path=clip.path,
                source_start=clip.source_start,
                source_end=clip.source_end,
                timeline_start=clip.timeline_start,
                volume=clip.volume,
                speed=clip.speed,
                filters=preset.video_filters,
            )
            for clip in project.video
        ]
    project.preset = preset.name
    return project
