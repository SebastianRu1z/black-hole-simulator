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
