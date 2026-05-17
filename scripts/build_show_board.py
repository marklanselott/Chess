#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "show_board.py"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "show_board"
SPEC_DIR = ROOT / "build" / "show_board_spec"


def executable_name(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def pyinstaller_is_available() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--version"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def install_pyinstaller() -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyinstaller"],
        cwd=ROOT,
        check=True,
    )


def build(name: str, clean: bool) -> Path:
    if clean:
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        shutil.rmtree(SPEC_DIR, ignore_errors=True)

    DIST_DIR.mkdir(exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--console",
        "--noconfirm",
        "--name",
        name,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(SPEC_DIR),
        str(ENTRYPOINT),
    ]

    if clean:
        command.insert(3, "--clean")

    subprocess.run(command, cwd=ROOT, check=True)
    return DIST_DIR / executable_name(name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build scripts/show_board.py into a single executable file."
    )
    parser.add_argument("--name", default="show_board", help="Output executable name")
    parser.add_argument("--no-clean", action="store_true", help="Keep previous PyInstaller cache")
    parser.add_argument(
        "--install-pyinstaller",
        action="store_true",
        help="Install PyInstaller into the current Python environment if it is missing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not ENTRYPOINT.exists():
        print(f"Entry point not found: {ENTRYPOINT}", file=sys.stderr)
        return 1

    if not pyinstaller_is_available():
        if args.install_pyinstaller:
            install_pyinstaller()
        else:
            print(
                "PyInstaller is not installed. Run:\n"
                f"  {sys.executable} -m pip install pyinstaller\n"
                "or rerun this script with --install-pyinstaller",
                file=sys.stderr,
            )
            return 1

    output = build(args.name, clean=not args.no_clean)
    print(f"Built: {output}")
    print("Place .env in the current folder, next to this file, or in its parent folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
