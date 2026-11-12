"""The dark scientific theme: colours, fonts and the Qt style sheet."""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

BACKGROUND = "#0b0e14"
PANEL = "#111620"
CARD = "#161c29"
BORDER = "#283044"
TEXT = "#e9ecf2"
MUTED = "#8e97ab"
ORANGE = "#ff9d3c"
BLUE = "#4cc2ff"
PURPLE = "#b79cff"
ERROR = "#ff6b6b"

_PALETTE = {
    "BACKGROUND": BACKGROUND,
    "PANEL": PANEL,
    "CARD": CARD,
    "BORDER": BORDER,
    "TEXT": TEXT,
    "MUTED": MUTED,
    "ORANGE": ORANGE,
    "BLUE": BLUE,
    "PURPLE": PURPLE,
    "ERROR": ERROR,
}

# Colours are written as @NAME and substituted below, so the sheet stays readable.
_STYLE_TEMPLATE = """
QMainWindow, QWidget#viewPanel { background: @BACKGROUND; }
QMainWindow::separator { width: 0px; height: 0px; }
QWidget { color: @TEXT; }
QLabel { background: transparent; }

QFrame#controlPanel { background: @PANEL; border: none; border-right: 1px solid @BORDER; }
QFrame#infoPanel { background: @PANEL; border: none; border-left: 1px solid @BORDER; }
QFrame#rowSeparator { background: @BORDER; border: none; min-height: 1px; max-height: 1px; }

QLabel#pageSubtitle { color: @MUTED; font-size: 10pt; }
QLabel#sectionLabel { color: @ORANGE; font-size: 8.5pt; font-weight: 700; }
QLabel#fieldLabel { font-size: 10.5pt; font-weight: 600; }
QLabel#quantityName { font-size: 10.5pt; }
QLabel#formula {
    color: @PURPLE; font-family: "Cambria", "Times New Roman", serif; font-size: 12pt;
}
QLabel#valueSi, QLabel#valueConvenient { font-size: 11pt; font-weight: 600; }
QLabel#valueSi { color: @ORANGE; }
QLabel#valueConvenient { color: @BLUE; }
QLabel#unitLabel { color: @MUTED; font-size: 12pt; }
QLabel#note, QLabel#sliderEnd, QLabel#helperLabel, QLabel#viewCaption { color: @MUTED; }
QLabel#sliderEnd { font-size: 8.5pt; }
QLabel#helperLabel[error="true"] { color: @ERROR; }
QLabel#scaleBarLabel { color: @TEXT; font-size: 9.5pt; }

QCheckBox { spacing: 9px; }
QCheckBox::indicator {
    width: 13px; height: 13px; border: 1px solid @MUTED; border-radius: 3px;
    background: @BACKGROUND;
}
QCheckBox::indicator:checked { background: @ORANGE; border: 1px solid @ORANGE; }
QCheckBox::indicator:hover { border: 1px solid @TEXT; }

QLineEdit {
    background: @BACKGROUND; border: 1px solid @BORDER; border-radius: 6px;
    padding: 7px 9px; font-size: 12pt;
    selection-background-color: @BLUE; selection-color: @BACKGROUND;
}
QLineEdit:focus { border: 1px solid @BLUE; }
QLineEdit[invalid="true"] { border: 1px solid @ERROR; }

QPushButton {
    background: @CARD; border: 1px solid @BORDER; border-radius: 6px;
    padding: 8px 10px; text-align: left;
}
QPushButton:hover { border: 1px solid @MUTED; }
QPushButton:pressed { background: @BORDER; }
QPushButton:checked { border: 1px solid @ORANGE; color: @ORANGE; }
QPushButton#viewButton { padding: 4px 12px; text-align: center; min-width: 14px; }

QSlider::groove:horizontal { height: 4px; background: @BORDER; border-radius: 2px; }
QSlider::sub-page:horizontal { background: @ORANGE; border-radius: 2px; }
QSlider::handle:horizontal {
    background: @ORANGE; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: @TEXT; }

QStatusBar { background: @PANEL; border-top: 1px solid @BORDER; }
QStatusBar::item { border: none; }
QStatusBar QLabel { color: @MUTED; font-size: 9pt; padding: 2px 8px; }

QToolTip { background: @CARD; color: @TEXT; border: 1px solid @BORDER; padding: 6px; }
"""


def style_sheet() -> str:
    """Return the Qt style sheet with the palette substituted in."""
    sheet = _STYLE_TEMPLATE
    for name, colour in _PALETTE.items():
        sheet = sheet.replace(f"@{name}", colour)
    return sheet


def apply_theme(app: QApplication) -> None:
    """Give the whole application the dark theme."""
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(style_sheet())
