#!/usr/bin/env python3
"""Verify direct D3D11 presentation into a native Qt widget."""

import argparse
import json
import os
import pathlib
import sys
import time


DLL_DIRECTORY_HANDLES = []


def configure_windows_dll_search():
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    configured_root = os.environ.get("OPENSHOT_INSTALL_ROOT")
    candidates = []
    if configured_root:
        candidates.append(pathlib.Path(configured_root) / "bin")
    else:
        candidates.append(repo_root / "build" / "install-x64-qt6" / "bin")
    candidates.append(pathlib.Path(sys.executable).resolve().parent)
    for candidate in candidates:
        if candidate.is_dir():
            DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(candidate)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", type=pathlib.Path)
    parser.add_argument("--frames", type=int, default=60)
    args = parser.parse_args()
    input_path = args.input_path.resolve()
    if not input_path.is_file():
        raise SystemExit("Input video not found: {}".format(input_path))

    configure_windows_dll_search()
    import openshot
    from qt_api import QtCore, QtGui, QtWidgets, Slot, unwrapinstance

    class PreviewWidget(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.fallback_frames = 0

        @Slot(QtGui.QImage)
        def present(self, _image):
            self.fallback_frames += 1

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([sys.argv[0]])
    widget = PreviewWidget()
    widget.setWindowTitle("TeachCut D3D11 presenter verification")
    widget.resize(1280, 720)
    native_window_attribute = getattr(QtCore.Qt, "WA_NativeWindow", None)
    if native_window_attribute is None:
        native_window_attribute = QtCore.Qt.WidgetAttribute.WA_NativeWindow
    widget.setAttribute(native_window_attribute, True)
    widget.show()
    app.processEvents()

    settings = openshot.Settings.Instance()
    previous = {
        "decoder": int(settings.HARDWARE_DECODER),
        "device": int(settings.HW_DE_DEVICE_SET),
        "zero_copy": bool(settings.ENABLE_D3D11_ZERO_COPY),
        "direct_present": bool(settings.ENABLE_D3D11_DIRECT_PRESENT),
    }
    reader = openshot.FFmpegReader(str(input_path), False)
    player = openshot.QtPlayer()
    frame = None
    try:
        settings.HARDWARE_DECODER = 4
        settings.HW_DE_DEVICE_SET = 0
        settings.DE_LIMIT_WIDTH_MAX = 8192
        settings.DE_LIMIT_HEIGHT_MAX = 8192
        settings.ENABLE_D3D11_ZERO_COPY = True
        settings.ENABLE_D3D11_DIRECT_PRESENT = True

        reader.Open()
        reader.ResetPerformanceMetrics()
        player.SetQWidget(int(unwrapinstance(widget)))
        player.ResetPresentationMetrics()

        frames = min(args.frames, int(reader.info.video_length))
        storage_modes = {}
        screenshot_path = input_path.parent / "d3d11-presenter-last-frame.png"
        try:
            screenshot_path.unlink()
        except FileNotFoundError:
            pass
        started = time.perf_counter()
        for frame_number in range(1, frames + 1):
            frame = reader.GetFrame(frame_number)
            mode = int(frame.StorageMode())
            storage_modes[str(mode)] = storage_modes.get(str(mode), 0) + 1
            if frame_number == frames:
                player.CaptureNextPresentation(str(screenshot_path))
            player.PresentFrame(frame)
            app.processEvents()
        elapsed = time.perf_counter() - started

        screenshot = QtGui.QImage(str(screenshot_path))
        screenshot_saved = screenshot_path.is_file() and not screenshot.isNull()
        sampled_colors = {
            int(screenshot.pixel(x, y)) & 0x00FFFFFF
            for x in range(0, screenshot.width(), max(1, screenshot.width() // 16))
            for y in range(0, screenshot.height(), max(1, screenshot.height() // 9))
        } if screenshot_saved else set()

        presentation = json.loads(player.PresentationMetricsJson())
        decoding = json.loads(reader.PerformanceMetricsJson())
        report = {
            "input": str(input_path),
            "frames": frames,
            "seconds": round(elapsed, 4),
            "frames_per_second": round(frames / elapsed, 2),
            "storage_modes": storage_modes,
            "last_frame_downloads": int(frame.GpuDownloadCount()) if frame else -1,
            "python_fallback_frames": widget.fallback_frames,
            "screenshot": str(screenshot_path) if screenshot_saved else None,
            "screenshot_size": [screenshot.width(), screenshot.height()],
            "screenshot_sampled_colors": len(sampled_colors),
            "presentation": presentation,
            "decoding": decoding,
        }
        errors = []
        if presentation.get("direct_presents") != frames:
            errors.append("not every requested frame was presented through D3D11")
        if presentation.get("fallback_presents") != 0 or widget.fallback_frames != 0:
            errors.append("the direct presenter unexpectedly used the QImage fallback")
        if presentation.get("present_failures") != 0:
            errors.append("one or more D3D11 presentations failed")
        if storage_modes.get("1") != frames:
            errors.append("not every requested frame remained GPU-only")
        if decoding.get("gpu_downloads") != 0 or decoding.get("cpu_frame_copies") != 0:
            errors.append("decode performed a GPU download or CPU image copy")
        if report["last_frame_downloads"] != 0:
            errors.append("presentation materialized the last GPU frame on the CPU")
        if not screenshot_saved or screenshot.width() <= 0 or screenshot.height() <= 0:
            errors.append("the native presenter window could not be captured")
        if len(sampled_colors) < 4 or not any(color != 0 for color in sampled_colors):
            errors.append("the captured D3D11 back buffer was blank")
        report["ok"] = not errors
        report["errors"] = errors
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if not errors else 1
    finally:
        try:
            player.SetQWidget(0)
        except Exception:
            pass
        frame = None
        reader.Close()
        widget.close()
        app.processEvents()
        settings.HARDWARE_DECODER = previous["decoder"]
        settings.HW_DE_DEVICE_SET = previous["device"]
        settings.ENABLE_D3D11_ZERO_COPY = previous["zero_copy"]
        settings.ENABLE_D3D11_DIRECT_PRESENT = previous["direct_present"]


if __name__ == "__main__":
    sys.exit(main())
