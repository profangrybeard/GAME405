#!/usr/bin/env python3
"""
check_renderer.py - run render_decks.py against synthetic decks and confirm
the cases that have broken before still behave.

Usage:
    python3 tools/check_renderer.py              # temp folder, cleaned up
    python3 tools/check_renderer.py --keep DIR   # keep decks, slides, review

Every name in the fixtures is invented. Point --keep outside the repo: the
fixtures include an About Me page with a stand-in personal photo.
"""

import argparse, json, subprocess, sys, tempfile
from pathlib import Path

import pymupdf

RENDER = Path(__file__).with_name("render_decks.py")
W, H = 720, 405  # 16:9 in points, the Google Slides PDF export size

BODY = ("Players guide a stubborn lighthouse keeper through a storm season, "
        "trading supplies with passing ships and rebuilding the lamp piece by "
        "piece. Every night the fog rolls in thicker and the choices about who "
        "to rescue get harder, so the tone is cozy by day and tense by night. "
        "Core loop is salvage, repair, signal.")
ABOUT = ("I am a third year game design student from Atlanta. I mostly work in "
         "Unreal and Blender, and I love systems heavy games with a strong sense "
         "of place. Outside class I run a tabletop group and sketch every day.")
COLLAGE = ("Three game concepts for Studio I, Fall 2026. Each one is built "
           "around a single strong verb and a place you want to stay in. "
           "Scroll on for the ideas.")
GRID = [(370, 40, 530, 190), (540, 40, 700, 190), (370, 200, 530, 350), (540, 200, 700, 350)]

# id: (filename, name, titles, kind). Each deck exercises one failure mode.
DECKS = {
    "alvarez": ("ATL_A01_GAME405_SamAlvarez_GamePitch.pdf", "Sam Alvarez",
                ["LIGHTKEEPER", "ROOT CELLAR", "PAPER KITES"], "normal"),
    "alvarez_v2": ("ATL_A01_GAME405_SamAlvarez_GamePitch_v2.pdf", "Sam Alvarez",
                   ["LIGHTKEEPER DX", "ROOT CELLAR TWO", "PAPER KITES REDUX"], "normal"),
    "chen": ("ATL_A01_GAME405_RobinChen_GamePitch.pdf", "Robin Chen",
             ["MOTH KING", "TIDE CLOCK", "BONE ORCHARD", "SIGNAL LOST"], "normal"),
    "okafor": ("ATL_A01_GAME405_DeeOkafor_GamePitch.pdf", "Dee Okafor",
               ["GLASS FERRY", "NIGHT MARKET"], "normal"),
    "smithj": ("ATL_A01_GAME405_JordanSmith_GamePitch.pdf", "Jordan Smith",
               ["HOLLOW CROWN", "SALT ROADS", "TIN SOLDIER"], "normal"),
    "smitha": ("ATL_A01_GAME405_AverySmith_GamePitch.pdf", "Avery Smith",
               ["FERAL CITY", "QUIET HOURS", "SKY FARM"], "normal"),
    "ng": ("ATL_A01_GAME405_KaiNg_GamePitch.pdf", "Kai Ng",
           ["KITE FIGHT", "MOSS BATTALION", "LAST LAUNDROMAT"], "normal"),
    "mira": ("ATL_A01_GAME405_Mira_Pitching.pdf", "Mira Patel",
             ["DUST DEVILS", "OUTPOST NINE", "CANDLE WALTZ"], "normal"),
    "munoz": ("ATL_A01_GAME405_ElenaMunoz_GamePitch.pdf", "Elena Munoz",
              [["THE LAST TRAIN", "TO NOWHERE"], "COPPER BELLS", "WILD DRAFT"], "normal"),
    "rivera": ("ATL_A01_GAME405_JordanRivera_GamePitch.pdf", "Jordan Rivera",
               ["STORM CHOIR", "RUST BUCKET", "HALF MOON"], "collage"),
    "tanaka": ("ATL_A01_GAME405_ReiTanaka_GamePitch.pdf", "Rei Tanaka",
               ["PAPER TIGER", "NEON SHRINE", "ECHO DIVE"], "numbered"),
}
F = {k: v[0] for k, v in DECKS.items()}

ROSTER = [("Alvarez", "Sam"), ("Chen", "Robin"), ("Okafor", "Dee"),
          ("Smith", "Jordan"), ("Smith", "Avery"), ("Ng", "Kai"),
          ("Patel", "Mira"), ("Muñoz", "Elena"), ("Rivera", "Jordan"),
          ("Tanaka", "Rei"), ("Walsh", "Casey")]

# ---------- fixtures ----------

_n = [0]


def image(page, rect):
    """A distinct solid swatch each call, so PyMuPDF cannot dedupe images."""
    _n[0] += 1
    c = _n[0]
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 48, 48), False)
    pix.set_rect(pix.irect, ((c * 67) % 200 + 40, (c * 131) % 200 + 40, (c * 199) % 200 + 40))
    page.insert_image(pymupdf.Rect(*rect), stream=pix.tobytes("png"))


def text(page, rect, body, size):
    assert page.insert_textbox(pymupdf.Rect(*rect), body, fontsize=size) >= 0


def deck(path, name, titles, kind):
    doc = pymupdf.open()
    p = doc.new_page(width=W, height=H)
    p.insert_text((40, 120), name, fontsize=40)
    if kind == "collage":
        text(p, (40, 140, 330, 380), COLLAGE, 13)
        for r in GRID:
            image(p, r)
    else:
        p.insert_text((40, 160), "GAME 405 Pitch Deck", fontsize=20)
        image(p, (560, 300, 690, 380))

    p = doc.new_page(width=W, height=H)
    p.insert_text((40, 80), "About Me", fontsize=30)
    text(p, (40, 100, 380, 360), ABOUT, 13)
    image(p, (430, 50, 680, 360))
    p.insert_text((455, 210), "PERSONAL PHOTO", fontsize=22, color=(1, 1, 1))

    for n, title in enumerate(titles, 1):
        p = doc.new_page(width=W, height=H)
        y, size = 70, 34
        if kind == "numbered":
            p.insert_text((40, 95), f"0{n}", fontsize=72)
            y, size = 140, 28
        for line in title if isinstance(title, list) else [title]:
            p.insert_text((40, y), line, fontsize=size)
            y += size + 4
        p.insert_text((40, y), f"cozy survival | pitched by {name}", fontsize=12)
        text(p, (40, y + 12, 340, 395), BODY, 11)
        for r in GRID:
            image(p, r)

    p = doc.new_page(width=W, height=H)
    p.insert_text((40, 180), "Thank you!", fontsize=44)
    p.insert_text((40, 220), "Questions?", fontsize=20)
    doc.save(path)


def build(root):
    (root / "decks").mkdir(parents=True)
    for fname, name, titles, kind in DECKS.values():
        deck(root / "decks" / fname, name, titles, kind)
    # Blackboard gradebook export shape: UTF-16 TSV, quoted, Last/First first.
    rows = ['"Last Name"\t"First Name"\t"Username"\t"Student ID"']
    rows += [f'"{last}"\t"{first}"\t"x{i}"\t"TEST{i:04}"' for i, (last, first) in enumerate(ROSTER)]
    (root / "roster.xls").write_text("\r\n".join(rows) + "\r\n", encoding="utf-16")


def render(root, overrides):
    (root / "overrides.json").write_text(json.dumps(overrides))
    r = subprocess.run([sys.executable, str(RENDER),
                        "--decks", str(root / "decks"), "--out", str(root / "slides"),
                        "--roster", str(root / "roster.xls"),
                        "--manifest", str(root / "manifest.json"),
                        "--overrides", str(root / "overrides.json")],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"render_decks.py failed:\n{r.stderr}")
    m = json.loads((root / "manifest.json").read_text())
    return m, {s["file"]: s["title"] for s in m["slides"]}, set(m["needs_review"])


# ---------- checks ----------

failures = []


def check(ok, what):
    print(("  ok    " if ok else "  FAIL  ") + what)
    if not ok:
        failures.append(what)


def run_checks(root):
    slides = root / "slides"
    print("run 1: no overrides")
    m, titles, flagged = render(root, {})
    check(m["count"] == len(titles) == len(list(slides.glob("*.jpg"))),
          "every manifest entry is its own file on disk")
    check("About Me" not in titles.values(), "no About Me page published")
    check(F["okafor"] in flagged and not list(slides.glob("okafor_*"))
          and (root / "review" / Path(F["okafor"]).stem / "p2.jpg").exists(),
          "two-idea deck goes to review/ with every page, nothing to slides/")
    check({F["alvarez"], F["alvarez_v2"]} <= flagged and not list(slides.glob("alvarez_*")),
          "resubmission flags both decks and publishes neither")
    check(F["mira"] in flagged and titles.get("ng_idea1.jpg") == "KITE FIGHT",
          "filename without a last name is flagged, Kai Ng keeps ng_*")
    check(titles.get("smithj_idea1.jpg") == "HOLLOW CROWN"
          and titles.get("smitha_idea1.jpg") == "FERAL CITY",
          "shared last name resolved by first name")
    check(titles.get("munoz_idea1.jpg") == "THE LAST TRAIN TO NOWHERE",
          "wrapped title joined, accented roster name matched")
    check([titles.get(f"tanaka_idea{n}.jpg") for n in (1, 2, 3)]
          == ["PAPER TIGER", "NEON SHRINE", "ECHO DIVE"],
          "big idea numbers skipped when reading titles")
    check({F["chen"], F["rivera"]} <= flagged, "four-idea deck and collage title page flagged")

    print("run 2: page overrides, and tanaka_idea2 pulled")
    ov = {"pages": {F["okafor"]: [3, 4], F["chen"]: [3, 4, 5, 6], F["rivera"]: [3, 4, 5]},
          "pulled": ["tanaka_idea2"]}
    m, titles, flagged = render(root, ov)
    check([titles.get(f"okafor_idea{n}.jpg") for n in (1, 2)] == ["GLASS FERRY", "NIGHT MARKET"],
          "override publishes exactly the chosen pages")
    check("chen_idea4.jpg" in titles and "rivera_idea3.jpg" in titles,
          "override can publish four ideas, or confirm three")
    check("tanaka_idea2.jpg" not in titles and titles.get("tanaka_idea3.jpg") == "ECHO DIVE",
          "pulled slide not rendered, the others keep their numbers")
    check(any("tanaka_idea2.jpg: on the pulled list" in p for p in m["problems"]),
          "pulled file still in slides/ is reported")

    print("run 3: after deleting the pulled file")
    (slides / "tanaka_idea2.jpg").unlink()
    m, titles, flagged = render(root, ov)
    check(not (slides / "tanaka_idea2.jpg").exists()
          and not any("tanaka_idea2" in p for p in m["problems"]),
          "takedown survives the next routine run")
    check(flagged == {F["alvarez"], F["alvarez_v2"], F["mira"]},
          "only the decks that need a human are left flagged")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", help="empty folder to build and render in, kept afterward")
    args = ap.parse_args()
    if args.keep:
        root = Path(args.keep)
        if root.exists() and any(root.iterdir()):
            sys.exit(f"{root} is not empty")
        build(root)
        run_checks(root)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            run_checks(Path(tmp))
    print()
    if failures:
        sys.exit(f"{len(failures)} checks failed.")
    print("all checks passed.")


if __name__ == "__main__":
    main()
