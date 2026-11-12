"""Shared test configuration.

Interface tests run on Qt's "offscreen" platform: they need no display and never open a
window on screen. The variable must be set before Qt is first imported.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """The single QApplication shared by all interface tests."""
    from bhlab.ui.app import create_application

    return create_application([])


@pytest.fixture
def window(qapp):
    """A freshly opened main window, laid out and ready to be driven."""
    from bhlab.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    qapp.processEvents()
    yield window
    window.close()
