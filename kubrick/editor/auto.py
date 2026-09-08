from __future__ import annotations

from pathlib import Path

from kubrick.core import MediaClip, Project, build_keep_segments, get_preset
from .analyzer import AnalyzerConfig, analyze


def build_auto_project(input_path: str | Path, config: AnalyzerConfig = AnalyzerConfig()) -> Project:
    """Analyze footage and turn the approved automatic decisions into a project."""
    source = Path(input_path)
    report = analyze(source, config)
    segments = build_keep_segments(report.duration, report.decisions)
    clips = [
        MediaClip(
            path=str(source),
            source_start=segment.source.start,
            source_end=segment.source.end,
            timeline_start=sum(item.duration or 0 for item in clips),
        )
        for segment in segments
    ]
    return Project(name=f"Kubrick — {source.stem}", video=clips, preset=config.profile)


def build_preset_project(input_path: str | Path, preset_name: str = "clean") -> Project:
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
    return project
