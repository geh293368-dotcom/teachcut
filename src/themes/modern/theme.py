"""Modern, low-risk skin for the existing OpenShot widget layout."""

import re
import sys

from themes.cosmic.theme import CosmicTheme


class TeachCutModernTheme(CosmicTheme):
    """Preserve every UI element while modernizing typography and surfaces."""

    _COLOR_REPLACEMENTS = {
        "#192332": "#111820",
        "#141923": "#0D131A",
        "#283241": "#1B242E",
        "#323C50": "#263241",
        "#91C3FF": "#E6EDF3",
        "rgba(145, 195, 255, 0.4)": "rgba(154, 168, 182, 0.72)",
        "rgba(145, 195, 255, 1.0)": "rgba(230, 237, 243, 1.0)",
        "#9BB2CC": "#9AA8B6",
        "#0078FF": "#4C9AFF",
        "#006EE6": "#3D8EE6",
        "#0A82FF": "#5AA7FF",
        "#53A0ED": "#4C9AFF",
        "#5AA2E6": "#70B7FF",
        "#FABE0A": "#F2C94C",
    }

    def __init__(self, app):
        super().__init__(app)

        for old_color, new_color in self._COLOR_REPLACEMENTS.items():
            self.style_sheet = re.sub(
                re.escape(old_color),
                new_color,
                self.style_sheet,
                flags=re.IGNORECASE,
            )

        self.style_sheet += """
QMainWindow, QDialog {
    color: #E6EDF3;
}

QMenuBar {
    padding: 2px 8px;
    border-bottom: 1px solid #263241;
}

QMenuBar::item {
    padding: 6px 10px;
    border-radius: 4px;
}

QToolBar#toolBar {
    min-height: 44px;
    border-bottom: 1px solid #263241;
}

QToolBar#toolBar QToolButton {
    padding: 8px 10px;
    margin: 3px 1px;
    border-radius: 5px;
}

QDockWidget QWidget#dockFilesContents,
QWidget#dockTransitionsContents,
QWidget#dockEmojisContents,
QWidget#dockEffectsContents,
QWidget#dockCaptionContents,
QWidget#dockVideoContents,
QWidget#dockPropertiesContents {
    border: 1px solid #263241;
    border-radius: 6px;
}

QTabBar::tab {
    min-height: 22px;
    margin-top: 10px;
    margin-left: 12px;
    padding: 4px 1px 6px 1px;
}

QTabBar::tab:selected,
QTabBar::tab:focus {
    border-bottom: 2px solid #4C9AFF;
}

QLineEdit,
QTextEdit,
QPlainTextEdit,
QSpinBox,
QDoubleSpinBox,
QComboBox {
    min-height: 28px;
    border: 1px solid #334150;
    border-radius: 5px;
    selection-background-color: #4C9AFF;
}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QComboBox:focus {
    border: 1px solid #70B7FF;
}

QPushButton {
    min-height: 28px;
    border: 1px solid #334150;
    border-radius: 5px;
}

QScrollBar:vertical {
    width: 10px;
}

QScrollBar:horizontal {
    height: 10px;
}

QToolTip {
    color: #E6EDF3;
    background-color: #1B242E;
    border: 1px solid #3B4A5A;
    padding: 5px 7px;
}
        """

    def create_application_font(self):
        from qt_api import QFont

        family = "Microsoft YaHei UI" if sys.platform == "win32" else "Noto Sans"
        font = QFont(family)
        font.setPointSizeF(9.0)
        return font

    def create_timeline_theme(self):
        from .styles import TeachCutModernTimelineTheme

        return TeachCutModernTimelineTheme()
