"""Small actions shared by the interface tests: do what a user's hands would do."""

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


def type_mass(window, text, *, press_enter=True):
    """Replace the content of the mass field by typing, as a user would."""
    edit = window.controls.mass_edit
    edit.setFocus()
    edit.selectAll()
    QTest.keyClick(edit, Qt.Key.Key_Delete)
    QTest.keyClicks(edit, text)
    if press_enter:
        QTest.keyClick(edit, Qt.Key.Key_Return)


def click(button):
    """Click a button with the left mouse button."""
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
