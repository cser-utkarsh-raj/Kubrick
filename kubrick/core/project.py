from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class MediaClip:
    """A source media interval placed on the main timeline."""

    path: str
    source_start: float = 0.0
    source_end: float | None = None
    timeline_start: float = 0.0
    volume: float = 1.0
    speed: float = 1.0
    filters: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.source_start < 0 or self.timeline_start < 0:
            raise ValueError("clip times must be non-negative")
        if self.source_end is not None and self.source_end <= self.source_start:
            raise ValueError("source_end must be greater than source_start")
        if self.speed <= 0:
            raise ValueError("speed must be positive")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")

    @property
    def duration(self) -> float | None:
        if self.source_end is None:
            return None
        return (self.source_end - self.source_start) / self.speed


@dataclass(frozen=True, slots=True)
class AudioClip:
    path: str
    source_start: float = 0.0
    source_end: float | None = None
    timeline_start: float = 0.0
    volume: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0

    def __post_init__(self) -> None:
        if self.source_start < 0 or self.timeline_start < 0:
            raise ValueError("audio times must be non-negative")
        if self.source_end is not None and self.source_end <= self.source_start:
            raise ValueError("source_end must be greater than source_start")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")
        if self.fade_in < 0 or self.fade_out < 0:
            raise ValueError("audio fades cannot be negative")


@dataclass(frozen=True, slots=True)
class Overlay:
    """A visual layer rendered above the main video."""

    kind: str
    value: str
    start: float = 0.0
    end: float | None = None
    x: str = "(W-w)/2"
    y: str = "(H-h)/2"
    width: int | None = None
    height: int | None = None
    font_size: int = 48
    color: str = "white"
    opacity: float = 1.0
    border_radius: int = 0

    def __post_init__(self) -> None:
        if self.kind not in {"text", "image", "shape"}:
            raise ValueError("overlay kind must be text, image, or shape")
        if self.start < 0 or (self.end is not None and self.end <= self.start):
            raise ValueError("invalid overlay timing")
        if not 0 <= self.opacity <= 1:
            raise ValueError("opacity must be between 0 and 1")
        if self.kind == "shape" and not self.value:
            raise ValueError("shape value must contain a color")


@dataclass(slots=True)
class Project:
    """Small, serializable editing model used by the local renderer."""

    name: str = "Untitled"
    video: list[MediaClip] = field(default_factory=list)
    audio: list[AudioClip] = field(default_factory=list)
    overlays: list[Overlay] = field(default_factory=list)
    width: int | None = None
    height: int | None = None
    fps: int | None = None
    preset: str = "clean"

    def validate(self) -> None:
        if not self.video:
            raise ValueError("project needs at least one video clip")
        for clip in [*self.video, *self.audio]:
            if not Path(clip.path).is_file():
                raise FileNotFoundError(clip.path)
        if self.width is not None and self.width <= 0:
            raise ValueError("width must be positive")
        if self.height is not None and self.height <= 0:
            raise ValueError("height must be positive")
        if self.fps is not None and self.fps <= 0:
            raise ValueError("fps must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Project:
        return cls(
            name=str(data.get("name", "Untitled")),
            video=[MediaClip(**{**item, "filters": tuple(item.get("filters", ()))}) for item in data.get("video", [])],
            audio=[AudioClip(**item) for item in data.get("audio", [])],
            overlays=[Overlay(**item) for item in data.get("overlays", [])],
            width=data.get("width"),
            height=data.get("height"),
            fps=data.get("fps"),
            preset=str(data.get("preset", "clean")),
        )

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> Project:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
