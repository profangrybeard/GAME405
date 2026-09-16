"""Build the hand-count vote paperwork from the manifest.

Two 8.5 x 11 sheets, both from the same list of names so their rows line up:

  ballot.html   one per student. Check five, plus one picked off the wall.
  tally.html    one for the room. A box per possible vote, marked as you read.

It reads names and nothing else. Not the ledger, not the grid, not the slide
titles. The board moves every time decks arrive, and a sheet that names cells
or positions is wrong the moment it does. A name is stable, and a new designer
is one more row, and the rows tighten as the roster grows so it stays one page.

Both sheets print blank rows out to the size of the class, so a student who
walks in the morning of with three slides can still be voted for by name.

    python3 tools/make_ballot.py

Render them with Chrome:

    chrome --headless --disable-gpu --print-to-pdf=ballot.pdf --no-pdf-header-footer ballot.html
    chrome --headless --disable-gpu --print-to-pdf=tally.pdf --no-pdf-header-footer tally.html

`--fake N out.html` builds a ballot for N invented designers, and `--fake-tally
N out.html` a tally, to check a bigger roster still lands on one page.
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

# Nobody can collect more votes than there are people in the room to cast them.
MARKS = ROSTER
WALL_PICKS = 8  # lines to tally the off-the-wall write-ins, which are free text

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

# Same idea for the tally sheet, counting the write-in lines too. Past the
# roomiest tier the total box shrinks as well, since padding alone runs out.
#              up to   pad   total box
TALLY_SIZES = [(31, "2", "13"),
               (34, "1", "13"),
               (38, "0", "13")]


def metrics(n):
    for limit, box, pad, name, lines in SIZES:
        if n <= limit:
            return {"BOX": box, "PAD": pad, "NAME": name, "lines": lines}
    raise SystemExit(f"{n} designers is more than one page can hold, split the sheet")


def tally_metrics(n):
    for limit, pad, box in TALLY_SIZES:
        if n <= limit:
            return {"PAD": pad, "TOTBOX": box}
    raise SystemExit(f"{n} rows is more than one tally page can hold, split the sheet")


def designers():
    """Everyone with slides up, by last name, with how many ideas they pitched."""
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    counts = {}
    for slide in manifest["slides"]:
        counts[slide["name"]] = counts.get(slide["name"], 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[0].split()[-1])


def blanks_for(people):
    return max(ROSTER - len(people), SPARE)


SHARED_CSS = """
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
.foot { font-size: 8pt; color: #888; margin-top: 10pt; display: flex; justify-content: space-between; }
"""

BALLOT_CSS = SHARED_CSS + """
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
"""

TALLY_CSS = SHARED_CSS + """
.check {
  border: 1.25pt solid #111; padding: 5pt 9pt; margin-bottom: 9pt;
  font-size: 9pt; white-space: nowrap;
}
.check b { font-size: 8pt; letter-spacing: 0.12em; text-transform: uppercase; }
.check .cell {
  display: inline-block; border-bottom: 0.75pt solid #111;
  width: 42pt; height: 12pt; margin: 0 3pt;
}
.check .why {
  display: block; color: #777; font-size: 7.5pt; margin-top: 3pt; white-space: normal;
}

/* Explicit columns. With table-layout fixed the first row would otherwise set
   the widths, and the header row has none, so Total ate a third of the sheet. */
table.tal { width: 100%; border-collapse: collapse; table-layout: fixed; }
table.tal th {
  font-size: 6.5pt; color: #999; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; text-align: left; padding-bottom: 3pt;
}
table.tal th.t { text-align: center; }
table.tal td { padding: __PAD__pt 0; border-bottom: 0.5pt solid #e2e2e2; }
td.nm { font-size: 9.5pt; font-weight: 600; }
td.nm.fill div { border-bottom: 0.75pt solid #999; height: 12pt; }
td.wide div { border-bottom: 0.75pt solid #999; height: 13pt; }
td.marks { padding-left: 5pt; padding-right: 7pt; }
.strip { display: flex; }
.strip i { border: 0.4pt solid #cfcfcf; border-right: none; height: 13pt; flex: 1; }
.strip i:last-child { border-right: 0.4pt solid #cfcfcf; }
.strip i.five { border-left-width: 1pt; border-left-color: #777; }
td.tot div { border: 1.25pt solid #111; height: __TOTBOX__pt; }
.grp { font-size: 7pt; letter-spacing: 0.1em; text-transform: uppercase; color: #444;
       font-weight: 700; padding: 8pt 0 3pt; }
"""

# Name, the run of boxes, the total. The write-in table keeps the same last
# column so its totals sit under the ones above.
COLS_MAIN = '<colgroup><col style="width:116pt" /><col /><col style="width:34pt" /></colgroup>'
COLS_WALL = '<colgroup><col /><col style="width:34pt" /></colgroup>'


def ballot(people):
    blanks = blanks_for(people)
    m = metrics(len(people) + blanks)
    css = BALLOT_CSS
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


def strip(n):
    """A run of boxes, one per possible vote, gated every five."""
    return '<div class="strip">' + "".join(
        f'<i class="{"five" if i and i % 5 == 0 else ""}"></i>' for i in range(n)
    ) + "</div>"


def tally(people):
    blanks = blanks_for(people)
    tm = tally_metrics(len(people) + blanks + WALL_PICKS)
    css = TALLY_CSS
    for key in ("PAD", "TOTBOX"):
        css = css.replace(f"__{key}__", tm[key])

    rows = "".join(
        f'<tr><td class="nm">{html.escape(name)}</td>'
        f'<td class="marks">{strip(MARKS)}</td>'
        f'<td class="tot"><div></div></td></tr>'
        for name, _ in people
    )
    blank_rows = (
        f'<tr><td class="nm fill"><div></div></td>'
        f'<td class="marks">{strip(MARKS)}</td>'
        f'<td class="tot"><div></div></td></tr>'
    ) * blanks
    wall_rows = (
        '<tr><td class="wide"><div></div></td>'
        '<td class="tot"><div></div></td></tr>'
    ) * WALL_PICKS

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>GAME 405 Idea Wall Tally</title>
<style>{css}</style>
</head>
<body>

<div class="top">
  <div>
    <h1>Idea Wall Tally</h1>
    <div class="sub">GAME 405 &middot; Senior Studio &middot; one box per vote, gated every five</div>
  </div>
  <div class="who">Date <span></span></div>
</div>
<div class="rule"></div>

<div class="check">
  <b>Ballots in</b><span class="cell"></span>&times; {VOTES} =<span class="cell"></span>checks.
  Totals below add up to<span class="cell"></span>
  <span class="why">Those two should match. If they do not, a ballot has the wrong number of checks, or a row got missed.</span>
</div>

<table class="tal">
  {COLS_MAIN}
  <tr>
    <th>Pitched</th>
    <th>One box per vote</th>
    <th class="t">Total</th>
  </tr>
  {rows}
  {blank_rows}
</table>

<div class="grp">Off the wall &middot; the write-ins, one line each</div>
<table class="tal">
  {COLS_WALL}
  {wall_rows}
</table>

<div class="foot">
  <span>Five jam teams, two go to production.</span>
  <span>miro.com/app/board/uXjVHoWCO8w=</span>
</div>

</body>
</html>
"""


def main():
    people = designers()
    if not people:
        raise SystemExit("no slides in the manifest yet, run the render step first")
    (ROOT / "ballot.html").write_text(ballot(people), encoding="utf-8")
    (ROOT / "tally.html").write_text(tally(people), encoding="utf-8")
    blanks = blanks_for(people)
    print(f"wrote ballot.html: {len(people)} named and {blanks} blank, "
          f"check {VOTES} and one off the wall")
    print(f"wrote tally.html: the same {len(people) + blanks} rows, "
          f"{MARKS} boxes each, plus {WALL_PICKS} write-in lines")


if __name__ == "__main__":
    fake = {"--fake": ballot, "--fake-tally": tally}
    flag = next((a for a in sys.argv if a in fake), None)
    if flag:
        at = sys.argv.index(flag)
        count = int(sys.argv[at + 1])
        people = [(f"Firstname Lastname{i:02d}", 3) for i in range(count)]
        Path(sys.argv[at + 2]).write_text(fake[flag](people), encoding="utf-8")
        print(f"fake {flag[6:] or 'ballot'} sheet for {count} designers")
    else:
        main()
