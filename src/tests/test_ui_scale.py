"""Tests for deterministic application UI scale resolution."""

import json
import os
import sys
import unittest
from unittest import mock


PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if PATH not in sys.path:
    sys.path.append(PATH)

from classes.ui_scale import resolve_ui_scale


class UiScaleTests(unittest.TestCase):
    def mock_settings(self, value):
        content = json.dumps([{"setting": "ui-scale", "value": value}])
        file_mock = mock.mock_open(read_data=content)
        return (
            mock.patch("classes.ui_scale.os.path.exists", return_value=True),
            mock.patch("classes.ui_scale.open", file_mock),
            file_mock,
        )

    def test_defaults_to_100_percent_without_settings(self):
        self.assertEqual(resolve_ui_scale("missing.settings", environ={}), 1.0)

    def test_reads_user_scale(self):
        exists_mock, open_mock, _ = self.mock_settings(1.2)
        with exists_mock, open_mock:
            self.assertEqual(resolve_ui_scale("openshot.settings", environ={}), 1.2)

    def test_process_override_wins_without_modifying_settings(self):
        exists_mock, open_patch, file_mock = self.mock_settings(1.2)
        with exists_mock, open_patch:
            self.assertEqual(
                resolve_ui_scale(
                    "openshot.settings",
                    environ={"OPENSHOT_UI_SCALE": "1.0"},
                ),
                1.0,
            )
        file_mock.assert_not_called()

    def test_values_are_clamped_to_supported_range(self):
        self.assertEqual(
            resolve_ui_scale("missing.settings", environ={"OPENSHOT_UI_SCALE": "9"}),
            3.0,
        )

    def test_invalid_override_falls_back_to_user_scale(self):
        exists_mock, open_mock, _ = self.mock_settings(1.25)
        with exists_mock, open_mock:
            self.assertEqual(
                resolve_ui_scale(
                    "openshot.settings",
                    environ={"OPENSHOT_UI_SCALE": "invalid"},
                ),
                1.25,
            )


if __name__ == "__main__":
    unittest.main()
