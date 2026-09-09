from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QComboBox, QPushButton, QProgressBar

from kubrick.core import PRESETS
from kubrick.editor import project_duration

FILTERS = {
    "None": "",
    "Natural contrast": "eq=contrast=1.03:saturation=1.02",
    "Punchy": "eq=contrast=1.04:brightness=0.01:saturation=1.04",
    "Soft": "eq=contrast=0.97:saturation=0.97",
    "Grayscale": "hue=s=0",
    "Sharpen": "unsharp=5:5:0.5:5:5:0",
}


def install(window) -> None:
    """Upgrade the current editor UI without duplicating the main window."""
    for button in window.findChildren(QPushButton):
        text = button.text().strip()
        if text == "Project":
            button.clicked.connect(lambda: _nav(window, "Project"))
        elif text == "Edit":
            button.clicked.connect(lambda: _nav(window, "Edit"))
        elif text == "Auto Edit":
            button.clicked.connect(lambda: _nav(window, "Auto Edit"))
        elif text == "Scenes":
            button.clicked.connect(lambda: _nav(window, "Scenes"))
        elif text == "Transcript":
            button.clicked.connect(lambda: _nav(window, "Transcript"))
        elif text == "Audio":
            button.clicked.connect(lambda: _nav(window, "Audio"))

    if hasattr(window, "preset"):
        window.preset.setToolTip("Auto Edit style. Select one, then press Auto Edit.")
        window.preset.currentTextChanged.connect(lambda name: _preset_status(window, name))
        _preset_status(window, window.preset.currentText())

    old = getattr(window, "filter", None)
    if old is not None:
        parent = old.parentWidget()
        combo = QComboBox(parent)
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

    if hasattr(window, "timeline"):
        window.timeline.setToolTip("Each block is an editable timeline segment. Ctrl+wheel zooms the timeline.")

    _install_project_preview(window)

    if not hasattr(window, "_ux_busy_bar"):
        bar = QProgressBar(window)
        bar.setRange(0, 0)
        bar.setFixedHeight(4)
        bar.hide()
        window._ux_busy_bar = bar
        window.statusBar().addPermanentWidget(bar, 1)


def _nav(window, name: str) -> None:
    labels = {"Project", "Edit", "Auto Edit", "Scenes", "Transcript", "Audio"}
    for button in window.findChildren(QPushButton):
        text = button.text().strip()
        if text in labels:
            button.setObjectName("navActive" if text == name else "nav")
            button.style().unpolish(button)
            button.style().polish(button)
    if name == "Project":
        window.video.setFocus()
        window.status.setText("Project · preview and source")
    elif name == "Edit":
        window.trim_start.setFocus()
        window.status.setText("Edit · select a timeline clip")
    elif name == "Auto Edit":
        window.preset.setFocus()
        window.status.setText(f"Auto Edit · {window.preset.currentText()}")
    elif name == "Scenes":
        window.timeline.setFocus()
        window.status.setText("Scenes · automatic edit segments are shown on the video track")
    elif name == "Transcript":
        window.status.setText("Transcript · optional speech analysis is available from the speech extra")
    elif name == "Audio":
        window.status.setText("Audio · add a music or voice layer from the Inspector")


def _preset_status(window, name: str) -> None:
    preset = PRESETS.get(name)
    if preset:
        window.preset.setStatusTip(preset.description)
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
    window.filter.setStatusTip(descriptions.get(name, ""))


def _install_project_preview(window) -> None:
    window._ux_preview_index = -1
    window._ux_project_position = 0.0
    window._ux_wanted_position = 0.0
    window._ux_loading = False
    window._ux_autoplay = False

    def find_clip(position: float):
        if not window.project or not window.project.video:
            return None
        for i, clip in enumerate(window.project.video):
            end = clip.timeline_end or clip.timeline_start
            if clip.timeline_start <= position < end or (i == len(window.project.video) - 1 and math.isclose(position, end, abs_tol=0.03)):
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
        if index != window._ux_preview_index or window.player.source().toLocalFile() != str(Path(clip.path).resolve()):
            load_clip(index, target, autoplay)
        else:
            window.player.setPosition(int(source * 1000))
            if autoplay:
                window.player.play()
        window.timeline.set_position(target)
        window.seek.blockSignals(True)
        window.seek.setValue(int(target * 1000))
        window.seek.blockSignals(False)
        window.time.setText(f"{window._fmt(target)} / {window._fmt(duration)}")

    def position_changed(ms: int):
        if not window.project or window._ux_preview_index < 0 or window._ux_preview_index >= len(window.project.video):
            return
        clip = window.project.video[window._ux_preview_index]
        source = ms / 1000
        project_pos = clip.timeline_start + max(0.0, source - clip.source_start) / clip.speed
        end = clip.timeline_end or clip.timeline_start
        if clip.source_end is not None and source >= clip.source_end - 0.04 and project_pos < end - 0.01:
            nxt = window._ux_preview_index + 1
            if nxt < len(window.project.video):
                load_clip(nxt, window.project.video[nxt].timeline_start, True)
                return
        window._ux_project_position = min(project_duration(window.project), project_pos)
        window.timeline.set_position(window._ux_project_position)
        window.seek.blockSignals(True)
        window.seek.setValue(int(window._ux_project_position * 1000))
        window.seek.blockSignals(False)
        window.time.setText(f"{window._fmt(window._ux_project_position)} / {window._fmt(project_duration(window.project))}")

    def media_status(status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia and window._ux_loading:
            window._ux_loading = False
            clip = window.project.video[window._ux_preview_index]
            source = clip.source_start + max(0.0, window._ux_wanted_position - clip.timeline_start) * clip.speed
            window.player.setPosition(int(source * 1000))
            if window._ux_autoplay:
                window.player.play()

    window._ux_seek_project = seek_project
    window._ux_find_clip = find_clip
    window.player.positionChanged.disconnect(window._position_changed)
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
        window.selected_track, window.selected_index = track, index
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
        duration = project_duration(window.project) if window.project and window.project.video else 0.0
        window.seek.setRange(0, int(duration * 1000))
        window._ux_project_position = min(window._ux_project_position, duration)
        window.timeline.set_position(window._ux_project_position)
        window.time.setText(f"{window._fmt(window._ux_project_position)} / {window._fmt(duration)}")
        window._update_inspector()

    window._refresh = refresh

    def auto_done(project, original):
        if hasattr(window, "_set_busy"):
            window._set_busy(False)
        window._set_project(project)
        edited = project_duration(project)
        removed = max(0.0, original - edited)
        window.review.setText(
            f"AUTO EDIT RESULT\nOriginal {window._fmt(original)} → Timeline {window._fmt(edited)}\n"
            f"Removed {window._fmt(removed)} · {len(project.video)} editable segments\n\n"
            "The preview follows the edited timeline. Render to create the final MP4."
        )
        window.status.setText(f"Auto Edit ready · {len(project.video)} segments · {window._fmt(edited)}")
        seek_project(0, False)

    window._auto_done = auto_done
    refresh()


def _fmt(window, seconds: float) -> str:
    return window._format_ms(int(seconds * 1000))
