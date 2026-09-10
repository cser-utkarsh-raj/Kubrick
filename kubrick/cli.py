from __future__ import annotations

import argparse
import json
from pathlib import Path

from kubrick.core import PRESETS, Project
from kubrick.editor import AnalyzerConfig, analyze, build_preset_project, render
from kubrick.media import render_project


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kubrick",
        description="Precision-first local video editing engine",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_parser = sub.add_parser("analyze", help="Analyze footage and produce an edit report")
    analyze_parser.add_argument("input", type=Path)
    analyze_parser.add_argument("--profile", choices=("gentle", "natural", "tight"), default="natural")
    analyze_parser.add_argument("--noise-db", type=float, default=-38.0)
    analyze_parser.add_argument("--visual", action="store_true", help="also run visual review analysis")
    analyze_parser.add_argument("--json", dest="json_path", type=Path)

    render_parser = sub.add_parser("render", help="Automatically tighten footage and render an MP4")
    render_parser.add_argument("input", type=Path)
    render_parser.add_argument("output", type=Path)
    render_parser.add_argument("--profile", choices=("gentle", "natural", "tight"), default="natural")
    render_parser.add_argument("--noise-db", type=float, default=-38.0)

    project_parser = sub.add_parser("new-project", help="Create an editable project JSON from source footage")
    project_parser.add_argument("input", type=Path)
    project_parser.add_argument("output", type=Path)
    project_parser.add_argument("--preset", choices=tuple(PRESETS), default="clean")

    validate_parser = sub.add_parser("validate-project", help="Validate an editable project before rendering")
    validate_parser.add_argument("project", type=Path)

    render_project_parser = sub.add_parser("render-project", help="Render an editable project JSON")
    render_project_parser.add_argument("project", type=Path)
    render_project_parser.add_argument("output", type=Path)
    render_project_parser.add_argument("--crf", type=int, default=18)
    render_project_parser.add_argument("--encoder-preset", default="medium")

    return parser


def _report_json(report) -> dict:
    return {
        "duration": report.duration,
        "silences": [{"start": s.start, "end": s.end} for s in report.silences],
        "decisions": [
            {
                "start": d.source.start,
                "end": d.source.end,
                "kind": d.kind.value,
                "confidence": d.confidence,
                "reason": d.reason,
                "target_duration": d.target_duration,
            }
            for d in report.decisions
        ],
        "removed_duration": report.removed_duration,
        "output_duration": report.output_duration,
        "metadata": report.metadata,
    }


def main() -> int:
    args = _build_parser().parse_args()

    if args.command == "analyze":
        config = AnalyzerConfig(args.profile, args.noise_db, visual=args.visual)
        report = analyze(args.input, config)
        text = json.dumps(_report_json(report), indent=2)
        if args.json_path:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            args.json_path.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    if args.command == "render":
        render(args.input, args.output, AnalyzerConfig(args.profile, args.noise_db))
        print(f"Rendered: {args.output}")
        return 0

    if args.command == "new-project":
        project = build_preset_project(args.input, args.preset)
        project.save(args.output)
        print(f"Project: {args.output}")
        return 0

    project = Project.load(args.project)
    if args.command == "validate-project":
        project.validate()
        print(f"Valid project: {args.project}")
        print(f"Timeline duration: {project.duration():.3f}s")
        print(f"Video clips: {len(project.video)} | Audio clips: {len(project.audio)} | Overlays: {len(project.overlays)}")
        return 0

    render_project(project, args.output, crf=args.crf, preset=args.encoder_preset)
    print(f"Rendered: {args.output}")
    return 0
