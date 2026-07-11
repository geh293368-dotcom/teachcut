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
        try:
            settings.ENABLE_D3D11_ZERO_COPY = True
            self.assertTrue(settings.ENABLE_D3D11_ZERO_COPY)
            settings.ENABLE_D3D11_ZERO_COPY = False
            self.assertFalse(settings.ENABLE_D3D11_ZERO_COPY)
        finally:
            settings.ENABLE_D3D11_ZERO_COPY = previous

    def test_reader_exposes_performance_metrics(self):
        self.assertTrue(hasattr(openshot.FFmpegReader, "PerformanceMetricsJson"))
        self.assertTrue(hasattr(openshot.FFmpegReader, "ResetPerformanceMetrics"))
