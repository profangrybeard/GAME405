#!/usr/bin/env python3
"""
place_slides.py - lay out the Miro idea wall from what was delivered.

Usage:
    python3 tools/place_slides.py               # plan, and write the SVG steps
    python3 tools/place_slides.py record FILE   # check a read-back of the frame, update the ledger
    python3 tools/place_slides.py adopt FILE    # take over placeholder tiles already on the frame
    python3 tools/place_slides.py blur on|off   # lay blurred copies over the slides until the reveal
    python3 tools/place_slides.py check         # layout and blur self-check

Run it from idea-wall/ after the render loop is done, pushed, and verified.

The wall shows every delivered pitch and never fewer than 63 tiles. Until
enough pitches arrive, placeholder tiles fill the rest under the names the wall
has always had, so it can be demoed any time. Past 63 it grows with the
pitches. The grid, the frame and the counters are worked out again on every
run. The frame always stays 16:9 so it fills the classroom TV, and no
designer's slides touch, diagonals included.

Miro has no blur or filter for images. With blur on, a blurred copy of every
slide from slides/blur/ sits on top of it, so the wall suggests its contents
without giving them away. The reveal deletes the copies, and the sharp slides
are already underneath. Miro stacks items in the order they were made, across
frames, so a copy is always made in a later step than its slide.

Miro's tools can create items inside a frame and delete them, but cannot move
an image or a text that is already inside one, or swap an image's source. So
nothing is ever moved: an item that is already right stays, and anything that
has to change is deleted and made again. Miro also resizes a frame around its
centre and leaves everything inside where it was, so every resize comes with a
second step that lands the frame back on its origin.

This script never talks to Miro. It writes placement_plan.json and the SVG
steps in placement_svg/ for Claude to send through the Miro connector, and it
keeps the ledger of what is on the wall in placements.json. See the placement
loop in CLAUDE.md.
"""

import argparse, hashlib, json, math, random, re, sys
from pathlib import Path

WALL_FRAME = "3458764683429206119"
TILE_W, TILE_H, GUTTER = 320, 180, 16
MARGIN = 80       # left, right and below the mosaic
TOP = 330         # the mosaic starts below the title block and the counters
HEADER_W = 2400   # narrowest frame that still fits the title and the counters
MIN_TILES = 63    # 9 across, 7 down: the smallest the wall ever gets
CHUNK = 20        # images per SVG step

TITLE = "Senior Studio 2026/2027: Idea Wall"
BYLINE = "Every idea this room pitched. <b>Nothing</b> thrown away."
JAM_TEAMS, PRODUCTION = 5, 2
CREAM, SLATE, AMBER = "#eae6dc", "#8fa0b6", "#f0a93b"
TILE_STYLE = ('rx="6" fill="#1e2e45" data-text-color="#8fa0b6" data-font-size="18" '
              'stroke="#2c3e56" stroke-dasharray="5,5"')
PLACEHOLDER = re.compile(r"student\d{2}_idea\d")

# Header text already on the live wall, from the first design. Its position is
# unknown to the ledger, so the first run rebuilds it.
HEADER_IDS = {
    "title": "3458764683429206128", "byline": "3458764683429206129",
    "pitches": "3458764683429206130", "pitches_label": "3458764683429206131",
    "jam": "3458764683429206132", "jam_label": "3458764683429206133",
    "production": "3458764683429206134", "production_label": "3458764683429206135",
}


def placeholder_name(p):
    """The wall's original tile names, by grid position."""
    return f"student{p % 23 + 1:02d}_idea{p // 23 + 1}"


def load(path, default=None):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    if default is None:
        sys.exit(f"{path} not found")
    return default


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def digest(path):
    """Hash of a published file, so a re-rendered slide gets placed again."""
    if not path.exists():
        sys.exit(f"{path} is missing. The render loop makes it, so run that first.")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_ledger(path):
    ledger = load(path, {})
    placed, tiles = {}, dict(ledger.get("tiles", {}))
    for name, e in ledger.get("placed", {}).items():
        placed[name] = {"image_id": e["image_id"], "box": e.get("box"),
                        # Placed as its blurred twin, before the copies went on top: make it again, sharp.
                        "sha256": None if e.get("blurred") else e["sha256"],
                        "cover_id": e.get("cover_id"), "cover_sha256": e.get("cover_sha256")}
        if "tile_id" in e:  # first ledger format: the slide sat on a placeholder tile
            tiles.setdefault(e["tile"], {"tile_id": e["tile_id"], "box": None})
    header = {k: v if isinstance(v, dict) else {"id": v, "x": None, "y": None}
              for k, v in ledger.get("header", HEADER_IDS).items()}
    return {"frame_id": ledger.get("frame_id", WALL_FRAME), "origin": ledger.get("origin", [0, 0]),
            "frame": ledger.get("frame", [3168, 1782]), "header": header,
            "placed": placed, "tiles": tiles}


def slide_actions(old, box, sha, cover_sha, blur):
    """What a run does to one slide and its blurred copy: (slide, copy, ids to delete).
    A copy has to be made after its slide to sit on top of it, so a slide that
    is made again always gets a new copy."""
    gone = []
    if old is None:
        act = "place"
    elif (old["sha256"], old["box"]) == (sha, box):
        act = "keep"
    else:
        act = "rebuild"
        gone.append(old["image_id"])
    had = old.get("cover_id") if old else None
    if not blur:
        cover = "remove" if had else "none"
    elif not had:
        cover = "create"
    elif act == "keep" and old.get("cover_sha256") == cover_sha:
        cover = "keep"
    else:
        cover = "rebuild"
    if had and cover in ("remove", "rebuild"):
        gone.append(had)
    return act, cover, gone


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


def header_specs(geo, pitches, designers):
    """Title and byline on the left. The counters on the right dominate, with
    the designer count as subtext under the pitches."""
    hw = max(geo["grid_w"], HEADER_W - 2 * MARGIN)
    left = (geo["w"] - hw) // 2
    bw, gap = 300, 40
    xs = [left + hw - 3 * bw - 2 * gap, left + hw - 2 * bw - gap, left + hw - bw]
    title_w = hw - 3 * bw - 2 * gap - 60
    who = f"by {designers} designer{'' if designers == 1 else 's'}"
    specs = [("title", left, 40, title_w, 58, CREAM, TITLE, "left", True),
             ("byline", left, 132, title_w, 26, SLATE, BYLINE, "left", False)]
    for (key, value, label), x in zip([("pitches", pitches, "PITCHED"), ("jam", JAM_TEAMS, "JAM TEAMS"),
                                       ("production", PRODUCTION, "PRODUCTION")], xs):
        specs.append((key, x, 10, bw, 132, AMBER, str(value), "center", True))
        specs.append((key + "_label", x, 196, bw, 22, SLATE, label, "center", False))
    specs.append(("designers", xs[0], 230, bw, 22, CREAM, who, "center", False))
    keys = ("key", "x", "y", "width", "size", "color", "body", "align", "bold")
    return [dict(zip(keys, s)) for s in specs]


# ---------- SVG ----------

def num(v):
    return f"{v:g}"


def frame_svg(frame_id, at, w, h, items):
    return ('<svg xmlns="http://www.w3.org/2000/svg">\n'
            f'<g data-miro-id="{frame_id}" transform="translate({num(at[0])},{num(at[1])})" data-frame="">\n'
            f'<rect data-type="frame" x="0" y="0" width="{w}" height="{h}" />\n'
            + "".join(items) + "</g>\n</svg>\n")


def image_el(ident, url, box):
    x, y, w, h = box
    return f'<image id="{ident}" data-type="image" href="{url}" x="{x}" y="{y}" width="{w}" height="{h}" />\n'


def slide_el(s):
    return image_el(s["name"], s["url"], s["box"])


def cover_el(s):
    return image_el(s["name"] + "_blur", s["cover_url"], s["box"])


def tile_el(t):
    x, y, w, h = t["box"]
    return (f'<rect id="{t["label"]}" x="{x}" y="{y}" width="{w}" height="{h}" '
            f'data-content="{t["label"]}" {TILE_STYLE} />\n')


def text_el(sp):
    ident = f'data-miro-id="{sp["id"]}"' if sp["action"] == "keep" else f'id="{sp["key"]}"'
    weight = ' font-weight="bold"' if sp["bold"] else ""
    return (f'<textArea {ident} x="{sp["x"]}" y="{sp["y"]}" width="{sp["width"]}" fill="{sp["color"]}" '
            f'font-family="plex_sans" font-size="{sp["size"]}" text-align="{sp["align"]}"{weight}>'
            f'{sp["body"]}</textArea>\n')


def delete_el(tag, item_id):
    return f'<{tag} data-miro-id="{item_id}" data-deleted="true" />\n'


# ---------- commands ----------

def plan(args):
    manifest = load(args.manifest)
    if manifest["problems"] or manifest["needs_review"]:
        sys.exit("manifest.json still has problems or needs_review. Finish the render loop first.")
    ledger = load_ledger(args.ledger)
    blur = bool(load(args.overrides, {}).get("blur", False))
    base = args.base.rstrip("/") + "/"
    slides = manifest["slides"]
    total = max(MIN_TILES, len(slides))
    geo = frame_for(total)
    order, apart = arrange(slides, geo["cols"])

    def box(p):
        r, c = divmod(p, geo["cols"])
        return [geo["x0"] + c * (TILE_W + GUTTER), TOP + r * (TILE_H + GUTTER), TILE_W, TILE_H]

    steps = []
    for p, s in enumerate(order):
        src = s.get("src", s["file"])
        step = {"name": Path(s["file"]).stem, "student": s["student"], "box": box(p),
                "url": base + "slides/" + src, "sha256": digest(Path(args.slides, src)),
                "cover_url": base + "slides/blur/" + src,
                "cover_sha256": digest(Path(args.slides, "blur", src)) if blur else None}
        act, cover, gone = slide_actions(ledger["placed"].get(step["name"]), step["box"],
                                         step["sha256"], step["cover_sha256"], blur)
        step.update(action=act, cover=cover, gone=gone)
        steps.append(step)
    names = {s["name"] for s in steps}
    removals = [{"name": n, "ids": [i for i in (e["image_id"], e["cover_id"]) if i]}
                for n, e in ledger["placed"].items() if n not in names]

    tiles = []
    for p in range(len(slides), total):
        t = {"label": placeholder_name(p), "box": box(p)}
        old = ledger["tiles"].get(t["label"])
        if old is None:
            t["action"] = "create"
        elif old["box"] == t["box"]:
            t.update(action="keep", tile_id=old["tile_id"])
        else:
            t.update(action="rebuild", old_tile_id=old["tile_id"])
        tiles.append(t)
    labels = {t["label"] for t in tiles}
    tile_removals = [{"label": l, "tile_id": e["tile_id"]} for l, e in ledger["tiles"].items() if l not in labels]

    pitches, designers = len(steps), len({s["student"] for s in steps})
    specs = header_specs(geo, pitches, designers)
    for sp in specs:
        old = ledger["header"].get(sp["key"])
        if not old or not old.get("id"):
            sp["action"] = "create"
        elif (old["x"], old["y"]) == (sp["x"], sp["y"]):
            sp.update(action="keep", id=old["id"])  # a text body can be updated in place
        else:
            sp.update(action="rebuild", old_id=old["id"])
    keys = {sp["key"] for sp in specs}
    header_removals = [{"key": k, "id": v["id"]} for k, v in ledger["header"].items()
                       if k not in keys and v.get("id")]
    notes = [] if apart or not slides else ["too few designers to keep every designer's slides apart"]

    out = Path(args.svg_dir)
    out.mkdir(exist_ok=True)
    for f in out.glob("*.svg"):
        f.unlink()
    files = []
    fid, origin = ledger["frame_id"], ledger["origin"]
    ow, oh = ledger["frame"]
    uw, uh = max(ow, geo["w"]), max(oh, geo["h"])

    def write(fname, items, w, h, at=origin):
        (out / fname).write_text(frame_svg(fid, at, w, h, items), encoding="utf-8", newline="\n")
        files.append(f"{out.name}/{fname}")

    def write_chunks(prefix, items):
        for i in range(0, len(items), CHUNK):
            write(f"{prefix}_{i // CHUNK + 1:02d}.svg", items[i:i + CHUNK], uw, uh)

    # A grow lands off-centre, so the same step is sent twice: resize, then pin.
    if (uw, uh) != (ow, oh):
        write("1_grow_1_resize.svg", [], uw, uh)
        write("1_grow_2_pin.svg", [], uw, uh)
    # A copy sits on top only if it is made in a later call than its slide. Copies
    # over new slides go straight after them, so none waits uncovered on Tim's OK.
    covers = [s for s in steps if s["cover"] in ("create", "rebuild")]
    write_chunks("2_images", [slide_el(s) for s in steps if s["action"] == "place"])
    write_chunks("3_covers", [cover_el(s) for s in covers if s["action"] == "place"])
    new_tiles = [t for t in tiles if t["action"] == "create"]
    if new_tiles:
        write("4_tiles.svg", [tile_el(t) for t in new_tiles], uw, uh)
    re_imgs = [s for s in steps if s["action"] == "rebuild"]
    re_tiles = [t for t in tiles if t["action"] == "rebuild"]
    re_texts = [sp for sp in specs if sp["action"] == "rebuild"]
    deletes = ([delete_el("image", i) for e in removals for i in e["ids"]] +
               [delete_el("image", i) for s in steps for i in s["gone"]] +
               [delete_el("rect", e["tile_id"]) for e in tile_removals] +
               [delete_el("rect", t["old_tile_id"]) for t in re_tiles] +
               [delete_el("textArea", sp["old_id"]) for sp in re_texts] +
               [delete_el("textArea", e["id"]) for e in header_removals])
    needs_ok = None
    if deletes:
        needs_ok = f"{out.name}/5_needs_ok.svg"
        write("5_needs_ok.svg", deletes + [slide_el(s) for s in re_imgs] + [tile_el(t) for t in re_tiles],
              uw, uh)
    write_chunks("6_covers", [cover_el(s) for s in covers if s["action"] != "place"])
    # A shrink also resizes around the centre, so move the frame up and left by
    # half the difference first, and the resize lands on the origin.
    if (geo["w"], geo["h"]) != (uw, uh):
        dx, dy = (uw - geo["w"]) / 2, (uh - geo["h"]) / 2
        write("7_shrink_1_move.svg", [], uw, uh, [origin[0] - dx, origin[1] - dy])
        write("7_shrink_2_resize.svg", [], geo["w"], geo["h"])
    write("8_header.svg", [text_el(sp) for sp in specs], geo["w"], geo["h"])

    save(args.plan, {"frame_id": fid, "origin": origin, "frame": [geo["w"], geo["h"]],
                     "cols": geo["cols"], "rows": geo["rows"], "pitches": pitches,
                     "designers": designers, "blur": blur, "steps": steps, "removals": removals,
                     "tiles": tiles, "tile_removals": tile_removals, "header": specs,
                     "header_removals": header_removals, "notes": notes, "svg": files,
                     "needs_ok": needs_ok})

    tally = lambda items, acts, field="action": ", ".join(f"{a} {sum(i[field] == a for i in items)}"
                                                         for a in acts)
    print(f"wall: {pitches} pitches by {designers} designers, {len(tiles)} placeholders, "
          f"{geo['cols']} x {geo['rows']} grid, frame {geo['w']}x{geo['h']}, blur {'on' if blur else 'off'}")
    print(f"  slides: {tally(steps, ('place', 'keep', 'rebuild'))}, remove {len(removals)}")
    print(f"  blurred copies: {tally(steps, ('create', 'keep', 'rebuild', 'remove'), 'cover')}")
    print(f"  placeholders: {tally(tiles, ('create', 'keep', 'rebuild'))}, remove {len(tile_removals)}")
    print(f"  header: {tally(specs, ('create', 'keep', 'rebuild'))}")
    print("SVG steps. Send them one at a time, in this order:")
    for f in files:
        print(f"  {f}" + ("   <- deletes, needs Tim's OK. On a no, stop and re-plan." if f == needs_ok else ""))
    for n in notes:
        print("NOTE:", n)


def attrs(s):
    return dict(re.findall(r'([\w:-]+)="([^"]*)"', s))


def read_frame(path):
    from html import unescape  # the canvas read-back escapes rich text: <b> comes back as &lt;b&gt;
    svg = Path(path).read_text(encoding="utf-8")
    g = re.search(r'<g\b[^>]*transform="translate\(([-\d.]+),\s*([-\d.]+)\)"', svg)
    rects = [attrs(a) for a in re.findall(r"<rect\b([^>]*)>", svg)]
    frame = next(r for r in rects if r.get("data-type") == "frame")
    shapes = [r for r in rects if r.get("data-type") != "frame"]
    images = [attrs(a) for a in re.findall(r"<image\b([^>]*?)/?>", svg)]
    texts = [(attrs(a), re.sub(r"<[^>]+>", "", unescape(body)).strip())
             for a, body in re.findall(r"<textArea\b([^>]*)>(.*?)</textArea>", svg, re.S)]
    origin = [float(g.group(1)), float(g.group(2))] if g else None
    return origin, frame, shapes, images, texts


def at(a):
    return round(float(a["x"])), round(float(a["y"]))


def record(args):
    """Check a read-back of the frame against the plan, then update the ledger."""
    plan_ = load(args.plan)
    ledger = load_ledger(args.ledger)
    origin, frame, shapes, images, texts = read_frame(args.file)
    problems = []

    img_at, img_ids = {}, {im["data-miro-id"] for im in images}
    for im in images:  # the read-back lists a frame's children bottom to top
        img_at.setdefault(at(im), []).append(im["data-miro-id"])
    placed = {}
    for s in plan_["steps"]:
        here = img_at.pop(tuple(s["box"][:2]), [])
        want = 2 if s["cover"] in ("create", "rebuild", "keep") else 1
        where = f"{s['box'][0]},{s['box'][1]}"
        if any(i in s["gone"] for i in here):
            problems.append(f"{s['name']}: deletes not applied, an old image is still at {where}")
        elif len(here) != want:
            problems.append(f"{s['name']}: {len(here)} images at {where}, expected {want}")
        else:
            ids = sorted(here, key=int)  # Miro ids grow with creation time: the slide is the older one
            on_top = here == ids
            if not on_top:
                problems.append(f"{s['name']}: the blurred copy is under the slide at {where}")
            placed[s["name"]] = {"image_id": ids[0], "sha256": s["sha256"], "box": s["box"],
                                 "cover_id": ids[1] if want == 2 else None,
                                 # a copy under its slide gets made again on the next run
                                 "cover_sha256": s["cover_sha256"] if want == 2 and on_top else None}
            continue
        if s["name"] in ledger["placed"]:
            placed[s["name"]] = ledger["placed"][s["name"]]
    for name, old in ledger["placed"].items():
        if name not in placed and any(i in img_ids for i in (old["image_id"], old["cover_id"]) if i):
            placed[name] = old
            problems.append(f"{name}: removed slide still on the wall")
    known = {i for e in placed.values() for i in (e["image_id"], e["cover_id"]) if i}
    problems += [f"unplanned image at {x},{y}" for (x, y), ids in img_at.items() for i in ids if i not in known]

    shp_at, shp_ids = {}, {sh["data-miro-id"] for sh in shapes}
    for sh in shapes:
        shp_at.setdefault(at(sh), []).append(sh)
    tiles = {}
    for t in plan_["tiles"]:
        here = shp_at.pop(tuple(t["box"][:2]), [])
        stale = t["action"] == "rebuild" and [h["data-miro-id"] for h in here] == [t["old_tile_id"]]
        if len(here) == 1 and here[0].get("data-content") == t["label"] and not stale:
            tiles[t["label"]] = {"tile_id": here[0]["data-miro-id"], "box": t["box"]}
            continue
        problems.append(f"placeholder {t['label']}: " + ("rebuild not applied" if stale else
                                                          f"{len(here)} tiles at {t['box'][0]},{t['box'][1]}"))
        if t["label"] in ledger["tiles"]:
            tiles[t["label"]] = ledger["tiles"][t["label"]]
    for label, old in ledger["tiles"].items():
        if label not in tiles and old["tile_id"] in shp_ids:
            tiles[label] = old
            problems.append(f"placeholder {label}: old tile still on the wall")
    known = {e["tile_id"] for e in tiles.values()}
    problems += [f"unplanned shape at {x},{y}" for (x, y), shs in shp_at.items()
                 for sh in shs if sh["data-miro-id"] not in known]

    header, matched = {}, set()
    for sp in plan_["header"]:
        hit = [(a, body) for a, body in texts
               if abs(at(a)[0] - sp["x"]) <= 3 and abs(at(a)[1] - sp["y"]) <= 3]
        old = ledger["header"].get(sp["key"])
        if len(hit) != 1:
            problems.append(f"header {sp['key']}: {len(hit)} texts at {sp['x']},{sp['y']}")
            if old:
                header[sp["key"]] = old
            continue
        tid = hit[0][0]["data-miro-id"]
        matched.add(tid)
        if sp["action"] == "rebuild" and tid == sp["old_id"]:
            problems.append(f"header {sp['key']}: rebuild not applied")
        header[sp["key"]] = {"id": tid, "x": sp["x"], "y": sp["y"]}
        want = re.sub(r"<[^>]+>", "", sp["body"])
        if hit[0][1] != want:
            problems.append(f"header {sp['key']} reads {hit[0][1]!r}, expected {want!r}")
    problems += [f"unplanned text {body!r} at {at(a)[0]},{at(a)[1]}" for a, body in texts
                 if a["data-miro-id"] not in matched]

    if [round(float(frame["width"])), round(float(frame["height"]))] != plan_["frame"]:
        problems.append(f"frame is {frame['width']}x{frame['height']}, expected {plan_['frame']}")
    if origin is not None and [round(v) for v in origin] != [round(v) for v in plan_["origin"]]:
        problems.append(f"frame sits at {origin}, expected {plan_['origin']}")

    save(args.ledger, {"frame_id": plan_["frame_id"], "origin": plan_["origin"], "frame": plan_["frame"],
                       "header": header, "placed": placed, "tiles": tiles})
    print(f"recorded {len(placed)} slides and {len(tiles)} placeholders; the wall should read "
          f"{plan_['pitches']} pitches by {plan_['designers']} designers, blur {'on' if plan_['blur'] else 'off'}")
    for p in problems:
        print("PROBLEM:", p)
    if not problems:
        print("the wall matches the plan.")


def adopt(args):
    """Take placeholder tiles already on the frame into the ledger, by label."""
    ledger = load_ledger(args.ledger)
    _, _, shapes, _, _ = read_frame(args.file)
    found = 0
    for sh in shapes:
        if PLACEHOLDER.fullmatch(sh.get("data-content", "")):
            ledger["tiles"][sh["data-content"]] = {"tile_id": sh["data-miro-id"],
                                                   "box": [*at(sh), TILE_W, TILE_H]}
            found += 1
    save(args.ledger, ledger)
    print(f"adopted {found} placeholder tiles, {len(ledger['tiles'])} in the ledger")


def set_blur(args):
    data = load(args.overrides, {})
    data["blur"] = args.state == "on"
    save(args.overrides, data)
    print(f"blur is {args.state}. Run the plan to " +
          ("lay the blurred copies over the slides." if data["blur"] else "take the copies off. That is the reveal."))


def check(args):
    rng = random.Random(405)
    cases = [[3] * n for n in (1, 7, 21, 22, 23, 24, 25, 30)]
    cases += [[rng.choice((1, 2, 3, 3, 3)) for _ in range(n)] for n in (6, 12, 18, 23, 26)]
    fails = []
    for counts in cases:
        slides = [{"student": f"s{d:02d}", "idea": i + 1} for d, c in enumerate(counts) for i in range(c)]
        total = max(MIN_TILES, len(slides))
        geo = frame_for(total)
        order, apart = arrange(slides, geo["cols"])
        again, _ = arrange(list(reversed(slides)), geo["cols"])
        cells = {divmod(i, geo["cols"]): s["student"] for i, s in enumerate(order)}
        touching = sum(cells.get((r + dr, c + dc)) == k for (r, c), k in cells.items()
                       for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)
        labels = [placeholder_name(p) for p in range(len(slides), total)]
        bottom = TOP + geo["rows"] * (TILE_H + GUTTER) - GUTTER
        label = f"{len(slides)} pitches by {len(counts)} designers"
        if len(counts) >= 5 and (not apart or touching):
            fails.append(f"{label}: {touching} touching pairs")
        if order != again:
            fails.append(f"{label}: layout depends on input order")
        if geo["w"] * 9 != geo["h"] * 16:
            fails.append(f"{label}: frame {geo['w']}x{geo['h']} is not 16:9")
        if geo["x0"] < MARGIN or bottom > geo["h"] - MARGIN:
            fails.append(f"{label}: mosaic runs past the margins")
        if len(set(labels)) != len(labels) or len(slides) + len(labels) != total:
            fails.append(f"{label}: placeholders do not fill the floor")
        print(f"  {label:26} {geo['cols']:2} x {geo['rows']} grid, {len(labels):2} placeholders, "
              f"frame {geo['w']}x{geo['h']}, {touching} touching")
    floor = frame_for(MIN_TILES)
    if (floor["cols"], floor["rows"], floor["w"], floor["h"]) != (9, 7, 3168, 1782):
        fails.append("the 63-tile floor is no longer 9 x 7 in a 3168x1782 frame")
    if frame_for(69)["cols"] != 9:
        fails.append("69 pitches no longer lay out 9 across")

    # What one run does to a slide and its blurred copy, case by case.
    a = {"image_id": "1", "sha256": "s", "box": [0, 0, 1, 1], "cover_id": "2", "cover_sha256": "c"}
    bare = dict(a, cover_id=None, cover_sha256=None)
    for label, old, blur, want in [
            ("new slide", None, True, ("place", "create", [])),
            ("nothing changed", a, True, ("keep", "keep", [])),
            ("the reveal", a, False, ("keep", "remove", ["2"])),
            ("blur back on", bare, True, ("keep", "create", [])),
            ("slide moved", dict(a, box=[9, 9, 1, 1]), True, ("rebuild", "rebuild", ["1", "2"])),
            ("copy re-rendered", dict(a, cover_sha256="old"), True, ("keep", "rebuild", ["2"])),
            ("slide re-rendered, blur off", dict(bare, sha256="old"), False, ("rebuild", "none", ["1"])),
            ("placed as a blurred twin", dict(bare, sha256=None), True, ("rebuild", "create", ["1"]))]:
        got = slide_actions(old, [0, 0, 1, 1], "s", "c", blur)
        if got != want:
            fails.append(f"blur, {label}: {got}, expected {want}")

    for f in fails:
        print("FAIL:", f)
    if fails:
        sys.exit(f"{len(fails)} checks failed.")
    print("layout: every case 16:9, inside the margins, floor filled, no designer touching their own slides.")
    print("blur: new, unchanged, revealed, re-blurred, moved and re-rendered slides all plan right.")


def main():
    ap = argparse.ArgumentParser(description="Lay out the Miro idea wall.")
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--ledger", default="placements.json")
    ap.add_argument("--plan", default="placement_plan.json")
    ap.add_argument("--overrides", default="overrides.json")
    ap.add_argument("--svg-dir", default="placement_svg")
    ap.add_argument("--slides", default="slides")
    ap.add_argument("--base", default="https://profangrybeard.github.io/GAME405/idea-wall/",
                    help="Pages URL of the idea-wall folder. Case-sensitive.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("record", help="check a read-back of the frame, update the ledger").add_argument("file")
    sub.add_parser("adopt", help="take over placeholder tiles already on the frame").add_argument("file")
    sub.add_parser("blur", help="lay blurred copies over the slides until the reveal").add_argument(
        "state", choices=["on", "off"])
    sub.add_parser("check", help="layout and blur self-check")
    args = ap.parse_args()
    {"record": record, "adopt": adopt, "blur": set_blur, "check": check}.get(args.cmd, plan)(args)


if __name__ == "__main__":
    main()
