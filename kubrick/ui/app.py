from __future__ import annotations

import sys
from pathlib import Path

try:
    from PySide6.QtCore import QObject, QThread, Qt, Signal
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QFileDialog, QFrame, QFormLayout, QHBoxLayout,
        QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QProgressBar,
        QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Install the GUI extra with: python -m pip install -e '.[gui]'") from exc

from kubrick.editor import AnalyzerConfig, analyze, render


APP_DIR = Path(__file__).resolve().parent
MARK = APP_DIR / "kubrick-mark.svg"

STYLESHEET = """
* { font-family: Inter, Segoe UI, Arial, sans-serif; }
QMainWindow, QWidget { background: #0a0a0a; color: #eee9e2; }
QFrame#sidebar { background: #0d0d0d; border-right: 1px solid #242424; }
QFrame#card { background: #111111; border: 1px solid #282828; border-radius: 14px; }
QLabel#brand { color: #f1eee8; font-size: 20px; font-weight: 700; letter-spacing: 5px; }
QLabel#eyebrow { color: #8d8984; font-size: 10px; letter-spacing: 3px; }
QLabel#hero { color: #f3efe9; font-size: 32px; font-weight: 700; }
QLabel#subtitle { color: #9b9690; font-size: 13px; line-height: 1.5; }
QLabel#section { color: #f0ece6; font-size: 16px; font-weight: 600; }
QLabel#muted { color: #77736e; font-size: 11px; }
QLineEdit, QComboBox { background: #0c0c0c; color: #eee9e2; border: 1px solid #303030; border-radius: 8px; padding: 9px 11px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #d52b1e; }
QPushButton { background: #191919; color: #eee9e2; border: 1px solid #353535; border-radius: 8px; padding: 10px 16px; font-weight: 600; }
QPushButton:hover { background: #232323; border-color: #555; }
QPushButton#primary { background: #c9281d; border: 1px solid #e04438; color: white; padding: 12px 20px; }
QPushButton#primary:hover { background: #dc3024; }
QPushButton#nav { text-align: left; background: transparent; border: 0; color: #8e8983; padding: 11px 13px; }
QPushButton#nav:hover, QPushButton#navActive { background: #251311; color: #f2eee7; border-left: 2px solid #d52b1e; }
QProgressBar { border: 0; background: #181818; border-radius: 3px; height: 5px; }
QProgressBar::chunk { background: #d52b1e; border-radius: 3px; }
QTableWidget { background: #0d0d0d; border: 1px solid #282828; border-radius: 10px; gridline-color: #202020; }
QHeaderView::section { background: #121212; color: #8e8983; border: 0; border-bottom: 1px solid #292929; padding: 9px; font-size: 10px; }
QTableWidget::item { padding: 8px; color: #d7d2cb; }
QTableWidget::item:selected { background: #2b1513; color: white; }
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
        self.setWindowTitle("KUBRICK — Precision Video Editor")
        self.setMinimumSize(1100, 720)
        self.resize(1240, 780)
        self.setStyleSheet(STYLESHEET)
        if MARK.exists():
            self.setWindowIcon(QIcon(str(MARK)))
        self.report = None
        self._thread: QThread | None = None
        self._worker: Worker | None = None
        self._build()

    def _build(self) -> None:
        shell = QHBoxLayout()
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._sidebar())
        shell.addWidget(self._content(), 1)
        root = QWidget()
        root.setLayout(shell)
        self.setCentralWidget(root)

    def _sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(220)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(6)

        brand_row = QHBoxLayout()
        if MARK.exists():
            mark = QLabel()
            mark.setPixmap(QIcon(str(MARK)).pixmap(30, 30))
            brand_row.addWidget(mark)
        brand = QLabel("KUBRICK")
        brand.setObjectName("brand")
        brand_row.addWidget(brand)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        tagline = QLabel("CUT THE NOISE.\nREVEAL THE STORY.")
        tagline.setObjectName("eyebrow")
        tagline.setContentsMargins(4, 10, 4, 24)
        layout.addWidget(tagline)

        for label, active in [("⌂  Home", True), ("✂  Edit Video", False), ("≡  Transcription", False),
                              ("✦  Auto Edit", False), ("▣  Scene Detect", False), ("◫  Enhance Audio", False),
                              ("↥  Export", False)]:
            button = QPushButton(label)
            button.setObjectName("navActive" if active else "nav")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)

        layout.addStretch(1)
        for label in ("⚙  Settings", "?  Help"):
            button = QPushButton(label)
            button.setObjectName("nav")
            layout.addWidget(button)
        quote = QLabel('“A film is, or should be,\nmore like music than fiction.”\n\n— Stanley Kubrick')
        quote.setObjectName("muted")
        quote.setWordWrap(True)
        quote.setContentsMargins(4, 18, 4, 4)
        layout.addWidget(quote)
        return side

    def _content(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(18)

        eyebrow = QLabel("PRECISION VIDEO EDITING")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)
        hero = QLabel("Make every second earn its place.")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        subtitle = QLabel("Kubrick finds dead air and editorial friction in real footage,\nthen builds a conservative, synchronized edit you can inspect before rendering.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        source_card = QFrame()
        source_card.setObjectName("card")
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(18, 16, 18, 16)
        source_title = QLabel("SOURCE")
        source_title.setObjectName("eyebrow")
        source_layout.addWidget(source_title)
        browse_row = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Drop or choose a video file…")
        self.browse = QPushButton("Browse")
        self.browse.clicked.connect(self._browse)
        browse_row.addWidget(self.input_box, 1)
        browse_row.addWidget(self.browse)
        source_layout.addLayout(browse_row)
        layout.addWidget(source_card)

        controls = QFrame()
        controls.setObjectName("card")
        form = QFormLayout(controls)
        form.setContentsMargins(18, 14, 18, 14)
        form.setHorizontalSpacing(28)
        self.profile = QComboBox()
        self.profile.addItems(["gentle", "natural", "tight"])
        self.profile.setCurrentText("natural")
        self.noise = QLineEdit("-38")
        form.addRow("Editing profile", self.profile)
        form.addRow("Silence threshold (dB)", self.noise)
        actions = QHBoxLayout()
        self.analyze_button = QPushButton("Analyze footage")
        self.analyze_button.setObjectName("primary")
        self.render_button = QPushButton("Render tightened copy")
        self.render_button.setEnabled(False)
        self.analyze_button.clicked.connect(self._analyze)
        self.render_button.clicked.connect(self._render)
        actions.addWidget(self.analyze_button)
        actions.addWidget(self.render_button)
        actions.addStretch(1)
        form.addRow("", actions)
        layout.addWidget(controls)

        result_head = QHBoxLayout()
        title = QLabel("Editorial decisions")
        title.setObjectName("section")
        result_head.addWidget(title)
        result_head.addStretch(1)
        self.status = QLabel("Choose a video to begin.")
        self.status.setObjectName("muted")
        result_head.addWidget(self.status)
        layout.addLayout(result_head)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Start", "End", "Duration", "Action", "Reason"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(False)
        layout.addWidget(self.table, 1)
        return page

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose video", "", "Video files (*.mp4 *.mov *.mkv *.webm *.avi);;All files (*)")
        if path:
            self.input_box.setText(path)

    def _set_busy(self, busy: bool) -> None:
        self.progress.setVisible(busy)
        self.analyze_button.setEnabled(not busy)
        self.render_button.setEnabled(not busy and self.report is not None)
        self.browse.setEnabled(not busy)

    def _run(self, fn, callback) -> None:
        self._set_busy(True)
        self._thread = QThread(self)
        self._worker = Worker(fn)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(callback)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._set_idle)
        self._thread.start()

    def _set_idle(self) -> None:
        self._set_busy(False)
        self._worker = None
        self._thread = None

    def _failed(self, message: str) -> None:
        self.status.setText("Operation failed.")
        QMessageBox.critical(self, "Kubrick", message)

    def _config(self) -> AnalyzerConfig:
        return AnalyzerConfig(self.profile.currentText(), float(self.noise.text()))

    def _analyze(self) -> None:
        source = Path(self.input_box.text().strip())
        if not source.is_file():
            QMessageBox.warning(self, "Kubrick", "Choose a valid video file first.")
            return
        self.status.setText("Analyzing audio evidence…")
        self._run(lambda: analyze(source, self._config()), self._analysis_done)

    def _analysis_done(self, report) -> None:
        self.report = report
        self.table.setRowCount(len(report.decisions))
        for row, decision in enumerate(report.decisions):
            values = (f"{decision.source.start:.2f}", f"{decision.source.end:.2f}", f"{decision.source.duration:.2f}", decision.kind.value, decision.reason)
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.status.setText(f"{len(report.decisions)} edits  •  remove {report.removed_duration:.1f}s  •  output ≈ {report.output_duration:.1f}s")
        self.render_button.setEnabled(True)

    def _render(self) -> None:
        source = Path(self.input_box.text().strip())
        target, _ = QFileDialog.getSaveFileName(self, "Render output", "kubrick_edit.mp4", "MP4 video (*.mp4)")
        if not target:
            return
        self.status.setText("Rendering synchronized edit…")
        self._run(lambda: render(source, target, self._config()), lambda _: self._render_done(target))

    def _render_done(self, target: str) -> None:
        self.status.setText(f"Rendered: {target}")
        QMessageBox.information(self, "Kubrick", f"Finished rendering:\n{target}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Kubrick")
    app.setApplicationDisplayName("Kubrick — Precision Video Editor")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
