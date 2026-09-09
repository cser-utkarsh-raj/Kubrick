from __future__ import annotations

import copy
import sys
from pathlib import Path

try:
    from PySide6.QtCore import QObject, QThread, Qt, QUrl, Signal
    from PySide6.QtGui import QIcon, QKeySequence, QShortcut
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
        QScrollArea,
        QSlider,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Install the GUI extra with: python -m pip install -e '.[gui]'") from exc

from kubrick.core import AudioClip, MediaClip, Overlay, Project
from kubrick.editor import add_audio, add_filter, add_overlay, build_preset_project, cut_range, project_duration, trim_clip
from kubrick.media import probe_duration, render_project
from kubrick.ui.timeline import TimelineWidget

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
QScrollArea { background:#090909; border:0; }
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
        self._kubrick_ux_installed = False
        self._build()
        self._install_shortcuts()
        self._reset_project()
        from kubrick.ui.ux import install
        install(self)
        self._kubrick_ux_installed = True

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

    def _install_shortcuts(self) -> None:
        shortcuts = [("Space", self._toggle_play), ("Left", lambda: self._nudge_position(-100)), ("Right", lambda: self._nudge_position(100)), ("Shift+Left", lambda: self._nudge_position(-1000)), ("Shift+Right", lambda: self._nudge_position(1000)), ("I", self._set_in), ("O", self._set_out), ("Ctrl+Z", self._undo), ("Ctrl+Shift+Z", self._redo)]
        self._shortcuts = []
        for sequence, slot in shortcuts:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)

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
        for label, active in [("⌂  Project", True), ("✂  Edit", False), ("✦  Auto Edit", False), ("▦  Scenes", False), ("≡  Transcript", False), ("◫  Audio", False)]:
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
        for text, slot in [("New", self._reset_project), ("Open", self._open_project), ("Save", self._save_project), ("Import", self._import_video)]:
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
        self.volume = QLineEdit("1.0")
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
        for text, slot in [("+ Text", self._add_text), ("+ Image", self._add_image), ("+ Shape", self._add_shape), ("+ Audio", self._add_audio)]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            layout.addWidget(button)
        label = QLabel("FILTER")
        label.setObjectName("eyebrow")
        layout.addWidget(label)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("choose an effect")
        layout.addWidget(self.filter)
        filter_button = QPushButton("Apply to selected clip")
        filter_button.clicked.connect(self._apply_filter)
        layout.addWidget(filter_button)
        remove = QPushButton("Remove selected layer / clip")
        remove.setObjectName("danger")
        remove.clicked.connect(self._remove_selected)
        layout.addWidget(remove)
        layout.addStretch(1)
        self.review = QLabel("Automatic decisions become normal editable clips. Nothing is rendered until you press Render.")
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
        hint = QLabel("Click to seek · drag audio/layers · Ctrl+wheel to zoom")
        hint.setObjectName("muted")
        head.addWidget(hint)
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
        self.timeline = TimelineWidget()
        self.timeline.clip_selected.connect(self._timeline_selected)
        self.timeline.position_selected.connect(self._timeline_position)
        self.timeline.clip_moved.connect(self._timeline_moved)
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setWidget(self.timeline)
        layout.addWidget(scroll, 1)
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
        if hasattr(self, "_refresh"):
            self._refresh()
        else:
            self.timeline.set_project(self.project)

    def _import_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import video", "", "Video files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v);;All files (*)")
        if path:
            self._load_source(Path(path))

    def _load_source(self, source: Path) -> None:
        try:
            duration = probe_duration(source)
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", f"Could not inspect media:\n{exc}")
            return
        self.project = Project(name=source.stem, video=[MediaClip(str(source), 0, duration, 0)])
        self.source = source
        self.history.clear()
        self.future.clear()
        self.project_title.setText(source.stem.upper())
        self.player.setSource(QUrl.fromLocalFile(str(source)))
        self.status.setText(f"Imported · {duration:.1f}s")
        self._refresh()

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Kubrick project", "", "Kubrick projects (*.kubrick.json);;JSON (*.json)")
        if not path:
            return
        try:
            project = Project.load(path)
            project.validate()
            self._set_project(project, push_history=False)
            self.status.setText(f"Loaded · {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _save_project(self) -> None:
        if not self.project or not self.project.video:
            QMessageBox.warning(self, "Kubrick", "Import footage first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save project", f"{self.project.name}.kubrick.json", "Kubrick project (*.kubrick.json)")
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
        self._run_worker(lambda: build_preset_project(self.source, preset_name), self._auto_done)

    def _auto_done(self, project: Project) -> None:
        self._building = False
        self.auto.setEnabled(True)
        self.render.setEnabled(True)
        self._set_project(project)
        self.review.setText(f"Auto edit produced {len(project.video)} main-video segments. Review them, then render.")
        self.status.setText(f"Auto edit ready · {len(project.video)} segments")

    def _timeline_selected(self, track: str, index: int) -> None:
        self.selected_track = track
        self.selected_index = index
        self._update_inspector()

    def _timeline_position(self, position: float) -> None:
        if hasattr(self, "_ux_seek_project"):
            self._ux_seek_project(position)
        else:
            self.player.setPosition(int(position * 1000))

    def _timeline_moved(self, track: str, index: int, start: float) -> None:
        if not self.project:
            return
        try:
            if track == "audio" and 0 <= index < len(self.project.audio):
                old = self.project.audio[index]
                updated_audio = list(self.project.audio)
                updated_audio[index] = AudioClip(old.path, old.source_start, old.source_end, start, old.volume, old.fade_in, old.fade_out)
                self._set_project(Project(self.project.name, list(self.project.video), updated_audio, list(self.project.overlays), self.project.width, self.project.height, self.project.fps, self.project.preset))
                self.status.setText("Audio layer moved")
            elif track in {"text", "image", "shape"} and 0 <= index < len(self.project.overlays):
                old = self.project.overlays[index]
                duration = (old.end - old.start) if old.end is not None else None
                end = None if duration is None else start + duration
                updated_overlays = list(self.project.overlays)
                updated_overlays[index] = Overlay(old.kind, old.value, start, end, old.x, old.y, old.width, old.height, old.font_size, old.color, old.opacity, old.border_radius)
                self._set_project(Project(self.project.name, list(self.project.video), list(self.project.audio), updated_overlays, self.project.width, self.project.height, self.project.fps, self.project.preset))
                self.status.setText("Layer moved")
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

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
            clips = list(self.project.video)
            clips[self.selected_index] = trim_clip(clips[self.selected_index], start, end)
            timeline = 0.0
            normalized = []
            for clip in clips:
                item = MediaClip(clip.path, clip.source_start, clip.source_end, timeline, clip.volume, clip.speed, clip.filters)
                normalized.append(item)
                timeline += item.duration or 0.0
            self._set_project(Project(self.project.name, normalized, list(self.project.audio), list(self.project.overlays), self.project.width, self.project.height, self.project.fps, self.project.preset))
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
            clips[self.selected_index] = MediaClip(clip.path, clip.source_start, clip.source_end, clip.timeline_start, volume, speed, clip.filters)
            timeline = 0.0
            normalized = []
            for item in clips:
                normalized_item = MediaClip(item.path, item.source_start, item.source_end, timeline, item.volume, item.speed, item.filters)
                normalized.append(normalized_item)
                timeline += normalized_item.duration or 0.0
            self._set_project(Project(self.project.name, normalized, list(self.project.audio), list(self.project.overlays), self.project.width, self.project.height, self.project.fps, self.project.preset))
            self.status.setText("Clip settings applied")
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _apply_filter(self) -> None:
        if not self.project or self.selected_track != "video" or self.selected_index is None:
            QMessageBox.information(self, "Kubrick", "Select a video clip first.")
            return
        expression = self.filter.text().strip()
        self._snapshot_and(lambda project: add_filter(project, expression, self.selected_index), "Filter applied")

    def _add_text(self) -> None:
        if not self.project or not self.project.video:
            return
        overlay = Overlay("text", "Your title", 0, min(3.0, project_duration(self.project)))
        self._snapshot_and(lambda project: add_overlay(project, overlay), "Text layer added")

    def _add_image(self) -> None:
        if not self.project or not self.project.video:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        overlay = Overlay("image", path, 0, min(3.0, project_duration(self.project)), width=420, height=240)
        self._snapshot_and(lambda project: add_overlay(project, overlay), "Image layer added")

    def _add_shape(self) -> None:
        if not self.project or not self.project.video:
            return
        overlay = Overlay("shape", "#d52b1e", 0, min(3.0, project_duration(self.project)), x=40, y=40, width=320, height=180, opacity=0.75)
        self._snapshot_and(lambda project: add_overlay(project, overlay), "Shape layer added")

    def _add_audio(self) -> None:
        if not self.project or not self.project.video:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose audio", "", "Audio (*.wav *.mp3 *.m4a *.aac *.flac *.ogg)")
        if not path:
            return
        try:
            duration = probe_duration(path)
            clip = AudioClip(path, 0, duration, 0)
            self._snapshot_and(lambda project: add_audio(project, clip), "Audio layer added")
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _remove_selected(self) -> None:
        if not self.project or self.selected_index is None or self.selected_track is None:
            QMessageBox.information(self, "Kubrick", "Select a timeline item first.")
            return
        if self.selected_track == "video" and 0 <= self.selected_index < len(self.project.video):
            clips = list(self.project.video)
            clips.pop(self.selected_index)
            timeline = 0.0
            normalized = []
            for clip in clips:
                item = MediaClip(clip.path, clip.source_start, clip.source_end, timeline, clip.volume, clip.speed, clip.filters)
                normalized.append(item)
                timeline += item.duration or 0.0
            self._set_project(Project(self.project.name, normalized, list(self.project.audio), list(self.project.overlays), self.project.width, self.project.height, self.project.fps, self.project.preset))
            self.selected_index = None
            self.status.setText("Video segment removed")
        elif self.selected_track == "audio" and 0 <= self.selected_index < len(self.project.audio):
            audio = list(self.project.audio)
            audio.pop(self.selected_index)
            self._set_project(Project(self.project.name, list(self.project.video), audio, list(self.project.overlays), self.project.width, self.project.height, self.project.fps, self.project.preset))
            self.selected_index = None
            self.status.setText("Audio layer removed")
        elif self.selected_track in {"text", "image", "shape"}:
            matches = [i for i, item in enumerate(self.project.overlays) if item.kind == self.selected_track]
            if self.selected_index in matches:
                overlays = list(self.project.overlays)
                overlays.pop(self.selected_index)
                self._set_project(Project(self.project.name, list(self.project.video), list(self.project.audio), overlays, self.project.width, self.project.height, self.project.fps, self.project.preset))
                self.selected_index = None
                self.status.setText("Layer removed")

    def _cut_range(self) -> None:
        if not self.project or not self.project.video:
            return
        try:
            start, end = float(self.cut_start.text()), float(self.cut_end.text())
            self._snapshot_and(lambda project: cut_range(project, start, end), f"Cut {start:.2f}–{end:.2f}s")
        except Exception as exc:
            QMessageBox.critical(self, "Kubrick", str(exc))

    def _seek(self, value: int) -> None:
        if hasattr(self, "_ux_seek_project"):
            self._ux_seek_project(value / 1000)
        else:
            self.player.setPosition(value)

    def _position_changed(self, position: int) -> None:
        if not hasattr(self, "_ux_project_position"):
            self.time.setText(f"{position / 1000:.1f}s")

    def _duration_changed(self, duration: int) -> None:
        if not hasattr(self, "_ux_project_position"):
            self.seek.setRange(0, duration)
            self.time.setText(f"00:00 / {duration / 1000:.2f}")

    def _toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _nudge_position(self, delta_ms: int) -> None:
        if hasattr(self, "_ux_project_position"):
            self._ux_seek_project(self._ux_project_position + delta_ms / 1000)
        else:
            self.player.setPosition(max(0, self.player.position() + delta_ms))

    def _set_in(self) -> None:
        if self.player.source().isValid():
            self.trim_start.setText(f"{self.player.position() / 1000:.3f}")

    def _set_out(self) -> None:
        if self.player.source().isValid():
            self.trim_end.setText(f"{self.player.position() / 1000:.3f}")

    def _undo(self) -> None:
        if not self.history:
            return
        self.future.append(copy.deepcopy(self.project))
        self.project = self.history.pop()
        self._refresh()

    def _redo(self) -> None:
        if not self.future:
            return
        self.history.append(copy.deepcopy(self.project))
        self.project = self.future.pop()
        self._refresh()

    def _run_worker(self, fn, done) -> None:
        self._thread = QThread(self)
        self._worker = Worker(fn)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(done)
        self._worker.failed.connect(self._worker_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _worker_failed(self, message: str) -> None:
        self._building = False
        self.auto.setEnabled(True)
        self.render.setEnabled(True)
        QMessageBox.critical(self, "Kubrick", message)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.auto.setEnabled(not busy)
        self.render.setEnabled(not busy)
        if message:
            self.status.setText(message)

    def _refresh(self) -> None:
        self.timeline.set_project(self.project)
        duration = project_duration(self.project) if self.project and self.project.video else 0.0
        self.seek.setRange(0, int(duration * 1000))
        self.time.setText(f"00:00 / {self._format_ms(int(duration * 1000))}")
        self._update_inspector()

    @staticmethod
    def _format_ms(value: int) -> str:
        total = max(0, value // 1000)
        minutes, seconds = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

    def _render(self) -> None:
        if not self.project or not self.project.video:
            QMessageBox.warning(self, "Kubrick", "Import footage first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Render video", f"{self.project.name}_edited.mp4", "MP4 video (*.mp4)")
        if not path:
            return
        self._set_busy(True, "Rendering…")
        self._run_worker(lambda: render_project(self.project, path), lambda _: self._render_done(path))

    def _render_done(self, path: str) -> None:
        self._set_busy(False, f"Rendered · {Path(path).name}")
        QMessageBox.information(self, "Kubrick", f"Render complete:\n{path}")


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
