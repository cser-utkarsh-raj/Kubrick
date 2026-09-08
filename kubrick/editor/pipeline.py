from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path

from kubrick.core import PROFILES, SilencePolicy, TimeRange, build_keep_segments
from kubrick.media.ffmpeg import probe_duration, render_keep_segments
from kubrick.speech.editing import speech_edit_candidates
from kubrick.speech.transcribe import transcribe

@dataclass(slots=True)
class PipelineResult:
    duration: float
    silences: list[TimeRange]
    decisions: list
    speech_candidates: list


def analyze_video(path: str | Path, *, profile: str = "natural", speech: bool = False) -> PipelineResult:
    path = Path(path)
    duration = probe_duration(path)
    # Silence detection is delegated to the media layer/CLI in the current foundation.
    # Keeping orchestration separate makes the desktop UI and future API deterministic.
    silences: list[TimeRange] = []
    decisions = SilencePolicy(PROFILES[profile]).decide(silences)
    candidates = speech_edit_candidates(transcribe(path)) if speech else []
    return PipelineResult(duration, silences, decisions, candidates)


def save_report(result: PipelineResult, output: str | Path) -> None:
    payload = {
        "duration": result.duration,
        "silences": [asdict(x) for x in result.silences],
        "decisions": [asdict(x) for x in result.decisions],
        "speech_candidates": [asdict(x) for x in result.speech_candidates],
    }
    Path(output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
