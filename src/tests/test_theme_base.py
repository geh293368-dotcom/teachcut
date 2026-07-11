"""Unit tests for theme asset loading."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch


PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if PATH not in sys.path:
    sys.path.append(PATH)

from themes.base import BaseTheme
from themes.manager import ThemeName
from themes.modern.theme import TeachCutModernTheme


class ThemeAssetTests(unittest.TestCase):
    def setUp(self):
        self.theme = BaseTheme(SimpleNamespace(devicePixelRatio=lambda: 1.0))

    def test_svg_icons_keep_high_dpi_renderer(self):
        expected = object()
        with patch.object(self.theme, "create_svg_icon", return_value=expected) as create_svg:
            result = self.theme.create_icon("toolbar/save.svg", object())

        self.assertIs(result, expected)
        create_svg.assert_called_once()

    def test_png_icons_use_qicon_loader(self):
        expected = object()
        with patch("themes.base.QIcon", return_value=expected) as qicon:
            result = self.theme.create_icon("toolbar/save.png", object())

        self.assertIs(result, expected)
        qicon.assert_called_once_with("toolbar/save.png")

    def test_raster_extension_matching_is_case_insensitive(self):
        with patch("themes.base.QIcon") as qicon:
            self.theme.create_icon("toolbar/save.PNG", object())

        qicon.assert_called_once_with("toolbar/save.PNG")

    def test_modern_theme_is_registered(self):
        self.assertEqual(ThemeName.find_by_name("TeachCut Modern"), ThemeName.TEACHCUT_MODERN)

    def test_modern_theme_replaces_cosmic_palette(self):
        theme = TeachCutModernTheme(self.theme.app)

        self.assertIn("#111820", theme.style_sheet)
        self.assertIn("#4C9AFF", theme.style_sheet)
        self.assertNotIn("#91C3FF", theme.style_sheet)


if __name__ == "__main__":
    unittest.main()
