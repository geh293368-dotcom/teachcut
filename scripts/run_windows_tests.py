#!/usr/bin/env python3
"""Run the OpenShot Python test suite against a local Windows native build."""

import argparse
import os
from pathlib import Path
import sys
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--verbosity", type=int, default=1)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    install_root = Path(args.install_root).resolve()
    mingw_bin = Path(sys.executable).resolve().parent
    native_bin = install_root / "bin"

    if hasattr(os, "add_dll_directory"):
        for dll_dir in (native_bin, mingw_bin):
            os.add_dll_directory(str(dll_dir))

    sys.path[:0] = [
        str(install_root / "python"),
        str(repo_root / "src"),
    ]
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    tests_dir = repo_root / "src" / "tests"
    suite = unittest.defaultTestLoader.discover(
        str(tests_dir),
        top_level_dir=str(tests_dir),
    )
    result = unittest.TextTestRunner(verbosity=args.verbosity).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
