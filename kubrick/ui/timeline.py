from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from kubrick.core import Project
from kubrick.editor import project_duration


@dataclass(slots=True)
class _Hit:
    track: str
    index: int
    start: float
    end: float


class TimelineWidget(QWidget):
    """Compact multi-track timeline with click-to-seek and draggable layers."""

    clip_selected = Signal(str, int)
    position_selected = Signal(float)
    clip_moved = Signal(str, int, float)

    LEFT = 82
    RULER = 26
    ROW = 44
    MIN_ZOOM = 24.0
    MAX_ZOOM = 180.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.project: Project | None = None
        self.position = 0.0
        self.zoom = 70.0
        self._drag: _Hit | None = None
        self._drag_origin_x = 0.0
        self._drag_start = 0.0
        self._drag_changed = False
        self._resize_to_content()

    def _resize_to_content(self) -> None:
        duration = self._duration()
        rows = max(1, len(self._tracks()))
        width = int(self.LEFT + duration * self.zoom + 120)
        height = self.RULER + rows * self.ROW + 4
        self.setMinimumSize(width, height)
        self.resize(max(self.width(), width), height)

    def set_project(self, project: Project | None) -> None:
        self.project = project
        self._drag = None
        self._resize_to_content()
        self.update()

    def set_position(self, position: float) -> None:
        self.position = max(0.0, position)
        self.update()

    def _duration(self) -> float:
        if not self.project or not self.project.video:
            return 1.0
        try:
            return max(1.0, project_duration(self.project))
        except (TypeError, ValueError):
            return 1.0

    def _x_for_time(self, value: float) -> float:
        return self.LEFT + value * self.zoom

    def _time_for_x(self, x: float) -> float:
        return max(0.0, (x - self.LEFT) / self.zoom)

    def _tracks(self) -> list[tuple[str, int, float, float, str]]:
        if not self.project:
            return []
        tracks: list[tuple[str, int, float, float, str]] = []
        for index, clip in enumerate(self.project.video):
            end = clip.timeline_end
            if end is not None:
                tracks.append(("VIDEO", index, clip.timeline_start, end, clip.path))
        for index, clip in enumerate(self.project.audio):
            end = clip.timeline_end
            if end is not None:
                tracks.append(("AUDIO", index, clip.timeline_start, end, clip.path))
        for index, overlay in enumerate(self.project.overlays):
            end = overlay.end if overlay.end is not None else self._duration()
            tracks.append((overlay.kind.upper(), index, overlay.start, end, overlay.value))
        return tracks

    def _hit(self, x: float, y: float) -> _Hit | None:
        row = int((y - self.RULER) // self.ROW)
        tracks = self._tracks()
        if row < 0 or row >= len(tracks):
            return None
        track, index, start, end, _ = tracks[row]
        time = self._time_for_x(x)
        if start <= time <= end:
            return _Hit(track.lower(), index, start, end)
        return None

    def _seek_from_x(self, x: float) -> None:
        position = min(self._duration(), self._time_for_x(x))
        self.position = position
        self.position_selected.emit(position)
        self.update()

    def paintEvent(self, _event) -> None:  # pragma: no cover - visual rendering
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QBrush(QColor("#090909")))
        duration = self._duration()
        tracks = self._tracks()

        painter.setPen(QPen(QColor("#343434")))
        painter.drawLine(self.LEFT, 0, self.LEFT, self.height())
        painter.setFont(QFont("Segoe UI", 8))
        tick = 1.0
        if duration > 120:
            tick = 10.0
        elif duration > 60:
            tick = 5.0
        elif duration > 30:
            tick = 2.0
        value = 0.0
        while value <= duration + 0.01:
            x = self._x_for_time(value)
            painter.setPen(QPen(QColor("#252525")))
            painter.drawLine(QPointF(x, self.RULER), QPointF(x, self.height()))
            painter.setPen(QPen(QColor("#77736e")))
            painter.drawText(int(x + 3), 17, self._format_time(value))
            value += tick

        for row, (track, index, start, end, label) in enumerate(tracks):
            y = self.RULER + row * self.ROW
            painter.setPen(QPen(QColor("#222222")))
            painter.drawLine(0, y + self.ROW - 1, self.width(), y + self.ROW - 1)
            painter.setPen(QPen(QColor("#aaa59d")))
            painter.drawText(10, y + 26, track)
            left = self._x_for_time(start)
            right = max(left + 4, self._x_for_time(end))
            block = QRect(int(left), int(y + 7), int(right - left), self.ROW - 14)
            selected = self._drag and self._drag.index == index and self._drag.track == track.lower()
            painter.setBrush(QBrush(QColor("#261513" if selected else "#171717")))
            painter.setPen(QPen(QColor("#6f2d27")))
            painter.drawRoundedRect(block, 6, 6)
            painter.setPen(QPen(QColor("#d8d2ca")))
            text = label.rsplit("/", 1)[-1]
            painter.drawText(block.adjusted(9, 0, -9, 0), Qt.AlignmentFlag.AlignVCenter, text)

        playhead_x = self._x_for_time(min(duration, self.position))
        painter.setPen(QPen(QColor("#d52b1e"), 2))
        painter.drawLine(QPointF(playhead_x, 0), QPointF(playhead_x, self.height()))
        painter.setBrush(QBrush(QColor("#d52b1e")))
        painter.drawEllipse(QPointF(playhead_x, 5), 4, 4)

    def mousePressEvent(self, event) -> None:  # pragma: no cover - Qt interaction
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = event.position()
        hit = self._hit(point.x(), point.y())
        if hit:
            self.clip_selected.emit(hit.track, hit.index)
            if hit.track in {"audio", "text", "image", "shape"}:
                self._drag = hit
                self._drag_origin_x = point.x()
                self._drag_start = hit.start
                self._drag_changed = False
        else:
            self._seek_from_x(point.x())

    def mouseMoveEvent(self, event) -> None:  # pragma: no cover - Qt interaction
        if not self._drag or not self.project:
            return
        delta = (event.position().x() - self._drag_origin_x) / self.zoom
        new_start = max(0.0, self._drag_start + delta)
        max_start = self._duration() - (self._drag.end - self._drag.start)
        new_start = min(new_start, max(0.0, max_start))
        if abs(new_start - self._drag_start) > 0.01:
            self._drag_changed = True
            duration = self._drag.end - self._drag.start
            self._drag = _Hit(self._drag.track, self._drag.index, new_start, new_start + duration)
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # pragma: no cover - Qt interaction
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._drag and self._drag_changed:
            self.clip_moved.emit(self._drag.track, self._drag.index, self._drag.start)
        self._drag = None
        self._drag_changed = False
        self.update()

    def wheelEvent(self, event) -> None:  # pragma: no cover - Qt interaction
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            event.ignore()
            return
        factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        self.zoom = min(self.MAX_ZOOM, max(self.MIN_ZOOM, self.zoom * factor))
        self._resize_to_content()
        self.update()
        event.accept()

    @staticmethod
    def _format_time(value: float) -> str:
        total = max(0, int(value))
        minutes, seconds = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
