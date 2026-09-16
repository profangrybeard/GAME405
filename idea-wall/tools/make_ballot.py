"""Build the hand-count vote sheet from the manifest.

One 8.5 x 11 page: everyone who pitched, five checkboxes worth of votes, and
one more picked off the wall.

It reads names and nothing else. Not the ledger, not the grid, not the slide
titles. The board moves every time decks arrive, and a sheet that names cells
or positions is wrong the moment it does. A name is stable, and a new designer
is one more row, and the rows tighten as the roster grows so it stays one page.

It also prints blank rows out to the size of the class, so a student who walks
in the morning of with three slides can still be voted for by name.

    python3 tools/make_ballot.py

Writes ballot.html. Render it with Chrome:

    chrome --headless --disable-gpu --print-to-pdf=ballot.pdf --no-pdf-header-footer ballot.html

`--fake N out.html` builds a sheet for N invented designers, to check a bigger
roster still lands on one page.
"""

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOTES = 5

# A row for every student in the class, named when we have their deck and blank
# when we do not. Someone walks in the morning of with three slides and nobody
# can vote for them unless there is a line to write them on.
ROSTER = 23  # 22 in the Blackboard export plus Yoseph Arafa in overrides.json
SPARE = 2  # somebody always registers late

# One page, however many people have pitched. The roster only grows, so the
# rows tighten as it does instead of spilling onto a second sheet.
# Measured, not guessed: each row is the loosest spacing that still prints on
# one page at that ceiling, counting the blanks. Re-measure if the header, the
# walk-in band, or the wall block changes. With ROSTER at 23 only the last two
# tiers come up; the roomier ones are there for a smaller class.
#          up to   box   pad     name    lines under the wall pick
SIZES = [(16, "21", "4.5", "12", 2),
         (20, "18", "3", "11", 2),
         (24, "16", "2", "10.5", 1),
         (30, "14", "0.5", "9.5", 1)]


def metrics(n):
    for limit, box, pad, name, lines in SIZES:
        if n <= limit:
            return {"BOX": box, "PAD": pad, "NAME": name, "lines": lines}
    raise SystemExit(f"{n} designers is more than one page can hold, split the sheet")


def designers():
    """Everyone with slides up, by last name, with how many ideas they pitched."""
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    counts = {}
    for slide in manifest["slides"]:
        counts[slide["name"]] = counts.get(slide["name"], 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[0].split()[-1])


CSS = """
@page { size: 8.5in 11in; margin: 0.5in; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  color: #111; font-size: 10pt; line-height: 1.35;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1 { font-size: 21pt; letter-spacing: 0.01em; margin: 0; text-transform: uppercase; }
h2 {
  font-size: 9pt; letter-spacing: 0.16em; text-transform: uppercase;
  margin: 0; font-weight: 700;
}
h2 .lede { letter-spacing: 0; text-transform: none; font-weight: 400; color: #666; }

.top { display: flex; justify-content: space-between; align-items: flex-end; gap: 20pt; }
.sub { font-size: 9.5pt; color: #555; margin-top: 3pt; }
.who { text-align: right; font-size: 8.5pt; color: #555; white-space: nowrap; }
.who span {
  display: inline-block; border-bottom: 0.75pt solid #111;
  margin-left: 6pt; width: 160pt;
}
.rule { border-top: 1.5pt solid #111; margin: 6pt 0 12pt; }
.band { margin-bottom: 6pt; }
.walkins { margin: 7pt 0 4pt; }
.walkins h2 { color: #444; }

ol.picks { list-style: none; margin: 0; padding: 0; }
ol.picks li { display: flex; align-items: center; gap: 12pt; padding: __PAD__pt 0; }
ol.picks li + li { border-top: 0.5pt solid #e2e2e2; }
.box { width: __BOX__pt; height: __BOX__pt; border: 1.25pt solid #111; flex: none; }
/* One fixed height for both kinds of row, so a blank measures like a name. */
.nm2 {
  font-size: __NAME__pt; font-weight: 600; width: 168pt; flex: none;
  height: 14pt; display: flex; align-items: center;
}
.nm2.fill { border-bottom: 0.75pt solid #999; }
.ideas { font-size: 7.5pt; color: #999; width: 44pt; flex: none; letter-spacing: 0.04em; }
.note { flex: 1; border-bottom: 0.5pt dotted #bbb; height: 15pt; }

.wall { border: 1.25pt solid #111; padding: 9pt 11pt 10pt; margin-top: 12pt; }
.wall .line { border-bottom: 0.75pt solid #999; height: 22pt; margin-top: 7pt; }
.wall .lbl { font-size: 7pt; color: #999; letter-spacing: 0.1em; text-transform: uppercase; }
.foot { font-size: 8pt; color: #888; margin-top: 10pt; display: flex; justify-content: space-between; }
"""


def build(people):
    blanks = max(ROSTER - len(people), SPARE)
    m = metrics(len(people) + blanks)
    css = CSS
    for key in ("BOX", "PAD", "NAME"):
        css = css.replace(f"__{key}__", m[key])

    rows = "".join(
        f'<li><div class="box"></div>'
        f'<div class="nm2">{html.escape(name)}</div>'
        f'<div class="ideas">{n} idea{"s" if n != 1 else ""}</div>'
        f'<div class="note"></div></li>'
        for name, n in people
    )
    blank_rows = (
        '<li><div class="box"></div>'
        '<div class="nm2 fill"></div>'
        '<div class="ideas"></div>'
        '<div class="note"></div></li>'
    ) * blanks
    wall_lines = '<div class="line"></div>' * m["lines"]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>GAME 405 Idea Wall Vote</title>
<style>{css}</style>
</head>
<body>

<div class="top">
  <div>
    <h1>Idea Wall Vote</h1>
    <div class="sub">GAME 405 &middot; Senior Studio &middot; five pitches, plus one off the wall</div>
  </div>
  <div class="who">Name <span></span></div>
</div>
<div class="rule"></div>

<div class="band">
  <h2>Check five &nbsp;<span class="lede">Any five. No ranking. Your own counts. The line on the right is yours if you want it.</span></h2>
</div>

<ol class="picks">{rows}</ol>

<div class="walkins">
  <h2>Pitched today, not on the wall &nbsp;<span class="lede">Write the name. Their work landed after the wall went up, so vote for them here.</span></h2>
</div>

<ol class="picks">{blank_rows}</ol>

<div class="wall">
  <h2>And one off the wall &nbsp;<span class="lede">Browse while people pitch. Anything that is not one of the {VOTES} above.</span></h2>
  {wall_lines}
  <div class="lbl">Whose idea, and what it is</div>
</div>

<div class="foot">
  <span>Hand counted. Turn it in before you leave.</span>
  <span>miro.com/app/board/uXjVHoWCO8w=</span>
</div>

</body>
</html>
"""


def main():
    people = designers()
    if not people:
        raise SystemExit("no slides in the manifest yet, run the render step first")
    out = ROOT / "ballot.html"
    out.write_text(build(people), encoding="utf-8")
    blanks = max(ROSTER - len(people), SPARE)
    print(f"wrote {out.name}: {len(people)} named and {blanks} blank, "
          f"check {VOTES} and one off the wall")


if __name__ == "__main__":
    if "--fake" in sys.argv:
        at = sys.argv.index("--fake")
        count = int(sys.argv[at + 1])
        people = [(f"Firstname Lastname{i:02d}", 3) for i in range(count)]
        Path(sys.argv[at + 2]).write_text(build(people), encoding="utf-8")
        print(f"fake sheet for {count} designers")
    else:
        main()
