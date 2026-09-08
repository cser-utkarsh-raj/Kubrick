from __future__ import annotations

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
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QProgressBar,
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
    AnalyzerConfig,
    add_filter,
    analyze,
    build_preset_project,
    cut_range,
)
from kubrick.media import render_project

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
QLineEdit, QComboBox { background:#0a0a0a; color:#eee9e2; border:1px solid #303030; border-radius:7px; padding:8px 10px; }
QLineEdit:focus, QComboBox:focus { border:1px solid #d52b1e; }
QPushButton { background:#171717; color:#eee9e2; border:1px solid #343434; border-radius:7px; padding:8px 12px; font-weight:600; }
QPushButton:hover { background:#222; border-color:#4b4b4b; }
QPushButton#primary { background:#c9281d; border-color:#e04438; color:white; }
QPushButton#primary:hover { background:#dc3024; }
QPushButton#nav { text-align:left; background:transparent; border:0; color:#85817b; padding:10px 12px; }
QPushButton#nav:hover, QPushButton#navActive { background:#251311; color:#f4efe8; border-left:2px solid #d52b1e; }
QPushButton#tool { padding:7px 10px; }
QVideoWidget { background:#050505; border:1px solid #282828; border-radius:10px; }
QSlider::groove:horizontal { height:4px; background:#292929; }
QSlider::handle:horizontal { width:12px; margin:-4px 0; border-radius:6px; background:#d52b1e; }
QProgressBar { border:0; background:#181818; border-radius:3px; height:4px; }
QProgressBar::chunk { background:#d52b1e; border-radius:3px; }
QListWidget, QTableWidget { background:#0a0a0a; border:1px solid #252525; border-radius:9px; gridline-color:#1e1e1e; }
QListWidget::item { padding:8px; color:#aaa59e; }
QListWidget::item:selected { background:#2b1513; color:#fff; }
QHeaderView::section { background:#121212; color:#77736e; border:0; border-bottom:1px solid #282828; padding:7px; font-size:9px; }
QTableWidget::item { padding:7px; color:#d4cfc8; }
QTableWidget::item:selected { background:#2b1513; color:white; }
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
        self.report = None
        self._thread: QThread | None = None
        self._worker: Worker | None = None
        self._build()
        self._new_project()

    def _build(self) -> None:
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._sidebar())
        root.addWidget(self._workspace(), 1)
        shell = QWidget()
        shell.setLayout(root)
        self.setCentralWidget(shell)

    def _sidebar(self) -> QWidget:
        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(190)
        layout = QVBoxLayout(side); layout.setContentsMargins(14,18,14,14); layout.setSpacing(4)
        row = QHBoxLayout()
        if MARK.exists():
            mark = QLabel(); mark.setPixmap(QIcon(str(MARK)).pixmap(28,28)); row.addWidget(mark)
        brand = QLabel("KUBRICK"); brand.setObjectName("brand"); row.addWidget(brand); row.addStretch(); layout.addLayout(row)
        sub = QLabel("PRECISION EDITOR"); sub.setObjectName("eyebrow"); sub.setContentsMargins(4,7,4,20); layout.addWidget(sub)
        for label, active in [("⌂  Project", True),("✂  Edit",False),("✦  Auto Edit",False),("▦  Scenes",False),("≡  Transcript",False),("◫  Audio",False)]:
            b=QPushButton(label); b.setObjectName("navActive" if active else "nav"); layout.addWidget(b)
        layout.addStretch(1)
        dot = QLabel(); dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if DOT_MARK.exists(): dot.setPixmap(QIcon(str(DOT_MARK)).pixmap(58,64))
        layout.addWidget(dot)
        dot_text = QLabel(".dot / KUBRICK"); dot_text.setObjectName("muted"); dot_text.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(dot_text)
        return side

    def _workspace(self) -> QWidget:
        page=QWidget(); outer=QVBoxLayout(page); outer.setContentsMargins(18,14,18,14); outer.setSpacing(10)
        outer.addWidget(self._topbar())
        split=QSplitter(Qt.Orientation.Vertical); split.addWidget(self._editor_area()); split.addWidget(self._timeline_panel()); split.setSizes([610,250]); outer.addWidget(split,1)
        return page

    def _topbar(self) -> QWidget:
        bar=QFrame(); bar.setObjectName("topbar"); row=QHBoxLayout(bar); row.setContentsMargins(12,8,12,8)
        title=QLabel("UNTITLED"); title.setObjectName("title"); self.project_title=title; row.addWidget(title); row.addSpacing(12)
        self.status=QLabel("Ready"); self.status.setObjectName("muted"); row.addWidget(self.status); row.addStretch()
        for text, slot in [("New",self._new_project),("Open",self._open_project),("Save",self._save_project),("Import",self._import_video)]:
            b=QPushButton(text); b.clicked.connect(slot); row.addWidget(b)
        self.auto=QPushButton("Auto Edit"); self.auto.setObjectName("primary"); self.auto.clicked.connect(self._auto_edit); row.addWidget(self.auto)
        self.render=QPushButton("Render"); self.render.setObjectName("primary"); self.render.clicked.connect(self._render); row.addWidget(self.render)
        return bar

    def _editor_area(self) -> QWidget:
        split=QSplitter(Qt.Orientation.Horizontal)
        center=QFrame(); c=QVBoxLayout(center); c.setContentsMargins(0,0,0,0); c.setSpacing(8)
        self.video=QVideoWidget(); c.addWidget(self.video,1)
        controls=QFrame(); cr=QHBoxLayout(controls); cr.setContentsMargins(8,5,8,5)
        self.play=QPushButton("▶"); self.play.setFixedWidth(38); self.play.clicked.connect(self._toggle_play); cr.addWidget(self.play)
        self.seek=QSlider(Qt.Orientation.Horizontal); self.seek.sliderMoved.connect(self._seek); cr.addWidget(self.seek,1)
        self.time=QLabel("00:00 / 00:00"); self.time.setObjectName("muted"); cr.addWidget(self.time); c.addWidget(controls)
        self.player=QMediaPlayer(self); self.audio=QAudioOutput(self); self.player.setAudioOutput(self.audio); self.player.setVideoOutput(self.video); self.player.positionChanged.connect(self._position_changed); self.player.durationChanged.connect(self._duration_changed); self.audio.setVolume(0.8)
        split.addWidget(center); split.addWidget(self._inspector()); split.setSizes([900,280]); return split

    def _inspector(self) -> QWidget:
        panel=QFrame(); panel.setObjectName("panel"); p=QVBoxLayout(panel); p.setContentsMargins(14,14,14,14); p.setSpacing(9)
        e=QLabel("INSPECTOR"); e.setObjectName("eyebrow"); p.addWidget(e)
        self.clip_info=QLabel("No clip selected"); self.clip_info.setObjectName("value"); self.clip_info.setWordWrap(True); p.addWidget(self.clip_info)
        p.addSpacing(8)
        preset=QLabel("AUTO PRESET"); preset.setObjectName("eyebrow"); p.addWidget(preset)
        self.preset=QComboBox(); self.preset.addItems(["clean","gentle","tight","punchy","mono-voice"]); p.addWidget(self.preset)
        p.addSpacing(8)
        tools=QLabel("LAYERS"); tools.setObjectName("eyebrow"); p.addWidget(tools)
        for text, slot in [("+ Text",self._add_text),("+ Image",self._add_image),("+ Shape",self._add_shape)]:
            b=QPushButton(text); b.setObjectName("tool"); b.clicked.connect(slot); p.addWidget(b)
        p.addSpacing(8)
        filters=QLabel("FILTER"); filters.setObjectName("eyebrow"); p.addWidget(filters)
        self.filter=QLineEdit(); self.filter.setPlaceholderText("eq=contrast=1.04:saturation=1.03"); p.addWidget(self.filter)
        fb=QPushButton("Apply to selected clip"); fb.clicked.connect(self._apply_filter); p.addWidget(fb)
        p.addStretch(1)
        self.review=QLabel("Automatic decisions remain editable. Nothing is rendered until you press Render."); self.review.setObjectName("muted"); self.review.setWordWrap(True); p.addWidget(self.review)
        return panel

    def _timeline_panel(self) -> QWidget:
        panel=QFrame(); panel.setObjectName("timeline"); p=QVBoxLayout(panel); p.setContentsMargins(10,8,10,8)
        head=QHBoxLayout(); e=QLabel("TIMELINE"); e.setObjectName("eyebrow"); head.addWidget(e); head.addStretch();
        self.cut_start=QLineEdit("0"); self.cut_start.setMaximumWidth(70); self.cut_end=QLineEdit("0"); self.cut_end.setMaximumWidth(70)
        cut=QPushButton("Cut range"); cut.clicked.connect(self._cut_range); head.addWidget(QLabel("start")); head.addWidget(self.cut_start); head.addWidget(QLabel("end")); head.addWidget(self.cut_end); head.addWidget(cut)
        p.addLayout(head)
        self.timeline=QTableWidget(0,5); self.timeline.setHorizontalHeaderLabels(["TRACK","SOURCE","START","END","DURATION"]); self.timeline.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.timeline.cellClicked.connect(self._timeline_selected); self.timeline.horizontalHeader().setStretchLastSection(True); p.addWidget(self.timeline,1)
        self.progress=QProgressBar(); self.progress.setRange(0,0); self.progress.hide(); p.addWidget(self.progress)
        return panel

    def _new_project(self) -> None:
        self.project=Project(name="Untitled"); self.source=None; self.report=None; self._refresh(); self.project_title.setText("UNTITLED"); self.status.setText("Ready")

    def _import_video(self) -> None:
        path,_=QFileDialog.getOpenFileName(self,"Import video","","Video files (*.mp4 *.mov *.mkv *.webm *.avi);;All files (*)")
        if not path: return
        self._load_source(Path(path))

    def _load_source(self, source: Path) -> None:
        try:
            from kubrick.media import probe_duration
            duration=probe_duration(source)
        except Exception as exc:
            QMessageBox.critical(self,"Kubrick",f"Could not inspect media:\n{exc}"); return
        self.source=source; self.project=Project(name=source.stem, video=[MediaClip(str(source),0,duration,0)]); self.project_title.setText(source.stem.upper()); self.player.setSource(QUrl.fromLocalFile(str(source))); self._refresh(); self.status.setText(f"Imported · {duration:.1f}s")

    def _open_project(self) -> None:
        path,_=QFileDialog.getOpenFileName(self,"Open Kubrick project","","Kubrick projects (*.kubrick.json);;JSON (*.json)")
        if not path: return
        try:
            self.project=Project.load(path); self.project_title.setText(self.project.name.upper()); self.source=Path(self.project.video[0].path) if self.project.video else None
            if self.source and self.source.exists(): self.player.setSource(QUrl.fromLocalFile(str(self.source)))
            self._refresh(); self.status.setText("Project loaded")
        except Exception as exc: QMessageBox.critical(self,"Kubrick",str(exc))

    def _save_project(self) -> None:
        if not self.project or not self.project.video: QMessageBox.warning(self,"Kubrick","Import footage first."); return
        path,_=QFileDialog.getSaveFileName(self,"Save project",f"{self.project.name}.kubrick.json","Kubrick project (*.kubrick.json)")
        if path:
            try: self.project.save(path); self.status.setText(f"Saved · {Path(path).name}")
            except Exception as exc: QMessageBox.critical(self,"Kubrick",str(exc))

    def _auto_edit(self) -> None:
        if not self.source or not self.source.exists(): QMessageBox.warning(self,"Kubrick","Import a video first."); return
        preset=get_preset(self.preset.currentText()); self.status.setText("Analyzing and building automatic edit…"); self._run(lambda: build_preset_project(self.source,preset.name),self._auto_done)

    def _auto_done(self, project: Project) -> None:
        self.project=project; self._refresh(); self.status.setText(f"Auto edit ready · {len(project.video)} timeline segments"); self.review.setText("Review the timeline before rendering. Automatic edits are represented as normal project clips.")

    def _add_text(self) -> None:
        if not self.project or not self.project.video: return
        self.project.overlays.append(Overlay("text","Your title",0,3)); self._refresh(); self.status.setText("Text layer added")

    def _add_image(self) -> None:
        if not self.project or not self.project.video: return
        path,_=QFileDialog.getOpenFileName(self,"Choose image","","Images (*.png *.jpg *.jpeg *.webp)")
        if path: self.project.overlays.append(Overlay("image",path,0,3,width=420,height=240)); self._refresh(); self.status.setText("Image layer added")

    def _add_shape(self) -> None:
        if not self.project or not self.project.video: return
        self.project.overlays.append(Overlay("shape","#d52b1e",0,2,width=420,height=120,opacity=.85)); self._refresh(); self.status.setText("Shape layer added")

    def _apply_filter(self) -> None:
        if not self.project or not self.project.video or not self.filter.text().strip(): return
        row=self.timeline.currentRow(); index=max(0,row); self.project=add_filter(self.project,self.filter.text(),index); self._refresh(); self.status.setText("Filter added non-destructively")

    def _cut_range(self) -> None:
        if not self.project or not self.project.video: return
        try: start=float(self.cut_start.text()); end=float(self.cut_end.text()); self.project=cut_range(self.project,start,end); self._refresh(); self.status.setText(f"Cut {end-start:.2f}s from timeline")
        except Exception as exc: QMessageBox.warning(self,"Kubrick",str(exc))

    def _timeline_selected(self,row:int,_col:int) -> None:
        if not self.project or row<0 or row>=len(self.project.video): return
        clip=self.project.video[row]; self.clip_info.setText(f"Video clip\n{Path(clip.path).name}\n{clip.source_start:.2f}s → {clip.source_end:.2f}s\nFilters: {len(clip.filters)}")
        self.player.setSource(QUrl.fromLocalFile(str(clip.path))); self.cut_start.setText(f"{clip.timeline_start:.2f}"); self.cut_end.setText(f"{clip.timeline_start+(clip.duration or 0):.2f}")

    def _refresh(self) -> None:
        self.timeline.setRowCount(0)
        if not self.project: return
        for clip in self.project.video:
            row=self.timeline.rowCount(); self.timeline.insertRow(row)
            values=("VIDEO",Path(clip.path).name,f"{clip.timeline_start:.2f}",f"{clip.timeline_start+(clip.duration or 0):.2f}",f"{clip.duration or 0:.2f}s")
            for col,value in enumerate(values): self.timeline.setItem(row,col,QTableWidgetItem(value))
        for audio in self.project.audio:
            row=self.timeline.rowCount(); self.timeline.insertRow(row); values=("AUDIO",Path(audio.path).name,f"{audio.timeline_start:.2f}","—","layer")
            for col,value in enumerate(values): self.timeline.setItem(row,col,QTableWidgetItem(value))
        for overlay in self.project.overlays:
            row=self.timeline.rowCount(); self.timeline.insertRow(row); values=(overlay.kind.upper(),Path(overlay.value).name if overlay.kind=="image" else overlay.value,f"{overlay.start:.2f}",f"{overlay.end or 0:.2f}","layer")
            for col,value in enumerate(values): self.timeline.setItem(row,col,QTableWidgetItem(value))

    def _run(self, fn, callback) -> None:
        self.progress.show(); self.auto.setEnabled(False); self.render.setEnabled(False)
        self._thread=QThread(self); self._worker=Worker(fn); self._worker.moveToThread(self._thread); self._thread.started.connect(self._worker.run); self._worker.finished.connect(callback); self._worker.failed.connect(self._failed); self._worker.finished.connect(self._thread.quit); self._worker.failed.connect(self._thread.quit); self._thread.finished.connect(self._idle); self._thread.start()

    def _idle(self) -> None:
        self.progress.hide(); self.auto.setEnabled(True); self.render.setEnabled(True); self._worker=None; self._thread=None

    def _failed(self,message:str) -> None:
        self.status.setText("Operation failed"); QMessageBox.critical(self,"Kubrick",message)

    def _render(self) -> None:
        if not self.project or not self.project.video: QMessageBox.warning(self,"Kubrick","Import footage first."); return
        path,_=QFileDialog.getSaveFileName(self,"Render output","kubrick_edit.mp4","MP4 video (*.mp4)")
        if not path: return
        project=self.project; self.status.setText("Rendering synchronized project…"); self._run(lambda: render_project(project,path),lambda _: self._render_done(path))

    def _render_done(self,path:str) -> None:
        self.status.setText(f"Rendered · {Path(path).name}"); QMessageBox.information(self,"Kubrick",f"Finished rendering:\n{path}")

    def _toggle_play(self) -> None:
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState: self.player.pause(); self.play.setText("▶")
        else: self.player.play(); self.play.setText("Ⅱ")

    def _seek(self,value:int) -> None: self.player.setPosition(value)
    def _position_changed(self,pos:int) -> None:
        self.seek.setValue(pos); self._update_time(pos,self.player.duration())
    def _duration_changed(self,duration:int) -> None: self.seek.setRange(0,max(0,duration)); self._update_time(self.player.position(),duration)
    def _update_time(self,pos:int,duration:int) -> None:
        def fmt(ms:int)->str:
            s=max(0,ms)//1000; return f"{s//60:02d}:{s%60:02d}"
        self.time.setText(f"{fmt(pos)} / {fmt(duration)}")


def main() -> int:
    app=QApplication(sys.argv); app.setApplicationName("Kubrick"); app.setApplicationDisplayName("Kubrick — Precision Video Editor"); app.setStyle("Fusion"); window=MainWindow(); window.show(); return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
