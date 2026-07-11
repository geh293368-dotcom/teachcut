#!/usr/bin/env python3
"""Benchmark libopenshot 4K decode and export paths on Windows."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time


DECODE_MODES = (
    ("cpu", 0),
    ("nvdec", 2),
    ("d3d11", 4),
)
ENCODE_CODECS = (
    "libx264",
    "h264_nvenc",
    "hevc_nvenc",
    "av1_nvenc",
)


def configure_runtime(repo_root, install_root):
    native_bin = install_root / "bin"
    mingw_bin = Path(sys.executable).resolve().parent
    if hasattr(os, "add_dll_directory"):
        for dll_dir in (native_bin, mingw_bin):
            os.add_dll_directory(str(dll_dir))
    sys.path[:0] = [str(install_root / "python"), str(repo_root / "src")]


def gpu_details():
    command = [
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(command, text=True, timeout=10).strip()
        name, driver, memory_mib = [part.strip() for part in output.splitlines()[0].split(",")]
        return {
            "name": name,
            "driver": driver,
            "memory_mib": int(memory_mib),
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def media_details(openshot, input_path):
    reader = openshot.FFmpegReader(str(input_path))
    try:
        reader.Open()
        info = reader.info
        return {
            "path": str(input_path),
            "width": int(info.width),
            "height": int(info.height),
            "fps": {
                "num": int(info.fps.num),
                "den": int(info.fps.den),
            },
            "video_length": int(info.video_length),
            "duration_seconds": float(info.duration),
            "video_codec": str(info.vcodec),
            "file_size_bytes": input_path.stat().st_size,
        }
    finally:
        reader.Close()


def benchmark_decode(openshot, input_path, frame_count, mode_name, mode_value, repeats):
    settings = openshot.Settings.Instance()
    settings.HARDWARE_DECODER = mode_value
    settings.HW_DE_DEVICE_SET = 0
    settings.DE_LIMIT_WIDTH_MAX = 8192
    settings.DE_LIMIT_HEIGHT_MAX = 8192

    elapsed_samples = []
    hardware_samples = []
    frames = 0
    source_fps = 0.0
    for _ in range(max(1, repeats)):
        reader = openshot.FFmpegReader(str(input_path))
        try:
            reader.Open()
            frames = min(frame_count, int(reader.info.video_length))
            source_fps = float(reader.info.fps.num) / float(reader.info.fps.den)
            started = time.perf_counter()
            for frame_number in range(1, frames + 1):
                reader.GetFrame(frame_number)
            elapsed_samples.append(time.perf_counter() - started)
            hardware_samples.append(bool(reader.HardwareDecodeSuccessful()))
        finally:
            reader.Close()
    elapsed = statistics.median(elapsed_samples)
    return {
        "mode": mode_name,
        "frames": frames,
        "repeats": len(elapsed_samples),
        "seconds": round(elapsed, 4),
        "sample_seconds": [round(sample, 4) for sample in elapsed_samples],
        "frames_per_second": round(frames / elapsed, 2),
        "realtime_multiple": round((frames / elapsed) / source_fps, 2),
        "hardware_success": all(hardware_samples),
    }


def benchmark_encode(openshot, input_path, output_dir, frame_count, codec, bitrate, decode_mode):
    if not openshot.FFmpegWriter.IsValidCodec(codec):
        return {"codec": codec, "available": False}

    settings = openshot.Settings.Instance()
    settings.HARDWARE_DECODER = decode_mode
    settings.HW_DE_DEVICE_SET = 0
    settings.HW_EN_DEVICE_SET = 0
    settings.DE_LIMIT_WIDTH_MAX = 8192
    settings.DE_LIMIT_HEIGHT_MAX = 8192

    output_path = output_dir / "encode-{}.mp4".format(codec)
    output_path.unlink(missing_ok=True)
    reader = openshot.FFmpegReader(str(input_path))
    writer = None
    try:
        reader.Open()
        frames = min(frame_count, int(reader.info.video_length))
        writer = openshot.FFmpegWriter(str(output_path))
        writer.SetVideoOptions(
            True,
            codec,
            openshot.Fraction(int(reader.info.fps.num), int(reader.info.fps.den)),
            int(reader.info.width),
            int(reader.info.height),
            openshot.Fraction(1, 1),
            False,
            False,
            bitrate,
        )
        writer.PrepareStreams()
        writer.SetOption(openshot.VIDEO_STREAM, "muxing_preset", "mp4_faststart")
        writer.Open()
        started = time.perf_counter()
        for frame_number in range(1, frames + 1):
            writer.WriteFrame(reader.GetFrame(frame_number))
        writer.Close()
        writer = None
        elapsed = time.perf_counter() - started
        source_fps = float(reader.info.fps.num) / float(reader.info.fps.den)
        return {
            "codec": codec,
            "available": True,
            "frames": frames,
            "seconds": round(elapsed, 4),
            "frames_per_second": round(frames / elapsed, 2),
            "realtime_multiple": round((frames / elapsed) / source_fps, 2),
            "decode_mode": next(name for name, value in DECODE_MODES if value == decode_mode),
            "output_size_bytes": output_path.stat().st_size,
        }
    except Exception as exc:
        return {
            "codec": codec,
            "available": True,
            "error": str(exc),
        }
    finally:
        if writer is not None:
            try:
                writer.Close()
            except Exception:
                pass
        reader.Close()


def recommendations(report):
    fastest_overall = max(report["decode"], key=lambda item: item["frames_per_second"])
    cpu_decode = next(item for item in report["decode"] if item["mode"] == "cpu")
    valid_hardware = [
        item for item in report["decode"]
        if item["mode"] != "cpu" and item.get("hardware_success")
    ]
    fastest_hardware = max(valid_hardware, key=lambda item: item["frames_per_second"], default=None)
    encode_by_codec = {item["codec"]: item for item in report["encode"]}
    recommendations_list = []
    hardware_wins_clearly = (
        fastest_overall["mode"] != "cpu"
        and fastest_overall["frames_per_second"] >= cpu_decode["frames_per_second"] * 1.10
    )
    if not hardware_wins_clearly:
        recommendations_list.append(
            "Keep hardware decode disabled for this clip: CPU decode measured {:.1f} FPS.".format(
                cpu_decode["frames_per_second"]
            )
        )
        if fastest_hardware:
            recommendations_list.append(
                "{} worked correctly but measured {:.1f} FPS because frames return to system memory.".format(
                    fastest_hardware["mode"].upper(), fastest_hardware["frames_per_second"]
                )
            )
    else:
        recommendations_list.append(
            "Use {} for 4K preview decode on this clip.".format(fastest_overall["mode"].upper())
        )
    recommendations_list.extend([
        "Use H.264 NVENC for the default fast and widely compatible 4K export.",
        "Use HEVC NVENC when smaller files matter and the playback target supports HEVC.",
        "Use AV1 NVENC as an optional delivery format, not the only master file.",
        "Keep 8K outside the routine benchmark because it is not a target workload.",
    ])
    if encode_by_codec.get("h264_nvenc", {}).get("error"):
        recommendations_list.insert(0, "H.264 NVENC failed; keep software H.264 as the safe fallback.")
    return recommendations_list


def write_markdown(path, report):
    lines = [
        "# Windows 4K GPU 基准",
        "",
        "- GPU：{}".format(report["gpu"].get("name", "不可用")),
        "- 驱动：{}".format(report["gpu"].get("driver", "未知")),
        "- 素材：{}x{}，{} 帧".format(
            report["media"]["width"], report["media"]["height"], report["media"]["video_length"]
        ),
        "- libopenshot：{}".format(report["libopenshot"]),
        "",
        "## 解码",
        "",
        "| 模式 | 硬件成功 | FPS | 实时倍数 |",
        "|---|---:|---:|---:|",
    ]
    for item in report["decode"]:
        lines.append("| {} | {} | {} | {}x |".format(
            item["mode"], item["hardware_success"], item["frames_per_second"], item["realtime_multiple"]
        ))
    lines.extend([
        "",
        "## 编码与完整输出链路",
        "",
        "| 编码器 | FPS | 实时倍数 | 结果 |",
        "|---|---:|---:|---|",
    ])
    for item in report["encode"]:
        lines.append("| {} | {} | {}x | {} |".format(
            item["codec"],
            item.get("frames_per_second", "-"),
            item.get("realtime_multiple", "-"),
            item.get("error", "成功" if item.get("available") else "不可用"),
        ))
    lines.extend(["", "## 建议", ""])
    lines.extend("- {}".format(item) for item in report["recommendations"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--decode-frames", type=int, default=180)
    parser.add_argument("--decode-repeats", type=int, default=3)
    parser.add_argument("--encode-frames", type=int, default=90)
    parser.add_argument("--bitrate", type=int, default=45_000_000)
    parser.add_argument("--skip-encode", action="store_true")
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    install_root = Path(args.install_root).resolve()
    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    configure_runtime(repo_root, install_root)
    import openshot

    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "libopenshot": openshot.OPENSHOT_VERSION_FULL,
        "gpu": gpu_details(),
        "media": media_details(openshot, input_path),
        "decode": [],
        "encode": [],
    }
    for name, value in DECODE_MODES:
        print("Benchmarking decode mode: {}".format(name), flush=True)
        report["decode"].append(
            benchmark_decode(
                openshot,
                input_path,
                args.decode_frames,
                name,
                value,
                args.decode_repeats,
            )
        )
    fastest_decode = max(report["decode"], key=lambda item: item["frames_per_second"])
    fastest_decode_value = dict(DECODE_MODES)[fastest_decode["mode"]]
    if not args.skip_encode:
        for codec in ENCODE_CODECS:
            print("Benchmarking export codec: {}".format(codec), flush=True)
            report["encode"].append(
                benchmark_encode(
                    openshot,
                    input_path,
                    output_dir,
                    args.encode_frames,
                    codec,
                    args.bitrate,
                    fastest_decode_value,
                )
            )
    report["recommendations"] = recommendations(report)

    json_path = Path(args.json_output).resolve()
    markdown_path = Path(args.markdown_output).resolve()
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(markdown_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
