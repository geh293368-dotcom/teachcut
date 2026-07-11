#!/usr/bin/env python3
"""Verify that the local native runtime exposes the codecs required by Windows."""

import argparse
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--verify-gpu", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    install_root = Path(args.install_root).resolve()
    native_bin = install_root / "bin"
    mingw_bin = Path(sys.executable).resolve().parent

    if hasattr(os, "add_dll_directory"):
        for dll_dir in (native_bin, mingw_bin):
            os.add_dll_directory(str(dll_dir))

    sys.path[:0] = [str(install_root / "python"), str(repo_root / "src")]
    import openshot

    print("libopenshot={}".format(openshot.OPENSHOT_VERSION_FULL))
    required_codecs = ("libx264", "h264_nvenc", "hevc_nvenc", "av1_nvenc")
    missing = []
    for codec in required_codecs:
        available = bool(openshot.FFmpegWriter.IsValidCodec(codec))
        print("codec.{}={}".format(codec, available))
        if not available:
            missing.append(codec)
    if missing:
        raise RuntimeError("Missing required Windows codecs: {}".format(", ".join(missing)))

    sample = repo_root / "src" / "resources" / "hardware-example.mp4"
    if not sample.is_file():
        raise RuntimeError("Hardware decode sample is missing: {}".format(sample))

    if args.verify_gpu:
        settings = openshot.Settings.Instance()
        settings.HW_DE_DEVICE_SET = 0
        for mode, label in ((2, "NVDEC"), (4, "D3D11")):
            settings.HARDWARE_DECODER = mode
            reader = openshot.FFmpegReader(str(sample))
            try:
                reader.Open()
                reader.GetFrame(1)
                success = bool(reader.HardwareDecodeSuccessful())
                print("decode.{}={}".format(label, success))
                if not success:
                    raise RuntimeError("{} hardware decode fell back to software".format(label))
            finally:
                reader.Close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
