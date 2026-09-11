#!/usr/bin/env python3
"""
place_slides.py - lay out the Miro idea wall from what was delivered.

Usage:
    python3 tools/place_slides.py              # plan, and write the SVG steps
    python3 tools/place_slides.py record FILE  # check a read-back of the wall, update the ledger
    python3 tools/place_slides.py check        # layout self-check

Run it from idea-wall/ after the render loop is done, pushed, and verified.

The wall holds exactly the pitches that were delivered. The grid, the frame
and the counters are worked out again on every run, so the wall shrinks when
pitches are missing and grows when students are added. The frame always stays
16:9 so it fills the classroom TV, and no designer's slides touch, diagonals
included.

This script never talks to Miro. It writes placement_plan.json and the SVG
steps in placement_svg/ for Claude to send through the Miro connector, and it
keeps the ledger of what is on the wall in placements.json. See the placement
loop in CLAUDE.md.
"""

import argparse, hashlib, json, math, random, re, sys
from pathlib import Path

BOARD = "https://miro.com/app/board/uXjVHoWCO8w=/"
FRAME_ID = "3458764683429206119"  # the wall frame
TILE_W, TILE_H, GUTTER = 320, 180, 16
MARGIN = 80       # left, right and below the mosaic
TOP = 330         # the mosaic starts below the title block and the counters
HEADER_W = 2400   # narrowest frame that still fits the title and the counters
CHUNK = 20        # images per SVG step

TITLE = "Senior Studio 2026/2027: Idea Wall"
BYLINE = "Every idea this room pitched. <b>Nothing</b> thrown away."
JAM_TEAMS, PRODUCTION = 5, 2
CREAM, SLATE, AMBER = "#eae6dc", "#8fa0b6", "#f0a93b"

# Header text already on the wall. The designers line is created on the first run.
HEADER_IDS = {
    "title": "3458764683429206128", "byline": "3458764683429206129",
    "pitches": "3458764683429206130", "pitches_label": "3458764683429206131",
    "jam": "3458764683429206132", "jam_label": "3458764683429206133",
    "production": "3458764683429206134", "production_label": "3458764683429206135",
}


def load(path, default=None):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    if default is None:
        sys.exit(f"{path} not found")
    return default


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_ledger(path):
    ledger = load(path, {})
    placed = {name: {"image_id": e["image_id"], "sha256": e["sha256"], "box": e.get("box")}
              for name, e in ledger.get("placed", {}).items()}
    return {"frame": ledger.get("frame", [3168, 1782]),
            "header": {**HEADER_IDS, **ledger.get("header", {})},
            "placed": placed}


# ---------- layout ----------

def frame_for(n):
    """Grid and a 16:9 frame for n tiles. The grid is centred left to right."""
    best = None
    for cols in range(max(1, math.ceil(math.sqrt(n))), 17):
        rows = math.ceil(n / cols)
        grid_w = cols * TILE_W + (cols - 1) * GUTTER
        w = max(grid_w + 2 * MARGIN, HEADER_W)
        h = TOP + rows * TILE_H + max(rows - 1, 0) * GUTTER + MARGIN
        score = abs(math.log(w * 9 / (h * 16)))
        if best is None or score < best[0]:
            best = (score, cols, rows, grid_w, w, h)
    _, cols, rows, grid_w, w, h = best
    # Pad to exactly 16:9 so presenting the frame fills the TV.
    if w * 9 < h * 16:
        h = math.ceil(h / 9) * 9
        w = h // 9 * 16
    else:
        w = math.ceil(w / 16) * 16
        h = w // 16 * 9
    return {"cols": cols, "rows": rows, "w": w, "h": h, "grid_w": grid_w, "x0": (w - grid_w) // 2}


def arrange(slides, cols):
    """Order slides so no designer's slides touch, diagonals included.
    Deterministic, not random: the same slides always give the same wall."""
    queues = {}
    for s in sorted(slides, key=lambda s: s["idea"]):
        queues.setdefault(s["student"], []).append(s)
    rank = {k: hashlib.sha1(k.encode()).hexdigest() for k in queues}
    left = {k: len(v) for k, v in queues.items()}
    cells, budget = [], [200000]

    def clear(i, k):
        r, c = divmod(i, cols)
        for dr, dc in ((0, -1), (-1, -1), (-1, 0), (-1, 1)):
            rr, cc = r + dr, c + dc
            if rr >= 0 and 0 <= cc < cols and cells[rr * cols + cc] == k:
                return False
        return True

    def fill(i):
        if i == len(slides):
            return True
        budget[0] -= 1
        if budget[0] < 0:
            return False
        # Designers with the most slides left go first, so none is stranded at the end.
        for k in sorted((k for k in left if left[k]), key=lambda k: (-left[k], rank[k])):
            if clear(i, k):
                cells.append(k)
                left[k] -= 1
                if fill(i + 1):
                    return True
                cells.pop()
                left[k] += 1
        return False

    apart = fill(0)
    if not apart:  # too few designers for the grid to keep them apart
        cells[:] = [k for k in sorted(queues, key=rank.get) for _ in queues[k]]
    taken = {k: 0 for k in queues}
    order = []
    for k in cells:
        order.append(queues[k][taken[k]])
        taken[k] += 1
    return order, apart


# ---------- SVG steps ----------

def frame_open(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg">\n'
            f'<g data-miro-id="{FRAME_ID}" transform="translate(0,0)" data-frame="">\n'
            f'<rect data-type="frame" x="0" y="0" width="{w}" height="{h}" />\n')


FRAME_CLOSE = "</g>\n</svg>\n"


def image_el(step, create):
    x, y, w, h = step["box"]
    if create:
        return (f'<image id="{step["name"]}" data-type="image" href="{step["url"]}" '
                f'x="{x}" y="{y}" width="{w}" height="{h}" />\n')
    return (f'<image data-miro-id="{step["image_id"]}" data-type="image" '
            f'x="{x}" y="{y}" width="{w}" height="{h}" />\n')


def text_el(ids, key, x, y, width, size, color, body, align="left", bold=False):
    ident = f'data-miro-id="{ids[key]}"' if ids.get(key) else f'id="{key}"'
    weight = ' font-weight="bold"' if bold else ""
    return (f'<textArea {ident} x="{x}" y="{y}" width="{width}" fill="{color}" '
            f'font-family="plex_sans" font-size="{size}" text-align="{align}"{weight}>{body}</textArea>\n')


def designers_line(n):
    return f"by {n} designer{'' if n == 1 else 's'}"


def header_els(geo, pitches, designers, ids):
    """Title and byline on the left. The counters on the right dominate, with
    the designer count as subtext under the pitches."""
    hw = max(geo["grid_w"], HEADER_W - 2 * MARGIN)
    left = (geo["w"] - hw) // 2
    bw, gap = 300, 40
    xs = [left + hw - 3 * bw - 2 * gap, left + hw - 2 * bw - gap, left + hw - bw]
    title_w = hw - 3 * bw - 2 * gap - 60
    els = [text_el(ids, "title", left, 40, title_w, 58, CREAM, TITLE, bold=True),
           text_el(ids, "byline", left, 132, title_w, 26, SLATE, BYLINE)]
    counters = [("pitches", pitches, "PITCHED"), ("jam", JAM_TEAMS, "JAM TEAMS"),
                ("production", PRODUCTION, "PRODUCTION")]
    for (key, value, label), x in zip(counters, xs):
        els.append(text_el(ids, key, x, 10, bw, 132, AMBER, str(value), "center", bold=True))
        els.append(text_el(ids, key + "_label", x, 196, bw, 22, SLATE, label, "center"))
    els.append(text_el(ids, "designers", xs[0], 230, bw, 22, CREAM, designers_line(designers), "center"))
    return els


# ---------- commands ----------

def plan(args):
    manifest = load(args.manifest)
    if manifest["problems"] or manifest["needs_review"]:
        sys.exit("manifest.json still has problems or needs_review. Finish the render loop first.")
    ledger = load_ledger(args.ledger)
    placed = ledger["placed"]
    base = args.base.rstrip("/") + "/"
    geo = frame_for(len(manifest["slides"]))
    order, apart = arrange(manifest["slides"], geo["cols"])

    steps = []
    for i, s in enumerate(order):
        r, c = divmod(i, geo["cols"])
        box = [geo["x0"] + c * (TILE_W + GUTTER), TOP + r * (TILE_H + GUTTER), TILE_W, TILE_H]
        name = Path(s["file"]).stem
        step = {"name": name, "student": s["student"], "title": s["title"], "box": box,
                "url": base + "slides/" + s["file"],
                "sha256": hashlib.sha256(Path(args.slides, s["file"]).read_bytes()).hexdigest()}
        old = placed.get(name)
        if old is None:
            step["action"] = "place"
        elif old["sha256"] != step["sha256"]:
            step.update(action="replace", old_image_id=old["image_id"])
        elif old["box"] != box:
            step.update(action="move", image_id=old["image_id"])
        else:
            step.update(action="keep", image_id=old["image_id"])
        steps.append(step)
    planned = {s["name"] for s in steps}
    removals = [{"name": n, "image_id": e["image_id"]} for n, e in placed.items() if n not in planned]
    pitches, designers = len(steps), len({s["student"] for s in steps})
    notes = [] if apart else ["too few designers to keep every designer's slides apart"]

    # Grow the frame to cover both layouts first, place and move, then settle it.
    ow, oh = ledger["frame"]
    uw, uh = max(ow, geo["w"]), max(oh, geo["h"])
    out = Path(args.svg_dir)
    out.mkdir(exist_ok=True)
    for f in out.glob("*.svg"):
        f.unlink()
    files = []

    def write(name, body):
        (out / name).write_text(body, encoding="utf-8", newline="\n")
        files.append(f"{out.name}/{name}")

    if (uw, uh) != (ow, oh):
        write("1_grow.svg", frame_open(uw, uh) + FRAME_CLOSE)
    routine = [s for s in steps if s["action"] in ("place", "move")]
    for n in range(0, len(routine), CHUNK):
        chunk = routine[n:n + CHUNK]
        write(f"2_images_{n // CHUNK + 1:02d}.svg", frame_open(uw, uh) +
              "".join(image_el(s, s["action"] == "place") for s in chunk) + FRAME_CLOSE)
    replaces = [s for s in steps if s["action"] == "replace"]
    needs_ok = None
    if removals or replaces:
        needs_ok = "3_needs_ok.svg"
        write(needs_ok, frame_open(uw, uh) +
              "".join(f'<image data-miro-id="{e["image_id"]}" data-deleted="true" />\n' for e in removals) +
              "".join(f'<image data-miro-id="{s["old_image_id"]}" data-deleted="true" />\n' for s in replaces) +
              "".join(image_el(s, True) for s in replaces) + FRAME_CLOSE)
    write("4_finish.svg", frame_open(geo["w"], geo["h"]) +
          "".join(header_els(geo, pitches, designers, ledger["header"])) + FRAME_CLOSE)

    save(args.plan, {"board": BOARD, "frame_id": FRAME_ID, "frame": [geo["w"], geo["h"]],
                     "cols": geo["cols"], "rows": geo["rows"], "pitches": pitches,
                     "designers": designers, "steps": steps, "removals": removals,
                     "notes": notes, "svg": files, "needs_ok": needs_ok})

    count = {a: sum(s["action"] == a for s in steps) for a in ("place", "move", "keep", "replace")}
    print(f"wall: {pitches} pitches by {designers} designers, {geo['cols']} x {geo['rows']} grid, "
          f"frame {geo['w']}x{geo['h']}")
    print("  " + ", ".join(f"{a} {n}" for a, n in count.items()) + f", remove {len(removals)}")
    print("SVG steps, in order:")
    for f in files:
        print(f"  {f}" + ("   <- deletes, needs Tim's OK" if needs_ok and f.endswith(needs_ok) else ""))
    for n in notes:
        print("NOTE:", n)


def attrs(s):
    return dict(re.findall(r'([\w:-]+)="([^"]*)"', s))


def record(args):
    """Check a read-back of the wall frame against the plan, then update the ledger."""
    plan_ = load(args.plan)
    ledger = load_ledger(args.ledger)
    svg = Path(args.file).read_text(encoding="utf-8")
    images = [attrs(a) for a in re.findall(r"<image\b([^>]*?)/?>", svg)]
    texts = [(attrs(a), re.sub(r"<[^>]+>", "", body).strip())
             for a, body in re.findall(r"<textArea\b([^>]*)>(.*?)</textArea>", svg, re.S)]
    shapes = len(re.findall(r'<rect\b(?![^>]*data-type="frame")', svg))
    frame = attrs(re.search(r'<rect\b[^>]*data-type="frame"[^>]*>', svg).group(0))

    at = {}
    for im in images:
        at.setdefault((round(float(im["x"])), round(float(im["y"]))), []).append(im["data-miro-id"])
    on_board = {im["data-miro-id"] for im in images}
    problems, placed = [], {}
    for s in plan_["steps"]:
        here = at.pop((s["box"][0], s["box"][1]), [])
        stale = s["action"] == "replace" and here == [s["old_image_id"]]
        if len(here) == 1 and not stale:
            placed[s["name"]] = {"image_id": here[0], "sha256": s["sha256"], "box": s["box"]}
            continue
        problems.append(f"{s['name']}: " + ("replace not applied" if stale else
                                            f"{len(here)} images at {s['box'][0]},{s['box'][1]}"))
        if s["name"] in ledger["placed"]:
            placed[s["name"]] = ledger["placed"][s["name"]]
    for name, old in ledger["placed"].items():
        if name not in placed and old["image_id"] in on_board:
            placed[name] = old
            problems.append(f"{name}: still on the wall, removal not applied")
    known = {e["image_id"] for e in placed.values()}
    for (x, y), ids in at.items():
        extra = [i for i in ids if i not in known]
        if extra:
            problems.append(f"{len(extra)} unplanned image(s) at {x},{y}")

    header = dict(ledger["header"])
    for a, body in texts:
        if re.fullmatch(r"by \d+ designers?", body):
            header["designers"] = a["data-miro-id"]
    shown = {a.get("data-miro-id"): body for a, body in texts}
    for key, want in (("pitches", str(plan_["pitches"])), ("designers", designers_line(plan_["designers"])),
                      ("title", TITLE)):
        if shown.get(header.get(key)) != want:
            problems.append(f"{key} reads {shown.get(header.get(key))!r}, expected {want!r}")
    if [round(float(frame["width"])), round(float(frame["height"]))] != plan_["frame"]:
        problems.append(f"frame is {frame['width']}x{frame['height']}, expected {plan_['frame']}")
    if shapes:
        problems.append(f"{shapes} tiles or other shapes still inside the frame")

    save(args.ledger, {"frame": plan_["frame"], "header": header, "placed": placed})
    print(f"{len(placed)} slides recorded, wall reads {plan_['pitches']} pitches "
          f"by {plan_['designers']} designers")
    for p in problems:
        print("PROBLEM:", p)
    if not problems:
        print("the wall matches the plan.")


def check(args):
    rng = random.Random(405)
    cases = [[3] * n for n in (22, 23, 24, 25, 30)]
    cases += [[rng.choice((1, 2, 3, 3, 3)) for _ in range(n)] for n in (6, 12, 18, 23, 26)]
    fails = []
    for counts in cases:
        slides = [{"student": f"s{d:02d}", "idea": i + 1} for d, c in enumerate(counts) for i in range(c)]
        geo = frame_for(len(slides))
        order, apart = arrange(slides, geo["cols"])
        again, _ = arrange(list(reversed(slides)), geo["cols"])
        cells = {divmod(i, geo["cols"]): s["student"] for i, s in enumerate(order)}
        touching = sum(cells.get((r + dr, c + dc)) == k for (r, c), k in cells.items()
                       for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)
        bottom = TOP + geo["rows"] * (TILE_H + GUTTER) - GUTTER
        label = f"{len(slides)} pitches by {len(counts)} designers"
        if not apart or touching:
            fails.append(f"{label}: {touching} touching pairs")
        if order != again:
            fails.append(f"{label}: layout depends on input order")
        if geo["w"] * 9 != geo["h"] * 16:
            fails.append(f"{label}: frame {geo['w']}x{geo['h']} is not 16:9")
        if geo["x0"] < MARGIN or bottom > geo["h"] - MARGIN:
            fails.append(f"{label}: mosaic runs past the margins")
        print(f"  {label:26} {geo['cols']:2} x {geo['rows']} grid, frame {geo['w']}x{geo['h']}, "
              f"{touching} touching")
    if frame_for(69)["cols"] != 9:
        fails.append("69 pitches no longer lay out 9 across")
    for f in fails:
        print("FAIL:", f)
    if fails:
        sys.exit(f"{len(fails)} layout checks failed.")
    print("layout: every case 16:9, inside the margins, no designer touching their own slides.")


def main():
    ap = argparse.ArgumentParser(description="Lay out the Miro idea wall.")
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--ledger", default="placements.json")
    ap.add_argument("--plan", default="placement_plan.json")
    ap.add_argument("--svg-dir", default="placement_svg")
    ap.add_argument("--slides", default="slides")
    ap.add_argument("--base", default="https://profangrybeard.github.io/GAME405/idea-wall/",
                    help="Pages URL of the idea-wall folder. Case-sensitive.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("record", help="check a read-back of the wall, update the ledger").add_argument("file")
    sub.add_parser("check", help="layout self-check")
    args = ap.parse_args()
    {"record": record, "check": check}.get(args.cmd, plan)(args)


if __name__ == "__main__":
    main()
