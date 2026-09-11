#!/usr/bin/env python3
"""
verify_publish.py - confirm every slide in the manifest is actually live.

Run this after pushing and before anyone places images on the Miro board.
A slide that 404s or comes back as text will show up on the wall as a broken
tile in front of the class.

Usage:
    python3 tools/verify_publish.py --base https://profangrybeard.github.io/GAME405/idea-wall/

Checks each file for:
  - HTTP 200
  - an image content type, not text
  - a real byte count, not a Git LFS pointer

LFS pointers are the specific failure worth naming. GitHub Pages does not
serve LFS-tracked files, it serves the pointer text, so the image silently
becomes ~130 bytes of ASCII. See .gitattributes at the repo root.
"""

import argparse, json, sys
from pathlib import Path

import requests

LFS_MAGIC = b"version https://git-lfs"


def check(url, session):
    try:
        r = session.get(url, timeout=20)
    except requests.RequestException as e:
        return f"unreachable ({e.__class__.__name__})"

    if r.status_code != 200:
        return f"HTTP {r.status_code}"

    ctype = r.headers.get("content-type", "")
    if not ctype.startswith("image/"):
        return f"content-type {ctype or 'missing'}, expected an image"

    if r.content.startswith(LFS_MAGIC):
        return "Git LFS pointer, not the image (Pages cannot serve LFS)"

    if len(r.content) < 5000:
        return f"only {len(r.content)} bytes, probably not a real slide"

    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True,
                    help="Pages URL of the idea-wall folder, with trailing slash")
    ap.add_argument("--manifest", default="manifest.json")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    slides = manifest.get("slides", [])
    if not slides:
        sys.exit("manifest has no slides")

    base = args.base.rstrip("/") + "/"
    session = requests.Session()
    failures = []

    print(f"checking {len(slides)} slides and their blurred twins against {base}")
    for s in slides:
        for path in (s["file"], "blur/" + s["file"]):
            problem = check(f"{base}slides/{path}", session)
            if problem:
                failures.append((path, problem))
                print(f"  FAIL {path}: {problem}")

    print()
    if failures:
        print(f"{len(failures)} of {len(slides)} slides are not usable.")
        print("Fix these before building the board.")
        sys.exit(1)

    print(f"all {len(slides)} slides live and serving as images.")
    print(f"manifest: {base}manifest.json")


if __name__ == "__main__":
    main()
