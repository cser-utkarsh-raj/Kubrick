from __future__ import annotations

import copy
import sys
from pathlib import Path

try:
    from PySide6.QtCore import QObject, QThread, Qt, QUrl, Signal
    from PySide6.QtGui import QIcon
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSlider,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Install the GUI extra with: python -m pip install -e '.[gui]'") from exc

from kubrick.core import AudioClip, MediaClip, Overlay, Project, get_preset
from kubrick.editor import (
    add_audio,
    add_filter,
    add_overlay,
    build_preset_project,
    cut_range,
    project_duration,
    trim_clip,
)
from kubrick.media import probe_duration, render_project

APP_DIR = Path(__file__).resolve().parent
MARK = APP_DIR / "kubrick-mark.svg"
DOT_MARK = APP_DIR / "dot.svg"

STYLESHEET = """
* { font-family: Inter, Segoe UI, Arial, sans-serif; }
QMainWindow, QWidget { background:#080808; color:#eee9e2; }
QFrame#sidebar { background:#0d0d0d; border-right:1px solid #242424; }
QFrame#topbar, QFrame#panel, QFrame#timeline { background:#0e0e0e; border:1px solid #252525; border-radius:12px; }
QLabel#brand { color:#f1eee8; font-size:17px; font-weight:800; letter-spacing:4px; }
QLabel#eyebrow { color:#77736e; font-size:9px; font-weight:800; letter-spacing:2.5px; }
QLabel#title { color:#f5f1ea; font-size:20px; font-weight:700; }
QLabel#muted { color:#77736e; font-size:11px; }
QLabel#value { color:#e9e4dd; font-size:12px; font-weight:600; }
QLineEdit, QComboBox { background:#0a0a0a; color:#eee9e2; border:1px solid #303030; border-radius:7px; padding:7px 9px; }
QLineEdit:focus, QComboBox:focus { border:1px solid #d52b1e; }
QPushButton { background:#171717; color:#eee9e2; border:1px solid #343434; border-radius:7px; padding:8px 12px; font-weight:600; }
QPushButton:hover { background:#222; border-color:#4b4b4b; }
QPushButton#primary { background:#c9281d; border-color:#e04438; color:white; }
QPushButton#primary:hover { background:#dc3024; }
QPushButton#danger:hover { background:#351513; border-color:#7b3029; }
QPushButton#nav { text-align:left; background:transparent; border:0; color:#85817b; padding:10px 12px; }
QPushButton#nav:hover, QPushButton#navActive { background:#251311; color:#f4efe8; border-left:2px solid #d52b1e; }
QVideoWidget { background:#050505; border:1px solid #282828; border-radius:10px; }
QSlider::groove:horizontal { height:4px; background:#292929; }
QSlider::handle:horizontal { width:12px; margin:-4px 0; border-radius:6px; background:#d52b1e; }
QTableWidget { background:#0a0a0a; border:1px solid #252525; border-radius:9px; gridline-color:#1e1e1e; }
QHeaderView::section { background:#121212; color:#77736e; border:0; border-bottom:1px solid #282828; padding:7px; font-size:9px; }
QTableWidget::item { padding:6px; color:#d4cfc8; }
QTableWidget::item:selected { background:#2b1513; color:white; }
QStatusBar { background:#0d0d0d; color:#77736e; border-top:1px solid #222; }
"""


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self) -> None:
        try:
            self.finished.emit(self.fn())
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kubrick — Precision Video Editor")
        self.setMinimumSize(1180, 760)
        self.resize(1440, 900)
        self.setStyleSheet(STYLESHEET)
        if MARK.exists():
            self.setWindowIcon(QIcon(str(MARK)))
        self.project: Project | None = None
        self.source: Path | None = None
        self.selected_track: str | None = None
        self.selected_index: int | None = None
        self.history: list[Project] = []
        self.future: list[Project] = []
        self._thread: QThread | None = None
        self._worker: Worker | None = None
        self._building = False
        self._build()
        self._reset_project()

    def _build(self) -> None:
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._sidebar())
        root.addWidget(self._workspace(), 1)
        shell = QWidget()
        shell.setLayout(root)
        self.setCentralWidget(shell)
        self.statusBar().showMessage("Ready")

    def _sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(190)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(4)
        row = QHBoxLayout()
        if MARK.exists():
            mark = QLabel()
            mark.setPixmap(QIcon(str(MARK)).pixmap(28, 28))
            row.addWidget(mark)
        brand = QLabel("KUBRICK")
        brand.setObjectName("brand")
        row.addWidget(brand)
        row.addStretch()
        layout.addLayout(row)
        sub = QLabel("PRECISION EDITOR")
        sub.setObjectName("eyebrow")
        sub.setContentsMargins(4, 7, 4, 20)
        layout.addWidget(sub)
        for label, active in [
            ("⌂  Project", True),
            ("✂  Edit", False),
            ("✦  Auto Edit", False),
            ("▦  Scenes", False),
            ("≡  Transcript", False),
            ("◫  Audio", False),
        ]:
            button = QPushButton(label)
            button.setObjectName("navActive" if active else "nav")
            layout.addWidget(button)
        layout.addStretch(1)
        dot = QLabel()
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if DOT_MARK.exists():
            dot.setPixmap(QIcon(str(DOT_MARK)).pixmap(54, 54))
        layout.addWidget(dot)
        dot_text = QLabel(".dot / KUBRICK")
        dot_text.setObjectName("muted")
        dot_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dot_text)
        return side

    def _workspace(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(10)
        outer.addWidget(self._topbar())
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self._editor_area())
        split.addWidget(self._timeline_panel())
        split.setSizes([610, 250])
        outer.addWidget(split, 1)
        return page

    def _topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("topbar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 8, 12, 8)
        title = QLabel("UNTITLED")
        title.setObjectName("title")
        self.project_title = title
        row.addWidget(title)
        row.addSpacing(12)
        self.status = QLabel("Ready")
        self.status.setObjectName("muted")
        row.addWidget(self.status)
        row.addStretch()
        for text, slot in [
            ("New", self._reset_project),
            ("Open", self._open_project),
            ("Save", self._save_project),
            ("Import", self._import_video),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        undo = QPushButton("Undo")
        undo.clicked.connect(self._undo)
        row.addWidget(undo)
        redo = QPushButton("Redo")
        redo.clicked.connect(self._redo)
        row.addWidget(redo)
        self.auto = QPushButton("Auto Edit")
        self.auto.setObjectName("primary")
        self.auto.clicked.connect(self._auto_edit)
        row.addWidget(self.auto)
        self.render = QPushButton("Render")
        self.render.setObjectName("primary")
        self.render.clicked.connect(self._render)
        row.addWidget(self.render)
        return bar

    def _editor_area(self) -> QWidget:
        split = QSplitter(Qt.Orientation.Horizontal)
        center = QFrame()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.video = QVideoWidget()
        layout.addWidget(self.video, 1)
        controls = QFrame()
        control_row = QHBoxLayout(controls)
        control_row.setContentsMargins(8, 5, 8, 5)
        self.play = QPushButton("▶")
        self.play.setFixedWidth(38)
        self.play.clicked.connect(self._toggle_play)
        control_row.addWidget(self.play)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.sliderMoved.connect(self._seek)
        control_row.addWidget(self.seek, 1)
        self.time = QLabel("00:00 / 00:00")
        self.time.setObjectName("muted")
        control_row.addWidget(self.time)
        layout.addWidget(controls)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video)
        self.player.positionChanged.connect(self._position_changed)
        self.player.durationChanged.connect(self._duration_changed)
        self.audio_output.setVolume(0.8)
        split.addWidget(center)
        split.addWidget(self._inspector())
        split.setSizes([900, 310])
        return split

    def _inspector(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        eyebrow = QLabel("INSPECTOR")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)
        self.clip_info = QLabel("No clip selected")
        self.clip_info.setObjectName("value")
        self.clip_info.setWordWrap(True)
        layout.addWidget(self.clip_info)

        label = QLabel("CLIP RANGE")
        label.setObjectName("eyebrow")
        layout.addWidget(label)
        range_row = QHBoxLayout()
        self.trim_start = QLineEdit()
        self.trim_start.setPlaceholderText("start")
        self.trim_end = QLineEdit()
        self.trim_end.setPlaceholderText("end")
        range_row.addWidget(self.trim_start)
        range_row.addWidget(self.trim_end)
        layout.addLayout(range_row)
        trim = QPushButton("Apply trim")
        trim.clicked.connect(self._apply_trim)
        layout.addWidget(trim)

        label = QLabel("SPEED / VOLUME")
        label.setObjectName("eyebrow")
        layout.addWidget(label)
        media_row = QHBoxLayout()
        self.speed = QLineEdit("1.0")
        self.speed.setPlaceholderText("speed")
        self.volume = QLineEdit("1.0")
        self.volume.setPlaceholderText("volume")
        media_row.addWidget(self.speed)
        media_row.addWidget(self.volume)
        layout.addLayout(media_row)
        apply_media = QPushButton("Apply clip settings")
        apply_media.clicked.connect(self._apply_media_settings)
        layout.addWidget(apply_media)

        label = QLabel("AUTO PRESET")
        label.setObjectName("eyebrow")
        layout.addWidget(label)
        self.preset = QComboBox()
        self.preset.addItems(["clean", "gentle", "tight", "punchy", "mono-voice"])
        layout.addWidget(self.preset)

        label = QLabel("LAYERS")
        label.setObjectName("eyebrow")
        layout.addWidget(label)
        for text, slot in [
            ("+ Text", self._add_text),
            ("+ Image", self._add_image),
            ("+ Shape", self._add_shape),
            ("+ Audio", self._add_audio),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            layout.addWidget(button)

        label = QLabel("FILTER")
        label.setObjectName("eyebrow")
        layout.addWidget(label)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("eq=contrast=1.04:saturation=1.03")
        layout.addWidget(self.filter)
        filter_button = QPushButton("Apply to selected clip")
        filter_button.clicked.connect(self._apply_filter)
        layout.addWidget(filter_button)

        remove = QPushButton("Remove selected layer / clip")
        remove.setObjectName("danger")
        remove.clicked.connect(self._remove_selected)
        layout.addWidget(remove)
        layout.addStretch(1)
        self.review = QLabel(
            "Automatic decisions become normal editable clips. Nothing is rendered until you press Render."
        )
        self.review.setObjectName("muted")
        self.review.setWordWrap(True)
        layout.addWidget(self.review)
        return panel

    def _timeline_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("timeline")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        head = QHBoxLayout()
        eyebrow = QLabel("TIMELINE")
        eyebrow.setObjectName("eyebrow")
        head.addWidget(eyebrow)
        head.addStretch()
        self.cut_start = QLineEdit("0")
        self.cut_start.setMaximumWidth(80)
        self.cut_end = QLineEdit("0")
        self.cut_end.setMaximumWidth(80)
        cut = QPushButton("Cut range")
        cut.clicked.connect(self._cut_range)
        head.addWidget(QLabel("start"))
        head.addWidget(self.cut_start)
        head.addWidget(QLabel("end"))
        head.addWidget(self.cut_end)
        head.addWidget(cut)
        layout.addLayout(head)
        self.timeline = QTableWidget(0, 5)
        self.timeline.setHorizontalHeaderLabels(["TRACK", "SOURCE", "START", "END", "DURATION"])
        self.timeline.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.timeline.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.timeline.cellClicked.connect(self._timeline_selected)
        self.timeline.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.timeline, 1)
        return panel

    def _reset_project(self) -> None:
        self.project = Project(name="Untitled")
        self.source = None
        self.selected_track = None
        self.selected_index = None
        self.history.clear()
        self.future.clear()
        self.player.stop()
        self.player.setSource(QUrl())
        self.project_title.setText("UNTITLED")
        self.status.setText("Ready")
        self._refresh()

    def _import_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import video",
            "",
            "Video files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v);;All files (*)",
        )
        if path:
            self._load_source(Path(path))

    def _load_source(self, source: Path) -> None:
        try:
            duration = probe_duration(source)
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", f"Could not inspect media:\n{exc}")
            return
        self.project = Project(
            name=source.stem,
            video=[MediaClip(str(source), 0, duration, 0)],
        )
        self.source = source
        self.history.clear()
        self.future.clear()
        self.project_title.setText(source.stem.upper())
        self.player.setSource(QUrl.fromLocalFile(str(source)))
        self.status.setText(f"Imported · {duration:.1f}s")
        self._refresh()

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Kubrick project",
            "",
            "Kubrick projects (*.kubrick.json);;JSON (*.json)",
        )
        if not path:
            return
        try:
            project = Project.load(path)
            self._set_project(project, push_history=False)
            self.status.setText(f"Loaded · {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _save_project(self) -> None:
        if not self.project or not self.project.video:
            QMessageBox.warning(self, "Kubrick", "Import footage first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save project",
            f"{self.project.name}.kubrick.json",
            "Kubrick project (*.kubrick.json)",
        )
        if not path:
            return
        try:
            self.project.save(path)
            self.status.setText(f"Saved · {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _set_project(self, project: Project, *, push_history: bool = True) -> None:
        if push_history and self.project is not None:
            self.history.append(copy.deepcopy(self.project))
            self.future.clear()
        self.project = project
        self.project_title.setText(project.name.upper())
        self.source = Path(project.video[0].path) if project.video else None
        if self.source and self.source.exists():
            self.player.setSource(QUrl.fromLocalFile(str(self.source)))
        self._refresh()

    def _snapshot_and(self, mutation, message: str) -> None:
        if not self.project:
            return
        try:
            updated = mutation(self.project)
            self._set_project(updated)
            self.status.setText(message)
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _auto_edit(self) -> None:
        if self._building:
            return
        if not self.source or not self.source.exists():
            QMessageBox.warning(self, "Kubrick", "Import a video first.")
            return
        preset_name = self.preset.currentText()
        self._building = True
        self.auto.setEnabled(False)
        self.render.setEnabled(False)
        self.status.setText(f"Analyzing with {preset_name}…")
        self._run_worker(
            lambda: build_preset_project(self.source, preset_name),
            self._auto_done,
        )

    def _auto_done(self, project: Project) -> None:
        self._building = False
        self.auto.setEnabled(True)
        self.render.setEnabled(True)
        self._set_project(project)
        self.review.setText(
            f"Auto edit produced {len(project.video)} main-video segments. Review them, then render."
        )
        self.status.setText(f"Auto edit ready · {len(project.video)} segments")

    def _timeline_selected(self, row: int, _column: int) -> None:
        track = self.timeline.item(row, 0)
        if not track:
            return
        self.selected_track = track.text().lower()
        index_item = self.timeline.item(row, 0)
        index = index_item.data(Qt.ItemDataRole.UserRole)
        self.selected_index = int(index) if index is not None else None
        self._update_inspector()

        if self.selected_track == "video" and self.project and self.selected_index is not None:
            if 0 <= self.selected_index < len(self.project.video):
                clip = self.project.video[self.selected_index]
                self.player.setSource(QUrl.fromLocalFile(str(clip.path)))
                self.player.setPosition(int(clip.source_start * 1000))

    def _update_inspector(self) -> None:
        if not self.project or self.selected_index is None or self.selected_track != "video":
            self.clip_info.setText("No video clip selected")
            return
        if self.selected_index >= len(self.project.video):
            return
        clip = self.project.video[self.selected_index]
        self.clip_info.setText(Path(clip.path).name)
        self.trim_start.setText(f"{clip.source_start:.3f}")
        self.trim_end.setText(f"{(clip.source_end or 0):.3f}")
        self.speed.setText(f"{clip.speed:.3f}")
        self.volume.setText(f"{clip.volume:.3f}")

    def _apply_trim(self) -> None:
        if not self.project or self.selected_track != "video" or self.selected_index is None:
            QMessageBox.information(self, "Kubrick", "Select a video clip first.")
            return
        try:
            start = float(self.trim_start.text())
            end = float(self.trim_end.text())
            index = self.selected_index
            clips = list(self.project.video)
            clips[index] = trim_clip(clips[index], start, end)
            timeline = 0.0
            for i, clip in enumerate(clips):
                clips[i] = MediaClip(
                    clip.path,
                    clip.source_start,
                    clip.source_end,
                    timeline,
                    clip.volume,
                    clip.speed,
                    clip.filters,
                )
                timeline += clips[i].duration or 0.0
            updated = Project(
                self.project.name,
                clips,
                list(self.project.audio),
                list(self.project.overlays),
                self.project.width,
                self.project.height,
                self.project.fps,
                self.project.preset,
            )
            self._set_project(updated)
            self.status.setText("Trim applied")
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _apply_media_settings(self) -> None:
        if not self.project or self.selected_track != "video" or self.selected_index is None:
            QMessageBox.information(self, "Kubrick", "Select a video clip first.")
            return
        try:
            speed = float(self.speed.text())
            volume = float(self.volume.text())
            if speed <= 0 or volume < 0:
                raise ValueError("speed must be positive and volume cannot be negative")
            clips = list(self.project.video)
            clip = clips[self.selected_index]
            clips[self.selected_index] = MediaClip(
                clip.path,
                clip.source_start,
                clip.source_end,
                clip.timeline_start,
                volume,
                speed,
                clip.filters,
            )
            timeline = 0.0
            for i, item in enumerate(clips):
                clips[i] = MediaClip(
                    item.path,
                    item.source_start,
                    item.source_end,
                    timeline,
                    item.volume,
                    item.speed,
                    item.filters,
                )
                timeline += clips[i].duration or 0.0
            updated = Project(
                self.project.name,
                clips,
                list(self.project.audio),
                list(self.project.overlays),
                self.project.width,
                self.project.height,
                self.project.fps,
                self.project.preset,
            )
            self._set_project(updated)
            self.status.setText("Clip settings applied")
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _apply_filter(self) -> None:
        if not self.project or self.selected_track != "video" or self.selected_index is None:
            QMessageBox.information(self, "Kubrick", "Select a video clip first.")
            return
        expression = self.filter.text().strip()
        self._snapshot_and(
            lambda project: add_filter(project, expression, self.selected_index),
            "Filter applied",
        )

    def _add_text(self) -> None:
        if not self.project or not self.project.video:
            return
        overlay = Overlay("text", "Your title", 0, min(3.0, project_duration(self.project)))
        self._snapshot_and(lambda project: add_overlay(project, overlay), "Text layer added")

    def _add_image(self) -> None:
        if not self.project or not self.project.video:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not path:
            return
        overlay = Overlay(
            "image",
            path,
            0,
            min(3.0, project_duration(self.project)),
            width=420,
            height=240,
        )
        self._snapshot_and(lambda project: add_overlay(project, overlay), "Image layer added")

    def _add_shape(self) -> None:
        if not self.project or not self.project.video:
            return
        overlay = Overlay(
            "shape",
            "#d52b1e",
            0,
            min(2.0, project_duration(self.project)),
            width=420,
            height=120,
            opacity=0.85,
        )
        self._snapshot_and(lambda project: add_overlay(project, overlay), "Shape layer added")

    def _add_audio(self) -> None:
        if not self.project or not self.project.video:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose audio",
            "",
            "Audio files (*.mp3 *.wav *.m4a *.aac *.flac *.ogg);;All files (*)",
        )
        if not path:
            return
        try:
            duration = probe_duration(path)
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", f"Could not inspect audio:\n{exc}")
            return
        audio = AudioClip(path, 0, duration, 0, 1.0)
        self._snapshot_and(lambda project: add_audio(project, audio), "Audio layer added")

    def _remove_selected(self) -> None:
        if not self.project or self.selected_index is None or not self.selected_track:
            return
        track = self.selected_track
        index = self.selected_index
        if track == "video" and index < len(self.project.video):
            if len(self.project.video) == 1:
                QMessageBox.warning(self, "Kubrick", "A project needs at least one video clip.")
                return
            clips = [clip for i, clip in enumerate(self.project.video) if i != index]
            timeline = 0.0
            normalized = []
            for clip in clips:
                normalized.append(
                    MediaClip(
                        clip.path,
                        clip.source_start,
                        clip.source_end,
                        timeline,
                        clip.volume,
                        clip.speed,
                        clip.filters,
                    )
                )
                timeline += normalized[-1].duration or 0.0
            updated = Project(
                self.project.name,
                normalized,
                list(self.project.audio),
                list(self.project.overlays),
                self.project.width,
                self.project.height,
                self.project.fps,
                self.project.preset,
            )
            self._set_project(updated)
            self.selected_index = None
            self.selected_track = None
            self.status.setText("Clip removed")
        elif track == "audio" and index < len(self.project.audio):
            updated = Project(
                self.project.name,
                list(self.project.video),
                [clip for i, clip in enumerate(self.project.audio) if i != index],
                list(self.project.overlays),
                self.project.width,
                self.project.height,
                self.project.fps,
                self.project.preset,
            )
            self._set_project(updated)
            self.status.setText("Audio layer removed")
        elif track in {"text", "image", "shape"} and index < len(self.project.overlays):
            updated = Project(
                self.project.name,
                list(self.project.video),
                list(self.project.audio),
                [overlay for i, overlay in enumerate(self.project.overlays) if i != index],
                self.project.width,
                self.project.height,
                self.project.fps,
                self.project.preset,
            )
            self._set_project(updated)
            self.status.setText("Layer removed")

    def _cut_range(self) -> None:
        if not self.project or not self.project.video:
            return
        try:
            start = float(self.cut_start.text())
            end = float(self.cut_end.text())
            self._snapshot_and(
                lambda project: cut_range(project, start, end),
                f"Cut {start:.2f}–{end:.2f}s",
            )
        except ValueError as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _undo(self) -> None:
        if not self.history or self.project is None:
            return
        self.future.append(copy.deepcopy(self.project))
        self.project = self.history.pop()
        self.source = Path(self.project.video[0].path) if self.project.video else None
        if self.source and self.source.exists():
            self.player.setSource(QUrl.fromLocalFile(str(self.source)))
        self._refresh()
        self.status.setText("Undo")

    def _redo(self) -> None:
        if not self.future or self.project is None:
            return
        self.history.append(copy.deepcopy(self.project))
        self.project = self.future.pop()
        self.source = Path(self.project.video[0].path) if self.project.video else None
        if self.source and self.source.exists():
            self.player.setSource(QUrl.fromLocalFile(str(self.source)))
        self._refresh()
        self.status.setText("Redo")

    def _render(self) -> None:
        if self._building:
            return
        if not self.project or not self.project.video:
            QMessageBox.warning(self, "Kubrick", "Import footage first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Render video",
            f"{self.project.name}_kubrick.mp4",
            "MP4 video (*.mp4)",
        )
        if not path:
            return
        project = copy.deepcopy(self.project)
        self._building = True
        self.auto.setEnabled(False)
        self.render.setEnabled(False)
        self.status.setText("Rendering…")
        self._run_worker(lambda: render_project(project, path), self._render_done)

    def _render_done(self, _result) -> None:
        self._building = False
        self.auto.setEnabled(True)
        self.render.setEnabled(True)
        self.status.setText("Render complete")
        QMessageBox.information(self, "Kubrick", "Render complete. The output file is ready.")

    def _run_worker(self, fn, callback) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        thread = QThread(self)
        worker = Worker(fn)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(callback)
        worker.failed.connect(self._worker_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._worker_finished)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _worker_failed(self, message: str) -> None:
        self._building = False
        self.auto.setEnabled(True)
        self.render.setEnabled(True)
        self.status.setText("Operation failed")
        QMessageBox.critical(self, "Kubrick", message)

    def _worker_finished(self) -> None:
        self._thread = None
        self._worker = None

    def _toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play.setText("▶")
        else:
            self.player.play()
            self.play.setText("Ⅱ")

    def _seek(self, value: int) -> None:
        self.player.setPosition(value)

    def _position_changed(self, position: int) -> None:
        self.seek.setValue(position)
        self.time.setText(f"{self._format_ms(position)} / {self._format_ms(self.player.duration())}")

    def _duration_changed(self, duration: int) -> None:
        self.seek.setRange(0, max(0, duration))
        self.time.setText(f"{self._format_ms(self.player.position())} / {self._format_ms(duration)}")

    @staticmethod
    def _format_ms(milliseconds: int) -> str:
        seconds = max(0, milliseconds // 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def _refresh(self) -> None:
        self.timeline.setRowCount(0)
        if not self.project:
            self.clip_info.setText("No project")
            return
        row = 0
        for index, clip in enumerate(sorted(self.project.video, key=lambda item: item.timeline_start)):
            self.timeline.insertRow(row)
            self._set_timeline_row(row, "VIDEO", index, clip.path, clip.timeline_start, clip.timeline_start + (clip.duration or 0.0))
            row += 1
        for index, clip in enumerate(self.project.audio):
            duration = 0.0 if clip.source_end is None else clip.source_end - clip.source_start
            self.timeline.insertRow(row)
            self._set_timeline_row(row, "AUDIO", index, clip.path, clip.timeline_start, clip.timeline_start + duration)
            row += 1
        for index, overlay in enumerate(self.project.overlays):
            end = overlay.end if overlay.end is not None else project_duration(self.project)
            self.timeline.insertRow(row)
            self._set_timeline_row(row, overlay.kind.upper(), index, overlay.value, overlay.start, end)
            row += 1
        self._update_inspector()

    def _set_timeline_row(self, row: int, track: str, index: int, source: str, start: float, end: float) -> None:
        values = [
            track,
            Path(source).name if track in {"VIDEO", "AUDIO", "IMAGE"} else source,
            f"{start:.2f}",
            f"{end:.2f}",
            f"{max(0.0, end - start):.2f}",
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column == 0:
                item.setData(Qt.ItemDataRole.UserRole, index)
            self.timeline.setItem(row, column, item)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Kubrick")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
