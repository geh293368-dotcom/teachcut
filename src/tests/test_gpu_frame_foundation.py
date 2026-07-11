import json
import unittest

import openshot


class GpuFrameFoundationTests(unittest.TestCase):
    def test_regular_frame_defaults_to_cpu_storage(self):
        frame = openshot.Frame(1, 16, 9, "#000000")
        self.assertEqual(int(frame.StorageMode()), 0)
        self.assertFalse(frame.HasGpuSurface())
        self.assertEqual(frame.GpuDownloadCount(), 0)
        self.assertEqual(frame.GpuDownloadNanoseconds(), 0)

    def test_zero_copy_switch_is_available_and_reversible(self):
        settings = openshot.Settings.Instance()
        previous = bool(settings.ENABLE_D3D11_ZERO_COPY)
        previous_present = bool(settings.ENABLE_D3D11_DIRECT_PRESENT)
        try:
            settings.ENABLE_D3D11_ZERO_COPY = True
            self.assertTrue(settings.ENABLE_D3D11_ZERO_COPY)
            settings.ENABLE_D3D11_DIRECT_PRESENT = True
            self.assertTrue(settings.ENABLE_D3D11_DIRECT_PRESENT)
            settings.ENABLE_D3D11_ZERO_COPY = False
            self.assertFalse(settings.ENABLE_D3D11_ZERO_COPY)
            settings.ENABLE_D3D11_DIRECT_PRESENT = False
            self.assertFalse(settings.ENABLE_D3D11_DIRECT_PRESENT)
        finally:
            settings.ENABLE_D3D11_ZERO_COPY = previous
            settings.ENABLE_D3D11_DIRECT_PRESENT = previous_present

    def test_reader_exposes_performance_metrics(self):
        self.assertTrue(hasattr(openshot.FFmpegReader, "PerformanceMetricsJson"))
        self.assertTrue(hasattr(openshot.FFmpegReader, "ResetPerformanceMetrics"))

    def test_player_exposes_direct_presentation_probe(self):
        self.assertTrue(hasattr(openshot.QtPlayer, "PresentFrame"))
        self.assertTrue(hasattr(openshot.QtPlayer, "PresentationMetricsJson"))
        self.assertTrue(hasattr(openshot.QtPlayer, "ResetPresentationMetrics"))
        self.assertTrue(hasattr(openshot.QtPlayer, "CaptureNextPresentation"))
