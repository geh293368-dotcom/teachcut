"""Cross-platform validation for TeachCut NVIDIA export presets."""

import os
import sys
import unittest
from xml.dom import minidom


PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if PATH not in sys.path:
    sys.path.append(PATH)


class NvidiaPresetTests(unittest.TestCase):
    def _load(self, filename):
        return minidom.parse(os.path.join(PATH, "presets", filename))

    @staticmethod
    def _text(document, tag):
        return document.getElementsByTagName(tag)[0].childNodes[0].data

    def test_nvidia_mp4_presets_use_expected_codecs(self):
        expected = {
            "format_mp4_hevc_nv.xml": "hevc_nvenc",
            "format_mp4_av1_nv.xml": "av1_nvenc",
            "youtube_4K_nv.xml": "h264_nvenc",
        }
        for filename, codec in expected.items():
            with self.subTest(filename=filename):
                document = self._load(filename)
                self.assertEqual(self._text(document, "videoformat"), "mp4")
                self.assertEqual(self._text(document, "videocodec"), codec)
                self.assertEqual(self._text(document, "audiocodec"), "aac")

    def test_youtube_nvidia_preset_is_limited_to_4k_profiles(self):
        document = self._load("youtube_4K_nv.xml")
        profiles = [node.childNodes[0].data for node in document.getElementsByTagName("projectprofile")]
        self.assertEqual(len(profiles), 8)
        self.assertTrue(all(profile.startswith("4K UHD 2160p") for profile in profiles))
        self.assertEqual(self._text(document, "title"), "YouTube (4K NVIDIA)")


if __name__ == "__main__":
    unittest.main()
