"""Build the hand-count vote sheet from the manifest and the placement ledger.

One 8.5 x 11 page: a map of the wall, five vote boxes, and a write-in.

The ballot keys on the wall grid, not on slide titles. Titles come out of the
decks and a third of them are unusable: duplicated across a student's three
ideas, a single glyph, or a whole paragraph. A cell code like C2 is short,
unambiguous, and a student can find it by counting across and down.

    python3 tools/make_ballot.py

Writes ballot.html. Render it with Chrome:

    chrome --headless --disable-gpu --print-to-pdf=ballot.pdf --no-pdf-header-footer ballot.html
"""

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COL0, ROW0 = 80, 330
COL_STEP, ROW_STEP = 336, 196
COLS = "ABCDEFGHI"
VOTES = 5


def cell_code(box):
    """The wall box [x, y, w, h] as a grid code like C2."""
    col = (box[0] - COL0) // COL_STEP
    row = (box[1] - ROW0) // ROW_STEP + 1
    return f"{COLS[col]}{row}"


def read_wall():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    placed = json.loads((ROOT / "placements.json").read_text(encoding="utf-8"))["placed"]
    wall = {}
    for slide in manifest["slides"]:
        key = slide["file"].rsplit(".", 1)[0]
        if key not in placed:
            continue
        code = cell_code(placed[key]["box"])
        wall[code] = {"name": slide["name"], "last": slide["name"].split()[-1], "idea": slide["idea"]}
    return wall


def grid_rows(wall):
    """Only the rows that hold slides, so an empty bottom row is not printed."""
    rows = sorted({int(code[1:]) for code in wall})
    return [[(f"{c}{r}", wall.get(f"{c}{r}")) for c in COLS] for r in rows]


def designer_index(wall):
    by_name = {}
    for code, slide in wall.items():
        by_name.setdefault(slide["last"], []).append((slide["idea"], code))
    return [(last, [code for _, code in sorted(codes)]) for last, codes in sorted(by_name.items())]


CSS = """
@page { size: 8.5in 11in; margin: 0.45in; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  color: #111; font-size: 9pt; line-height: 1.3;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1 { font-size: 17pt; letter-spacing: 0.02em; margin: 0; text-transform: uppercase; }
h2 {
  font-size: 8pt; letter-spacing: 0.14em; text-transform: uppercase;
  margin: 0 0 4pt; color: #444; font-weight: 700;
}
.rule { border-top: 1.5pt solid #111; margin: 5pt 0 8pt; }
.thin { border-top: 0.5pt solid #bbb; margin: 8pt 0; }

.top { display: flex; justify-content: space-between; align-items: flex-end; gap: 18pt; }
.sub { font-size: 8.5pt; color: #444; margin-top: 2pt; }
.who { text-align: right; font-size: 8pt; color: #444; white-space: nowrap; }
.who span { display: inline-block; border-bottom: 0.75pt solid #111; margin-left: 5pt; }
.who .nm { width: 150pt; }
.who .dt { width: 66pt; }

.how { display: flex; gap: 10pt; margin-bottom: 9pt; }
.how div {
  flex: 1; border: 0.5pt solid #ccc; border-left: 2.5pt solid #111;
  padding: 4pt 6pt; font-size: 8pt; line-height: 1.35;
}
.how b { display: block; font-size: 7.5pt; letter-spacing: 0.1em; text-transform: uppercase; }

table.wall { width: 100%; border-collapse: collapse; table-layout: fixed; }
table.wall th {
  font-size: 7.5pt; color: #666; font-weight: 700; padding: 0 0 2pt;
  letter-spacing: 0.06em;
}
table.wall th.rh, table.wall td.rh {
  width: 15pt; font-size: 8pt; color: #666; text-align: center; border: none;
}
table.wall td {
  border: 0.5pt solid #999; height: 41pt; padding: 3pt 3pt 2pt; vertical-align: top;
}
table.wall td.empty { background: #f4f4f4; border-style: dashed; border-color: #ccc; }
.code { font-size: 7pt; color: #777; letter-spacing: 0.06em; }
.last { font-size: 8.5pt; font-weight: 700; line-height: 1.1; margin-top: 1pt;
        word-break: break-word; hyphens: auto; }
.idea { font-size: 7pt; color: #555; margin-top: 1pt; }

.votes { margin-top: 3pt; }
.vrow { display: flex; align-items: stretch; gap: 8pt; margin-bottom: 6pt; }
.vnum { width: 13pt; font-size: 9pt; color: #888; padding-top: 9pt; text-align: right; }
.vbox {
  width: 74pt; height: 31pt; border: 1.25pt solid #111;
  display: flex; align-items: center; justify-content: center;
}
.vbox .hint { font-size: 6.5pt; color: #aaa; letter-spacing: 0.1em; }
.vline { flex: 1; border-bottom: 0.75pt solid #999; position: relative; }
.vline .hint {
  position: absolute; top: 100%; left: 3pt; padding-top: 1.5pt;
  font-size: 6.5pt; color: #aaa; letter-spacing: 0.08em;
}
.wi .vbox { border-style: dashed; }

.index { font-size: 7.5pt; color: #333; columns: 3; column-gap: 16pt; }
.index div { break-inside: avoid; margin-bottom: 1.5pt; }
.index b { font-weight: 700; }
.index span { color: #666; letter-spacing: 0.06em; }
.foot { font-size: 7pt; color: #888; margin-top: 7pt; }
"""


def build(wall):
    rows = grid_rows(wall)
    head = "".join(f'<th>{c}</th>' for c in COLS)
    body = []
    for row in rows:
        cells = []
        for code, slide in row:
            if slide is None:
                cells.append('<td class="empty"></td>')
                continue
            cells.append(
                f'<td><div class="code">{code}</div>'
                f'<div class="last">{html.escape(slide["last"])}</div>'
                f'<div class="idea">idea {slide["idea"]}</div></td>'
            )
        num = row[0][0][1:]
        body.append(f'<tr><td class="rh">{num}</td>{"".join(cells)}</tr>')

    vote_rows = "".join(
        f'<div class="vrow"><div class="vnum">{i}</div>'
        f'<div class="vbox"><span class="hint">CODE</span></div>'
        f'<div class="vline"><span class="hint">DESIGNER, AND WHAT THE IDEA IS</span></div></div>'
        for i in range(1, VOTES + 1)
    )

    index = "".join(
        f'<div><b>{html.escape(last)}</b> <span>{" ".join(codes)}</span></div>'
        for last, codes in designer_index(wall)
    )

    count = len(wall)
    designers = len({s["last"] for s in wall.values()})

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>GAME 405 Idea Wall Vote</title>
<style>{CSS}</style>
</head>
<body>

<div class="top">
  <div>
    <h1>Idea Wall Vote</h1>
    <div class="sub">GAME 405 &middot; Senior Studio &middot; {count} ideas from {designers} designers</div>
  </div>
  <div class="who">
    Name <span class="nm"></span><br /><br />
    Date <span class="dt"></span>
  </div>
</div>
<div class="rule"></div>

<div class="how">
  <div><b>1 &middot; Browse</b>Take the period. Walk the wall while people pitch. Every idea in the room is up there.</div>
  <div><b>2 &middot; Pick five</b>Five votes, no ranking, no order. Five different ideas. You may vote for your own.</div>
  <div><b>3 &middot; Write the code</b>Find the tile on the map below, copy its code into a box. Add the designer so I can read it back.</div>
</div>

<h2>The wall &middot; count across for the letter, down for the number</h2>
<table class="wall">
  <tr><th class="rh"></th>{head}</tr>
  {"".join(body)}
</table>

<div class="thin"></div>

<h2>My votes &middot; five from the wall, one write&#8209;in</h2>
<div class="votes">{vote_rows}</div>

<div class="vrow wi">
  <div class="vnum">6</div>
  <div class="vbox"><span class="hint">WRITE&#8209;IN</span></div>
  <div class="vline"><span class="hint">AN IDEA THAT IS NOT ON THE WALL, OR TWO OF THESE CROSSED TOGETHER</span></div>
</div>

<div class="thin"></div>

<h2>By designer</h2>
<div class="index">{index}</div>

<div class="foot">Hand counted. Turn this in before you leave.</div>

</body>
</html>
"""


def main():
    wall = read_wall()
    if not wall:
        raise SystemExit("nothing on the wall yet, run the placement step first")
    out = ROOT / "ballot.html"
    out.write_text(build(wall), encoding="utf-8")
    designers = len({s["last"] for s in wall.values()})
    print(f"wrote {out.name}: {len(wall)} ideas by {designers} designers, {VOTES} votes and a write-in")
    print("render it with:")
    print('  "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless --disable-gpu \\')
    print("    --print-to-pdf=ballot.pdf --no-pdf-header-footer ballot.html")


if __name__ == "__main__":
    main()
