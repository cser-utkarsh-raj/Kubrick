from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EditPreset:
    name: str
    description: str
    profile: str
    noise_db: float
    scene_threshold: float
    video_filters: tuple[str, ...] = ()
    audio_gain_db: float = 0.0
    audio_fade_in: float = 0.0
    audio_fade_out: float = 0.0


PRESETS: dict[str, EditPreset] = {
    "clean": EditPreset(
        "clean", "Natural cleanup for tutorials and talking-head footage.", "natural", -38, 0.35
    ),
    "tight": EditPreset(
        "tight", "Faster pacing with stronger silence removal.", "tight", -38, 0.35
    ),
    "gentle": EditPreset(
        "gentle", "Minimal intervention that preserves pauses and rhythm.", "gentle", -40, 0.35
    ),
    "punchy": EditPreset(
        "punchy", "Crisp creator look with a restrained contrast boost.", "natural", -38, 0.30,
        ("eq=contrast=1.04:brightness=0.01:saturation=1.04",),
    ),
    "mono-voice": EditPreset(
        "mono-voice", "Speech-forward preset with mild voice presence EQ.", "natural", -38, 0.35,
        (), 1.5,
    ),
}


def get_preset(name: str) -> EditPreset:
    try:
        return PRESETS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown preset: {name}. Choose from {', '.join(PRESETS)}") from exc
