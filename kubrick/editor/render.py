from __future__ import annotations

from pathlib import Path

from kubrick.core import build_keep_segments
from kubrick.media import render_keep_segments
from .analyzer import AnalyzerConfig, analyze


def render(input_path: str | Path, output_path: str | Path, config: AnalyzerConfig = AnalyzerConfig()) -> None:
    report = analyze(input_path, config)
    segments = build_keep_segments(report.duration, report.decisions)
    render_keep_segments(input_path, output_path, segments)
