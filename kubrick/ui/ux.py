from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QComboBox, QFrame, QPushButton, QProgressBar, QScrollArea, QSplitter

from kubrick.core import PRESETS
from kubrick.editor import project_duration
from kubrick.media import probe_duration

FILTERS = {
    "None": "",
    "Natural contrast": "eq=contrast=1.03:saturation=1.02",
    "Punchy": "eq=contrast=1.04:brightness=0.01:saturation=1.04",
    "Soft": "eq=contrast=0.97:saturation=0.97",
    "Grayscale": "hue=s=0",
    "Sharpen": "unsharp=5:5:0.5:5:5:0",
}


class FilterCombo(QComboBox):
    """Named filter selector that keeps the editor's text() contract."""

    def text(self) -> str:
        return FILTERS[self.currentText()]


def install(window) -> None:
    """Install the editor UX once all base widgets have been constructed."""
    if getattr(window, "_kubrick_ux_installed", False):
        return

    _wire_navigation(window)
    _fix_inspector(window)
    _configure_splitters(window)
    _configure_preset(window)
    _replace_filter(window)
    _configure_timeline(window)
    _install_project_preview(window)
    _install_busy_ui(window)
    _install_auto_edit_guard(window)


def _wire_navigation(window) -> None:
    labels = ("Project", "Edit", "Auto Edit", "Scenes", "Transcript", "Audio")
    for button in window.findChildren(QPushButton):
        text = button.text().strip()
        name = next((label for label in labels if text.endswith(label)), None)
        if name is not None:
            button.clicked.connect(lambda _checked=False, target=name: _nav(window, target))


def _fix_inspector(window) -> None:
    panel = window.findChild(QFrame, "panel")
    if panel is None or getattr(window, "_ux_inspector_scroll", None) is not None:
        return
    splitter = panel.parentWidget()
    if not isinstance(splitter, QSplitter):
        return
    index = splitter.indexOf(panel)
    if index < 0:
        return
    panel.setMinimumWidth(292)
    layout = panel.layout()
    if layout is not None:
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
    scroll = QScrollArea()
    scroll.setObjectName("inspectorScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(panel)
    splitter.replaceWidget(index, scroll)
    splitter.setCollapsible(index, False)
    splitter.setStretchFactor(index, 0)
    window._ux_inspector_scroll = scroll


def _configure_splitters(window) -> None:
    for splitter in window.findChildren(QSplitter):
        splitter.setOpaqueResize(True)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        if splitter.orientation() == Qt.Orientation.Vertical and splitter.count() == 2:
            splitter.setCollapsible(0, False)
            splitter.setCollapsible(1, False)
            splitter.setStretchFactor(0, 3)
            splitter.setStretchFactor(1, 1)
            splitter.setSizes([560, 260])
            splitter.setMinimumHeight(220)
            window._ux_main_splitter = splitter
        elif splitter.orientation() == Qt.Orientation.Horizontal and splitter.count() == 2:
            splitter.setCollapsible(0, False)
            splitter.setCollapsible(1, False)
            splitter.setStretchFactor(0, 3)
            splitter.setStretchFactor(1, 1)
            splitter.setSizes([900, 320])


def _configure_preset(window) -> None:
    if not hasattr(window, "preset"):
        return
    window.preset.setToolTip("Auto Edit style. Select one, then press Auto Edit.")
    window.preset.currentTextChanged.connect(lambda name: _preset_status(window, name))
    _preset_status(window, window.preset.currentText())


def _replace_filter(window) -> None:
    old = getattr(window, "filter", None)
    if old is None or isinstance(old, FilterCombo):
        return
    parent = old.parentWidget()
    combo = FilterCombo(parent)
    combo.addItems(FILTERS)
    combo.setToolTip("Choose a visual effect for the selected video clip.")
    layout = parent.layout()
    if layout is not None:
        for i in range(layout.count()):
            if layout.itemAt(i).widget() is old:
                layout.insertWidget(i, combo)
                old.hide()
                break
    window.filter = combo
    combo.currentTextChanged.connect(lambda name: _filter_status(window, name))
    _filter_status(window, combo.currentText())


def _configure_timeline(window) -> None:
    if hasattr(window, "timeline"):
        window.timeline.setToolTip(
            "Click a clip to select it. Drag audio/layers. Ctrl+wheel zooms. Drag the splitter handle to resize the timeline."
        )


def _install_busy_ui(window) -> None:
    bar = QProgressBar(window)
    bar.setRange(0, 0)
    bar.setFixedHeight(4)
    bar.hide()
    window._ux_busy_bar = bar
    window.statusBar().addPermanentWidget(bar, 1)

    original_set_busy = window._set_busy

    def set_busy(busy: bool, message: str = "") -> None:
        original_set_busy(busy, message)
        bar.setVisible(busy)

    window._set_busy = set_busy

    original_failed = window._worker_failed

    def worker_failed(message: str) -> None:
        bar.hide()
        original_failed(message)

    window._worker_failed = worker_failed


def _install_auto_edit_guard(window) -> None:
    """Show busy state for Auto Edit and restore it on both success and failure."""
    button = getattr(window, "auto", None)
    bar = getattr(window, "_ux_busy_bar", None)
    original = getattr(window, "_auto_edit", None)
    if button is None or bar is None or original is None:
        return
    try:
        button.clicked.disconnect(original)
    except (RuntimeError, TypeError):
        pass

    def auto_edit() -> None:
        if not getattr(window, "_building", False):
            bar.show()
        original()

    button.clicked.connect(auto_edit)
    window._auto_edit_ux = auto_edit


def _nav(window, name: str) -> None:
    labels = {"Project", "Edit", "Auto Edit", "Scenes", "Transcript", "Audio"}
    for button in window.findChildren(QPushButton):
        text = button.text().strip()
        target = next((label for label in labels if text.endswith(label)), None)
        if target is not None:
            button.setObjectName("navActive" if target == name else "nav")
            button.style().unpolish(button)
            button.style().polish(button)

    if name == "Project":
        window.video.setFocus()
        window.status.setText("Project · preview and source")
    elif name == "Edit":
        _ensure_video_selection(window)
        window.trim_start.setFocus()
        window.status.setText("Edit · clip controls ready")
    elif name == "Auto Edit":
        window.preset.setFocus()
        window.status.setText(f"Auto Edit · {window.preset.currentText()} · press Auto Edit to run")
    elif name == "Scenes":
        window.timeline.setFocus()
        window.status.setText("Scenes · editable segments are shown on the video track")
    elif name == "Transcript":
        window.status.setText("Transcript · speech analysis is available from the speech extra")
    elif name == "Audio":
        window.status.setText("Audio · add music or voice layers from the Inspector")


def _ensure_video_selection(window) -> None:
    if not window.project or not window.project.video:
        return
    if (
        getattr(window, "selected_track", None) != "video"
        or getattr(window, "selected_index", None) is None
        or window.selected_index >= len(window.project.video)
    ):
        window.selected_track = "video"
        window.selected_index = 0
        window._update_inspector()


def _preset_status(window, name: str) -> None:
    preset = PRESETS.get(name)
    if preset:
        window.preset.setStatusTip(preset.description)
        window.preset.setToolTip(preset.description)
        window.statusBar().showMessage(f"{name}: {preset.description}", 3500)


def _filter_status(window, name: str) -> None:
    descriptions = {
        "None": "No visual effect.",
        "Natural contrast": "Small contrast/saturation lift.",
        "Punchy": "Stronger contrast, brightness and saturation.",
        "Soft": "Softer, flatter image.",
        "Grayscale": "Removes color.",
        "Sharpen": "Mild edge sharpening.",
    }
    description = descriptions.get(name, "")
    window.filter.setStatusTip(description)
    window.filter.setToolTip(description)


def _install_project_preview(window) -> None:
    window._ux_preview_index = -1
    window._ux_project_position = 0.0
    window._ux_wanted_position = 0.0
    window._ux_loading = False
    window._ux_autoplay = False

    def fmt(seconds: float) -> str:
        total = max(0, int(seconds * 1000))
        whole = total // 1000
        minutes, seconds_left = divmod(whole, 60)
        hours, minutes_left = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes_left:02d}:{seconds_left:02d}"
        return f"{minutes_left:02d}:{seconds_left:02d}"

    window._ux_fmt = fmt

    def find_clip(position: float):
        if not window.project or not window.project.video:
            return None
        for i, clip in enumerate(window.project.video):
            end = clip.timeline_end or clip.timeline_start
            if clip.timeline_start <= position < end or (
                i == len(window.project.video) - 1
                and math.isclose(position, end, abs_tol=0.03)
            ):
                return i
        return None

    def load_clip(index: int, project_position: float, autoplay: bool):
        if not window.project or not 0 <= index < len(window.project.video):
            return
        clip = window.project.video[index]
        local = max(0.0, project_position - clip.timeline_start)
        source = clip.source_start + local * clip.speed
        window._ux_preview_index = index
        window._ux_wanted_position = project_position
        window._ux_autoplay = autoplay
        window._ux_loading = True
        window.player.setSource(QUrl.fromLocalFile(str(Path(clip.path).resolve())))
        window.player.setPosition(int(source * 1000))

    def seek_project(position: float, autoplay: bool = False):
        if not window.project or not window.project.video:
            return
        duration = project_duration(window.project)
        target = max(0.0, min(duration, position))
        index = find_clip(target)
        if index is None:
            return
        clip = window.project.video[index]
        local = max(0.0, target - clip.timeline_start)
        source = clip.source_start + local * clip.speed
        window._ux_project_position = target

        if (
            index != window._ux_preview_index
            or window.player.source().toLocalFile() != str(Path(clip.path).resolve())
        ):
            load_clip(index, target, autoplay)
        else:
            window.player.setPosition(int(source * 1000))
            if autoplay:
                window.player.play()

        window.timeline.set_position(target)
        window.seek.blockSignals(True)
        window.seek.setValue(int(target * 1000))
        window.seek.blockSignals(False)
        window.time.setText(f"{fmt(target)} / {fmt(duration)}")

    def position_changed(ms: int):
        if (
            not window.project
            or window._ux_preview_index < 0
            or window._ux_preview_index >= len(window.project.video)
        ):
            return

        clip = window.project.video[window._ux_preview_index]
        source = ms / 1000
        project_pos = clip.timeline_start + max(0.0, source - clip.source_start) / clip.speed
        end = clip.timeline_end or clip.timeline_start

        if (
            clip.source_end is not None
            and source >= clip.source_end - 0.04
            and project_pos < end - 0.01
        ):
            nxt = window._ux_preview_index + 1
            if nxt < len(window.project.video):
                load_clip(nxt, window.project.video[nxt].timeline_start, True)
                return

        window._ux_project_position = min(project_duration(window.project), project_pos)
        window.timeline.set_position(window._ux_project_position)
        window.seek.blockSignals(True)
        window.seek.setValue(int(window._ux_project_position * 1000))
        window.seek.blockSignals(False)
        duration = project_duration(window.project)
        window.time.setText(f"{fmt(window._ux_project_position)} / {fmt(duration)}")

    def media_status(status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia and window._ux_loading:
            window._ux_loading = False
            clip = window.project.video[window._ux_preview_index]
            source = clip.source_start + max(
                0.0, window._ux_wanted_position - clip.timeline_start
            ) * clip.speed
            window.player.setPosition(int(source * 1000))
            if window._ux_autoplay:
                window.player.play()

    window._ux_seek_project = seek_project
    window._ux_find_clip = find_clip

    try:
        window.player.positionChanged.disconnect(window._position_changed)
    except (RuntimeError, TypeError):
        pass
    window.player.positionChanged.connect(position_changed)
    window.player.mediaStatusChanged.connect(media_status)

    try:
        window.seek.sliderMoved.disconnect(window._seek)
    except (RuntimeError, TypeError):
        pass
    window.seek.sliderMoved.connect(lambda value: seek_project(value / 1000, False))

    def toggle():
        if not window.project or not window.project.video:
            return
        if window.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            window.player.pause()
            window.play.setText("▶")
        else:
            if window._ux_project_position >= project_duration(window.project) - 0.02:
                seek_project(0, False)
            window.player.play()
            window.play.setText("Ⅱ")

    try:
        window.play.clicked.disconnect(window._toggle_play)
    except (RuntimeError, TypeError):
        pass
    window.play.clicked.connect(toggle)

    def select(track: str, index: int):
        window.selected_track = track
        window.selected_index = index
        window._update_inspector()
        if track == "video" and window.project and 0 <= index < len(window.project.video):
            seek_project(window.project.video[index].timeline_start, False)

    try:
        window.timeline.clip_selected.disconnect(window._timeline_selected)
    except (RuntimeError, TypeError):
        pass
    window.timeline.clip_selected.connect(select)

    def refresh():
        window.timeline.set_project(window.project)
        if window.project and window.project.video:
            _ensure_video_selection(window)
        else:
            window.selected_track = None
            window.selected_index = None
        duration = project_duration(window.project) if window.project and window.project.video else 0.0
        window.seek.setRange(0, int(duration * 1000))
        window._ux_project_position = min(window._ux_project_position, duration)
        window.timeline.set_position(window._ux_project_position)
        window.time.setText(f"{fmt(window._ux_project_position)} / {fmt(duration)}")
        window._update_inspector()

    window._refresh_ux = refresh
    window._refresh = refresh

    def auto_done(project):
        original = 0.0
        if getattr(window, "source", None) is not None:
            try:
                original = probe_duration(window.source)
            except (OSError, RuntimeError, ValueError):
                original = sum((clip.duration or 0.0) for clip in project.video)
        if original <= 0.0:
            original = sum((clip.duration or 0.0) for clip in project.video)
        window._building = False
        window._set_busy(False)
        window._set_project(project)
        edited = project_duration(project)
        removed = max(0.0, original - edited)
        window.review.setText(
            "AUTO EDIT RESULT\n"
            f"Original {fmt(original)} → Timeline {fmt(edited)}\n"
            f"Removed {fmt(removed)} · {len(project.video)} editable segments\n\n"
            "Preview follows the edited timeline. Render to create the final MP4."
        )
        window.status.setText(
            f"Auto Edit ready · {len(project.video)} segments · {fmt(edited)}"
        )
        seek_project(0, False)

    window._auto_done = auto_done
    refresh()


def _fmt(window, seconds: float) -> str:
    """Compatibility formatter used by the main window."""
    return window._ux_fmt(seconds)
