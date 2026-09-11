#!/usr/bin/env python3
"""
place_slides.py - plan where each published slide goes on the Miro wall.

Usage:
    python3 tools/place_slides.py                              # write the plan
    python3 tools/place_slides.py record FILE IMAGE_ID TILE_ID
    python3 tools/place_slides.py forget FILE
    python3 tools/place_slides.py check                        # geometry self-check

Run it from idea-wall/ after the render loop is done, pushed, and verified.

The wall is a 9-column grid of 320x180 tiles inside one frame. Each student
owns a slot NN from 1 to 23, and their idea N sits at grid position
(N-1)*23 + (NN-1). That stride keeps a designer's three slides from touching,
diagonals included.

This script never talks to Miro. It decides what should change, writes
placement_plan.json, and keeps the ledger of what is on the board in
placements.json. Claude carries out the plan through the Miro connector and
records each placed image back here. See the placement loop in CLAUDE.md.
"""

import argparse, hashlib, json, sys
from pathlib import Path

BOARD = "https://miro.com/app/board/uXjVHoWCO8w=/"
FRAME_ID = "3458764683429206119"  # GAME 405 · THE IDEA WALL
FRAME_W, FRAME_H = 3168, 1782
COLS, SLOTS, IDEAS = 9, 23, 3
TILE_W, TILE_H, GUTTER = 320, 180, 16
ORIGIN_X, ORIGIN_Y = 80, 170


def tile_box(slot, idea):
    """Top-left of a tile, relative to the wall frame."""
    row, col = divmod((idea - 1) * SLOTS + (slot - 1), COLS)
    return ORIGIN_X + col * (TILE_W + GUTTER), ORIGIN_Y + row * (TILE_H + GUTTER)


def load(path, default=None):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    if default is None:
        sys.exit(f"{path} not found")
    return default


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n", newline="\n")


def plan(args):
    manifest = load(args.manifest)
    if manifest["problems"] or manifest["needs_review"]:
        sys.exit("manifest.json still has problems or needs_review. Finish the render loop first.")
    ledger = load(args.ledger, {"slots": {}, "placed": {}})
    slots, placed = ledger["slots"], ledger["placed"]
    pulled = set(load(args.overrides, {}).get("pulled", []))
    base = args.base.rstrip("/") + "/"
    actions, problems = [], []

    # Slots go first come, first served, and are never reshuffled. A tile name
    # on the board is load-bearing, and the stride makes every slot equal.
    for key in dict.fromkeys(s["student"] for s in manifest["slides"]):
        if key not in slots:
            free = sorted(set(range(1, SLOTS + 1)) - set(slots.values()))
            if not free:
                problems.append(f"{key}: all {SLOTS} slots are taken, extend the board")
                continue
            slots[key] = free[0]

    current = set()
    for s in manifest["slides"]:
        name = Path(s["file"]).stem
        if s["student"] not in slots:
            continue
        if s["idea"] > IDEAS:
            problems.append(f"{s['file']}: the wall has {IDEAS} tiles per student, none for idea {s['idea']}")
            continue
        current.add(name)
        x, y = tile_box(slots[s["student"]], s["idea"])
        step = {
            "name": name,
            "file": s["file"],
            "title": s["title"],
            "tile": f"student{slots[s['student']]:02d}_idea{s['idea']}",
            "url": base + "slides/" + s["file"],
            "x": x + TILE_W // 2,  # image_create positions by the image centre
            "y": y + TILE_H // 2,
            "width": TILE_W,
            "box": [x, y, TILE_W, TILE_H],
            "sha256": hashlib.sha256(Path(args.slides, s["file"]).read_bytes()).hexdigest(),
        }
        old = placed.get(name)
        if old is None:
            actions.append({"action": "place", **step})
        elif old["sha256"] != step["sha256"]:
            actions.append({"action": "replace", **step,
                            "tile_id": old["tile_id"], "old_image_id": old["image_id"]})

    for name, old in placed.items():
        if name not in current:
            why = "pulled" if name in pulled else "no longer in the manifest"
            actions.append({"action": "remove", "name": name, "why": why, "tile": old["tile"],
                            "tile_id": old["tile_id"], "image_id": old["image_id"]})

    save(args.ledger, ledger)
    save(args.plan, {"board": BOARD, "frame_id": FRAME_ID, "actions": actions, "problems": problems})

    print(f"{len(actions)} actions, {len(placed)} slides already on the wall -> {args.plan}")
    for a in actions:
        if a["action"] == "remove":
            print(f"  remove   {a['name']} from {a['tile']} ({a['why']}), needs Tim's OK")
        else:
            note = ", needs Tim's OK" if a["action"] == "replace" else ""
            print(f"  {a['action']:8} {a['name']} -> {a['tile']}  {a['title']!r}{note}")
    for p in problems:
        print("PROBLEM:", p)


def record(args):
    steps = {a["name"]: a for a in load(args.plan)["actions"] if a["action"] in ("place", "replace")}
    name = Path(args.file).stem
    if name not in steps:
        sys.exit(f"{name} is not a place or replace step in {args.plan}")
    a = steps[name]
    ledger = load(args.ledger)
    ledger["placed"][name] = {"file": a["file"], "tile": a["tile"], "tile_id": args.tile_id,
                              "image_id": args.image_id, "sha256": a["sha256"], "title": a["title"]}
    save(args.ledger, ledger)
    print(f"recorded {name}: image {args.image_id} on tile {args.tile_id}")


def forget(args):
    ledger = load(args.ledger)
    name = Path(args.file).stem
    if ledger["placed"].pop(name, None) is None:
        sys.exit(f"{name} is not in {args.ledger}")
    save(args.ledger, ledger)
    print(f"forgot {name}")


def check(args):
    boxes = {(s, i): tile_box(s, i) for s in range(1, SLOTS + 1) for i in range(1, IDEAS + 1)}
    fails = []
    if len(set(boxes.values())) != len(boxes):
        fails.append("two tiles share a position")
    if any(x + TILE_W > FRAME_W or y + TILE_H > FRAME_H for x, y in boxes.values()):
        fails.append("a tile falls outside the frame")
    # Positions read off the live wall on 2026-09-11.
    seen = {(1, 1): (80, 170), (1, 2): (1760, 562), (1, 3): (416, 1150),
            (23, 1): (1424, 562), (4, 2): (2768, 562)}
    fails += [f"student{s:02d}_idea{i} at {boxes[(s, i)]}, the board has {xy}"
              for (s, i), xy in seen.items() if boxes[(s, i)] != xy]
    grid = {((y - ORIGIN_Y) // (TILE_H + GUTTER), (x - ORIGIN_X) // (TILE_W + GUTTER)): s
            for (s, _), (x, y) in boxes.items()}
    for (r, c), s in grid.items():
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (dr or dc) and grid.get((r + dr, c + dc)) == s:
                    fails.append(f"student{s:02d} touches its own tile at row {r}, col {c}")
    for f in fails:
        print("FAIL:", f)
    if fails:
        sys.exit(f"{len(fails)} geometry checks failed.")
    print(f"{len(boxes)} tiles: geometry matches the wall, and no designer's slides touch.")


def main():
    ap = argparse.ArgumentParser(description="Plan slide placement on the Miro wall.")
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--ledger", default="placements.json")
    ap.add_argument("--plan", default="placement_plan.json")
    ap.add_argument("--overrides", default="overrides.json")
    ap.add_argument("--slides", default="slides")
    ap.add_argument("--base", default="https://profangrybeard.github.io/GAME405/idea-wall/",
                    help="Pages URL of the idea-wall folder. Case-sensitive.")
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("record", help="log an image placed from the plan")
    r.add_argument("file")
    r.add_argument("image_id")
    r.add_argument("tile_id")
    sub.add_parser("forget", help="drop a removed slide from the ledger").add_argument("file")
    sub.add_parser("check", help="geometry and adjacency self-check")
    args = ap.parse_args()
    {"record": record, "forget": forget, "check": check}.get(args.cmd, plan)(args)


if __name__ == "__main__":
    main()
