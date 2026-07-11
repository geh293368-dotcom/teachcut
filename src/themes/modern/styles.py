"""Timeline paint theme for TeachCut Modern."""

from qt_api import QColor

from themes.cosmic.styles import CosmicDuskTimelineTheme


class TeachCutModernTimelineTheme(CosmicDuskTimelineTheme):
    """Neutral graphite timeline with one restrained blue accent."""

    def __init__(self):
        super().__init__()

        self.background = QColor("#0D131A")
        self.ruler_name_background = QColor("#0D131A")
        self.scrollbar_track = QColor("#0D131A")
        self.ruler.background = QColor("#0D131A")

        self.clip.background = QColor("#161E27")
        self.clip.border_color = QColor("#4C9AFF")
        self.clip.border_radius = 6

        self.track.background = QColor("#1B242E")
        self.track.border_color = QColor("#263241")
        self.track.name_background = QColor("#111820")
        self.track.name_border_color = QColor("#4C9AFF")
        self.track.name_border_top_color = QColor("#0D131A")
        self.track.name_border_bottom_color = QColor("#0D131A")
