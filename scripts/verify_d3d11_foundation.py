#!/usr/bin/env python3
"""Verify shared D3D11 decode surfaces and lazy CPU materialization."""

import argparse
import hashlib
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
    candidates = (
        repo_root / "build" / "install-x64" / "bin",
        pathlib.Path(sys.executable).resolve().parent,
    )
    for candidate in candidates:
        if candidate.is_dir():
            DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(candidate)))


def run_decode(openshot, input_path, frame_count, zero_copy):
    settings = openshot.Settings.Instance()
    settings.HARDWARE_DECODER = 4
    settings.HW_DE_DEVICE_SET = 0
    settings.DE_LIMIT_WIDTH_MAX = 8192
    settings.DE_LIMIT_HEIGHT_MAX = 8192
    settings.ENABLE_D3D11_ZERO_COPY = bool(zero_copy)

    reader = openshot.FFmpegReader(str(input_path), False)
    last_frame = None
    gpu_frame_for_materialization = None
    storage_modes = {}
    try:
        reader.Open()
        reader.ResetPerformanceMetrics()
        frames = min(frame_count, int(reader.info.video_length))
        started = time.perf_counter()
        for frame_number in range(1, frames + 1):
            last_frame = reader.GetFrame(frame_number)
            mode = int(last_frame.StorageMode())
            storage_modes[str(mode)] = storage_modes.get(str(mode), 0) + 1
            if mode == 1:
                gpu_frame_for_materialization = last_frame
        elapsed = time.perf_counter() - started
        metrics = json.loads(reader.PerformanceMetricsJson())

        materialized = None
        pixel_sha256 = None
        if zero_copy and gpu_frame_for_materialization is not None:
            before = int(gpu_frame_for_materialization.StorageMode())
            pixels = gpu_frame_for_materialization.GetPixelsBytes()
            after = int(gpu_frame_for_materialization.StorageMode())
            materialized = {
                "before": before,
                "after": after,
                "pixel_bytes": len(pixels) if pixels else 0,
                "download_count": int(gpu_frame_for_materialization.GpuDownloadCount()),
                "download_ms": round(gpu_frame_for_materialization.GpuDownloadNanoseconds() / 1_000_000.0, 3),
            }
            pixel_sha256 = hashlib.sha256(pixels).hexdigest() if pixels else None
        elif last_frame is not None:
            pixels = last_frame.GetPixelsBytes()
            pixel_sha256 = hashlib.sha256(pixels).hexdigest() if pixels else None

        return {
            "zero_copy": bool(zero_copy),
            "frames": frames,
            "seconds": round(elapsed, 4),
            "frames_per_second": round(frames / elapsed, 2),
            "hardware_success": bool(reader.HardwareDecodeSuccessful()),
            "storage_modes": storage_modes,
            "metrics": metrics,
            "materialized": materialized,
            "pixel_sha256": pixel_sha256,
        }
    finally:
        reader.Close()


def validate(report):
    baseline = report["materialized_d3d11"]
    zero_copy = report["zero_copy_d3d11"]
    errors = []
    if not baseline["hardware_success"] or not zero_copy["hardware_success"]:
        errors.append("D3D11 hardware decode did not succeed in both runs")
    if not zero_copy["metrics"].get("shared_d3d11_device"):
        errors.append("the shared D3D11 device was not active")
    if baseline["metrics"].get("gpu_downloads", 0) <= 0:
        errors.append("the baseline did not record immediate GPU downloads")
    if baseline["metrics"].get("cpu_frame_copies", 0) <= 0:
        errors.append("the baseline did not record CPU frame copies")
    if zero_copy["metrics"].get("gpu_frames_retained", 0) <= 0:
        errors.append("the zero-copy run did not retain GPU frames")
    if zero_copy["metrics"].get("gpu_downloads", 0) != 0:
        errors.append("the zero-copy reader performed an eager GPU download")
    if zero_copy["storage_modes"].get("1", 0) <= 0:
        errors.append("the zero-copy run returned no D3D11-backed Frame objects")
    materialized = zero_copy.get("materialized") or {}
    if materialized.get("before") != 1 or materialized.get("after") != 2:
        errors.append("the final frame did not transition from GPU-only to materialized")
    if materialized.get("pixel_bytes", 0) <= 0 or materialized.get("download_count") != 1:
        errors.append("lazy CPU materialization did not return pixels exactly once")
    if not baseline.get("pixel_sha256") or baseline.get("pixel_sha256") != zero_copy.get("pixel_sha256"):
        errors.append("lazy D3D11 materialization did not match the baseline RGBA pixels")
    return errors


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

    settings = openshot.Settings.Instance()
    previous_zero_copy = bool(settings.ENABLE_D3D11_ZERO_COPY)
    try:
        report = {
            "input": str(input_path),
            "materialized_d3d11": run_decode(openshot, input_path, args.frames, False),
            "zero_copy_d3d11": run_decode(openshot, input_path, args.frames, True),
        }
    finally:
        settings.ENABLE_D3D11_ZERO_COPY = previous_zero_copy

    errors = validate(report)
    report["ok"] = not errors
    report["errors"] = errors
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
