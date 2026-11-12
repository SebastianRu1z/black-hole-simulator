"""Application start-up."""

import sys
from collections.abc import Sequence

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from bhlab.ui.main_window import MainWindow
from bhlab.ui.theme import apply_theme

APPLICATION_NAME = "Black Hole Physics Lab"


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    """Return the themed QApplication, creating it on first use."""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName(APPLICATION_NAME)
    apply_theme(app)
    return app


def run(argv: Sequence[str] | None = None, *, quit_after_ms: int | None = None) -> int:
    """Open the main window and run until it is closed. Returns the exit code.

    ``quit_after_ms`` closes the application by itself after that many milliseconds. The
    automated start-up test uses it; normal use leaves it as None.
    """
    app = create_application(argv)
    window = MainWindow()
    window.show()
    if quit_after_ms is not None:
        QTimer.singleShot(quit_after_ms, app.quit)
    return app.exec()


def main() -> int:
    """Entry point used by ``python -m bhlab``."""
    return run(sys.argv)
