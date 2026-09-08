from __future__ import annotations

import re
import subprocess
from pathlib import Path

from kubrick.core.models import TimeRange

_START = re.compile(r"silence_start:\s*([0-9.]+)")
_END = re.compile(r"silence_end:\s*([0-9.]+)")


def detect_silence(path: str | Path, *, noise_db: float = -38.0, min_duration: float = 0.65, duration: float | None = None) -> list[TimeRange]:
    if noise_db >= 0:
        raise ValueError("noise_db must be negative")
    if min_duration <= 0:
        raise ValueError("min_duration must be positive")
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn",
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        lines = [x.strip() for x in proc.stderr.splitlines() if x.strip()]
        raise RuntimeError(lines[-1] if lines else "FFmpeg silence detection failed")
    return parse_silence_log(proc.stderr, duration=duration)


def parse_silence_log(stderr: str, *, duration: float | None = None) -> list[TimeRange]:
    open_start: float | None = None
    result: list[TimeRange] = []
    for line in stderr.splitlines():
        start = _START.search(line)
        if start:
            open_start = float(start.group(1))
            continue
        end = _END.search(line)
        if end and open_start is not None:
            finish = float(end.group(1))
            if finish >= open_start:
                result.append(TimeRange(open_start, finish))
            open_start = None
    if open_start is not None and duration is not None and duration >= open_start:
        result.append(TimeRange(open_start, duration))
    return result
