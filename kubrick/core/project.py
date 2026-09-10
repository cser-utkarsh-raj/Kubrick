from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


PROJECT_SCHEMA_VERSION = 1


def _finite(value: float, label: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")


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
        _finite(self.source_start, "source_start")
        _finite(self.timeline_start, "timeline_start")
        _finite(self.volume, "volume")
        _finite(self.speed, "speed")
        if self.source_start < 0 or self.timeline_start < 0:
            raise ValueError("clip times must be non-negative")
        if self.source_end is not None:
            _finite(self.source_end, "source_end")
            if self.source_end <= self.source_start:
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

    @property
    def timeline_end(self) -> float | None:
        duration = self.duration
        return None if duration is None else self.timeline_start + duration


@dataclass(frozen=True, slots=True)
class AudioClip:
    """An external audio interval placed on the shared project timeline."""

    path: str
    source_start: float = 0.0
    source_end: float | None = None
    timeline_start: float = 0.0
    volume: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0

    def __post_init__(self) -> None:
        _finite(self.source_start, "source_start")
        _finite(self.timeline_start, "timeline_start")
        _finite(self.volume, "volume")
        _finite(self.fade_in, "fade_in")
        _finite(self.fade_out, "fade_out")
        if self.source_start < 0 or self.timeline_start < 0:
            raise ValueError("audio times must be non-negative")
        if self.source_end is not None:
            _finite(self.source_end, "source_end")
            if self.source_end <= self.source_start:
                raise ValueError("source_end must be greater than source_start")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")
        if self.fade_in < 0 or self.fade_out < 0:
            raise ValueError("audio fades cannot be negative")

    @property
    def duration(self) -> float | None:
        if self.source_end is None:
            return None
        return self.source_end - self.source_start

    @property
    def timeline_end(self) -> float | None:
        return None if self.duration is None else self.timeline_start + self.duration


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
        _finite(self.start, "overlay start")
        if self.end is not None:
            _finite(self.end, "overlay end")
        _finite(self.opacity, "overlay opacity")
        if self.start < 0 or (self.end is not None and self.end <= self.start):
            raise ValueError("invalid overlay timing")
        if not 0 <= self.opacity <= 1:
            raise ValueError("opacity must be between 0 and 1")
        if self.width is not None and self.width <= 0:
            raise ValueError("overlay width must be positive")
        if self.height is not None and self.height <= 0:
            raise ValueError("overlay height must be positive")
        if self.font_size <= 0:
            raise ValueError("font_size must be positive")
        if self.border_radius < 0:
            raise ValueError("border_radius cannot be negative")
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
    schema_version: int = PROJECT_SCHEMA_VERSION

    def duration(self) -> float:
        """Return the end of the main video timeline."""
        ends = [clip.timeline_end for clip in self.video]
        finite_ends = [end for end in ends if end is not None]
        if not finite_ends:
            raise ValueError("project duration is unknown because a video clip has no source_end")
        return max(finite_ends)

    def validate(self) -> None:
        if not self.video:
            raise ValueError("project needs at least one video clip")
        if self.schema_version > PROJECT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported project schema version {self.schema_version}; "
                f"maximum supported is {PROJECT_SCHEMA_VERSION}"
            )
        if self.schema_version < 1:
            raise ValueError("invalid project schema version")
        for clip in [*self.video, *self.audio]:
            if not Path(clip.path).is_file():
                raise FileNotFoundError(clip.path)
        for overlay in self.overlays:
            if overlay.kind == "image" and not Path(overlay.value).is_file():
                raise FileNotFoundError(overlay.value)
        if self.width is not None and self.width <= 0:
            raise ValueError("width must be positive")
        if self.height is not None and self.height <= 0:
            raise ValueError("height must be positive")
        if self.fps is not None and self.fps <= 0:
            raise ValueError("fps must be positive")

        expected_start = 0.0
        for index, clip in enumerate(self.video):
            if abs(clip.timeline_start - expected_start) > 1e-6:
                raise ValueError("main video clips must form a continuous timeline starting at 0")
            end = clip.timeline_end
            if end is None:
                if index != len(self.video) - 1:
                    raise ValueError("only the final video clip may have unknown duration")
                break
            expected_start = end

        duration = expected_start
        for overlay in self.overlays:
            if overlay.end is not None and overlay.end > duration + 1e-6:
                raise ValueError("overlay extends beyond project duration")
        for clip in self.audio:
            end = clip.timeline_end
            if end is not None and end > duration + 1e-6:
                raise ValueError("audio clip extends beyond project duration")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def _save_dict(self, base: Path) -> dict[str, Any]:
        """Serialize media references relative to the project file directory."""
        payload = self.to_dict()

        def relative(value: str) -> str:
            path = Path(value).expanduser()
            if not path.is_absolute():
                return value
            try:
                return os.path.relpath(path, base)
            except ValueError:
                # Windows can have unrelated drive letters; keep an absolute path.
                return str(path)

        for clip in payload["video"]:
            clip["path"] = relative(clip["path"])
        for clip in payload["audio"]:
            clip["path"] = relative(clip["path"])
        for overlay in payload["overlays"]:
            if overlay["kind"] == "image":
                overlay["value"] = relative(overlay["value"])
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Project:
        if not isinstance(data, dict):
            raise ValueError("project JSON must contain an object")
        schema_version = int(data.get("schema_version", 1))
        if schema_version > PROJECT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported project schema version {schema_version}; "
                f"maximum supported is {PROJECT_SCHEMA_VERSION}"
            )
        return cls(
            name=str(data.get("name", "Untitled")),
            video=[
                MediaClip(
                    **{**item, "filters": tuple(item.get("filters", ()))},
                )
                for item in data.get("video", [])
            ],
            audio=[AudioClip(**item) for item in data.get("audio", [])],
            overlays=[Overlay(**item) for item in data.get("overlays", [])],
            width=data.get("width"),
            height=data.get("height"),
            fps=data.get("fps"),
            preset=str(data.get("preset", "clean")),
            schema_version=schema_version,
        )

    def save(self, path: str | Path) -> None:
        """Atomically save the project with portable media references."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._save_dict(destination.parent), indent=2) + "\n"
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{destination.stem}.",
            suffix=".tmp",
            dir=destination.parent,
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, destination)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise

    @classmethod
    def load(cls, path: str | Path) -> Project:
        """Load a project and resolve relative media paths beside the project file."""
        project_path = Path(path).resolve()
        project = cls.from_dict(json.loads(project_path.read_text(encoding="utf-8")))
        base = project_path.parent

        def resolve(value: str) -> str:
            candidate = Path(value).expanduser()
            if candidate.is_absolute():
                return str(candidate)
            return str((base / candidate).resolve())

        project.video = [
            MediaClip(
                path=resolve(clip.path),
                source_start=clip.source_start,
                source_end=clip.source_end,
                timeline_start=clip.timeline_start,
                volume=clip.volume,
                speed=clip.speed,
                filters=clip.filters,
            )
            for clip in project.video
        ]
        project.audio = [
            AudioClip(
                path=resolve(clip.path),
                source_start=clip.source_start,
                source_end=clip.source_end,
                timeline_start=clip.timeline_start,
                volume=clip.volume,
                fade_in=clip.fade_in,
                fade_out=clip.fade_out,
            )
            for clip in project.audio
        ]
        project.overlays = [
            Overlay(
                kind=overlay.kind,
                value=resolve(overlay.value) if overlay.kind == "image" else overlay.value,
                start=overlay.start,
                end=overlay.end,
                x=overlay.x,
                y=overlay.y,
                width=overlay.width,
                height=overlay.height,
                font_size=overlay.font_size,
                color=overlay.color,
                opacity=overlay.opacity,
                border_radius=overlay.border_radius,
            )
            for overlay in project.overlays
        ]
        return project
