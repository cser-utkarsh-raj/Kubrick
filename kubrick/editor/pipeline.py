from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from kubrick.core import PROFILES, SilencePolicy, TimeRange, build_keep_segments
from kubrick.media.ffmpeg import probe_duration, render_keep_segments
from kubrick.media.silencedetect import detect_silence
from kubrick.speech.editing import speech_edit_candidates
from kubrick.speech.transcribe import transcribe


@dataclass(slots=True)
class PipelineResult:
    duration: float
    silences: list[TimeRange]
    decisions: list
    speech_candidates: list


def analyze_video(path: str | Path, *, profile: str = "natural", speech: bool = False) -> PipelineResult:
    """Run the same deterministic silence analysis used by the main editor."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    path = Path(path)
    duration = probe_duration(path)
    policy = PROFILES[profile]
    silences = detect_silence(
        path,
        noise_db=-38.0,
        min_duration=policy.min_silence,
        duration=duration,
    )
    decisions = SilencePolicy(policy).decide(silences)
    candidates = speech_edit_candidates(transcribe(path)) if speech else []
    return PipelineResult(duration, silences, decisions, candidates)


def render(input_path: str | Path, output_path: str | Path, *, profile: str = "natural") -> None:
    """Analyze footage and render its retained segments."""
    result = analyze_video(input_path, profile=profile)
    segments = build_keep_segments(result.duration, result.decisions)
    render_keep_segments(input_path, output_path, segments)


def save_report(result: PipelineResult, output: str | Path) -> None:
    payload = {
        "duration": result.duration,
        "silences": [asdict(x) for x in result.silences],
        "decisions": [asdict(x) for x in result.decisions],
        "speech_candidates": [asdict(x) for x in result.speech_candidates],
    }
    Path(output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
