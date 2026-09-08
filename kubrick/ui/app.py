from __future__ import annotations

import sys
from pathlib import Path

try:
    from PySide6.QtCore import QObject, QThread, Signal
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
        QLineEdit, QMainWindow, QMessageBox, QPushButton, QProgressBar,
        QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    )
except ImportError as exc:  # pragma: no cover - exercised only without optional GUI dependency
    raise RuntimeError("Install the GUI extra with: python -m pip install -e '.[gui]'") from exc

from kubrick.editor import AnalyzerConfig, analyze, render


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self) -> None:
        try:
            self.finished.emit(self.fn())
        except Exception as exc:  # UI boundary: convert worker failures into a message
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kubrick — Precision Editor")
        self.resize(980, 680)
        self.report = None
        self._thread: QThread | None = None
        self._worker: Worker | None = None

        self.input_box = QLineEdit()
        self.browse = QPushButton("Browse…")
        self.profile = QComboBox()
        self.profile.addItems(["gentle", "natural", "tight"])
        self.profile.setCurrentText("natural")
        self.noise = QLineEdit("-38")
        self.analyze_button = QPushButton("Analyze")
        self.render_button = QPushButton("Render tightened copy")
        self.render_button.setEnabled(False)
        self.status = QLabel("Choose a video to begin.")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Start", "End", "Duration", "Action", "Reason"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        browse_row = QHBoxLayout()
        browse_row.addWidget(self.input_box, 1)
        browse_row.addWidget(self.browse)

        form = QFormLayout()
        form.addRow("Source", browse_row)
        form.addRow("Profile", self.profile)
        form.addRow("Silence threshold (dB)", self.noise)

        actions = QHBoxLayout()
        actions.addWidget(self.analyze_button)
        actions.addWidget(self.render_button)
        actions.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(self.table, 1)

        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

        self.browse.clicked.connect(self._browse)
        self.analyze_button.clicked.connect(self._analyze)
        self.render_button.clicked.connect(self._render)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose video", "", "Video files (*.mp4 *.mov *.mkv *.webm *.avi);;All files (*)"
        )
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
            values = (
                f"{decision.source.start:.2f}", f"{decision.source.end:.2f}",
                f"{decision.source.duration:.2f}", decision.kind.value, decision.reason,
            )
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.status.setText(
            f"{len(report.decisions)} edits • remove {report.removed_duration:.1f}s • "
            f"output ≈ {report.output_duration:.1f}s"
        )
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
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
