from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def qt_app():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
    app.quit()


def test_editor_keeps_inspector_and_resizable_timeline(qt_app) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFrame, QSplitter
    from kubrick.ui.app import MainWindow

    window = MainWindow()
    window.show()
    qt_app.processEvents()

    splitters = window.findChildren(QSplitter)
    vertical = [s for s in splitters if s.orientation() == Qt.Orientation.Vertical]
    horizontal = [s for s in splitters if s.orientation() == Qt.Orientation.Horizontal]

    assert vertical
    assert horizontal
    assert any(s.count() == 2 and s.handleWidth() >= 8 for s in vertical)
    assert any(s.count() == 2 and s.handleWidth() >= 8 for s in horizontal)
    assert window.findChild(QFrame, "panel") is not None
    assert window.findChild(QFrame, "sidebar") is not None

    window.close()
