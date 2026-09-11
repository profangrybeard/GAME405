# CLAUDE.md

Working notes for Claude Code on the GAME 405 class repo.

## Shape of this repo

A class repo, not a project repo. It will hold several subprojects over the
quarter. Each gets its own folder, README, and `tools/`. Nothing but shared
config lives at the root.

Current subprojects:
- `idea-wall/` renders pitch deck PDFs into slides for the class idea wall.
  Board: https://miro.com/app/board/uXjVHoWCO8w=/

Served by GitHub Pages from `main`, root folder, so `idea-wall/` is published
at `/idea-wall/`.

## Traps worth not rediscovering

**Never add Git LFS.** GitHub Pages does not serve LFS-tracked files, it serves
the pointer. A slide tracked in LFS reaches Miro as ~130 bytes of text and the
tile renders broken. If a subproject genuinely needs large binaries, propose a
separate repo, do not migrate this one.

**Do not delete `.nojekyll`.** It is empty and it is supposed to be. Without it
Pages runs a Jekyll build that skips underscore-prefixed paths.

**Published filenames are load-bearing.** The Miro board references slides by
filename. Renaming a published file breaks a tile on the wall with no error
anywhere. Do not rename or restructure `idea-wall/slides/` casually.

**The Pages URL is case-sensitive.** The site is
`https://profangrybeard.github.io/GAME405/`. Lowercase `/game405/` is a 404, so
a slide URL typed into Miro by hand has to keep the capitals or the tile dies
with no error anywhere.

**Verify after publishing.** `idea-wall/tools/verify_publish.py` checks every
manifest entry for a 200, an image content type, and a plausible byte count.
Run it after a push with new content and before anyone builds the board.

## Privacy rules, not preferences

- Never commit anything under `idea-wall/decks/`. Source decks contain pages
  that are deliberately unpublished, including personal photos.
- Never commit a roster export. They carry student IDs. The gitignore covers
  `*.xls` and `gc_*`, but check before any `git add -A`.
- Only renderer-selected pages get published. A page that was not selected was
  not selected on purpose.
- Takedown requests: see NOTICE.md. It is three steps. The third, the Miro
  board, runs through the placement step and needs Tim's OK before anything is
  deleted. Miro keeps its own copy of every slide, so removing the file from
  Pages does not take it off the wall. Say so out loud every time.

## The idea-wall loop

```bash
cd idea-wall
python3 tools/render_decks.py --decks decks/ --out slides/ --roster <path>
```

Then read `manifest.json`. A run is done when `problems` and `needs_review` are
both empty. If they are not, name the specific decks and say what you plan to
do before committing anything. A flagged deck publishes nothing. Every page of
it lands in `review/`, which is gitignored, so the right pages can be chosen.

When a deck picks the wrong pages, do not loosen the scoring thresholds to make
that one deck pass. That trades one visible problem for invisible ones across
the rest. Add the deck to `pages` in `overrides.json` instead. A deck flagged
for its filename gets renamed in `decks/` to carry the student's first and last
name, not an override.

`tools/check_renderer.py` runs the renderer against synthetic decks covering
every failure seen so far. Run it after any change to `render_decks.py`.

## The placement loop

After the render loop is done, pushed, and `verify_publish.py` passes:

```bash
cd idea-wall
python3 tools/place_slides.py
```

It works out the whole wall from the manifest: the grid, a 16:9 frame, where
each slide goes, the placeholder tiles that keep the wall at 63 or more, and
the counters. It writes `placement_plan.json` and the SVG steps in
`placement_svg/`. Send the steps through the claude.ai Miro connector's
`canvas_update_from_svg`, one call at a time, in the order the script prints.
Calls sent side by side race on the frame. The plugin Miro connector is signed
into a different org and cannot see this board.

Miro will not move or re-point an image inside a frame, and ignores position
changes to text inside one. So an item that is already right is kept, and
anything that has to change is deleted and created again in its new place.

- `1_grow_1_resize.svg`, then `1_grow_2_pin.svg`. Only when the wall grows.
  Miro resizes a frame around its center, so the second call pins it back.
- `2_images_NN.svg` and `3_tiles.svg`: new slides and new placeholder tiles.
- `4_needs_ok.svg` deletes the old copy of everything that changed and creates
  it again: a slide that moved or swapped blur, a placeholder that moved or
  that a slide took over, a pulled slide, header text that moved. Show Tim the
  list and send it only with Tim's OK. On a no, stop and re-plan. The later
  steps assume it went through.
- `5_shrink_1_move.svg`, then `5_shrink_2_resize.svg`. Only when the wall
  shrinks. The frame moves by half the difference first, so the resize lands it
  back on its corner.
- `6_header.svg`: title, byline, and counters.
- Then read the wall frame back with `canvas_read_as_svg` (widget
  `3458764683429206119`), save the SVG to `placement_read.svg`, and run
  `python3 tools/place_slides.py record placement_read.svg`. It checks that
  every slide and placeholder sits exactly on its box, nothing is doubled,
  nothing old was left behind, and the header reads right, then updates
  `placements.json`. Commit that file.

`place_slides.py adopt placement_read.svg` teaches the ledger about placeholder
tiles it did not create. It was run once, for the switch from the hand-built
wall.

`python3 tools/place_slides.py blur on` makes the next run show every slide as
its blurred twin from `slides/blur/`, and `blur off` swaps the sharp slides
back. Flipping it is a run of this loop, not an instant switch inside Miro.

The counters are text. Miro cannot count on its own, so the placement step
rewrites them from the manifest on every run, and `record` reads them back.

`python3 tools/place_slides.py check` runs the layout against many wall sizes:
every frame 16:9, every slide inside the margins, no designer's slides touching.
Run it after any change to the script.

## Known state, September 11 2026

- Roster: 22 students in the Blackboard export, plus Yoseph Arafa under
  `extra_students` in `overrides.json`, so 23 and up to 69 pitches. Students
  were still adding, so treat the count as a moving number.
- The wall sizes itself to the delivered pitches. Since the switch on September
  11 it shows Lex Broughton's 3 slides and 60 placeholders on the 63 floor,
  blurred for demos (`"blur": true` in `overrides.json`). `blur off` and a run
  of the placement loop is the reveal.
- Output: JPEG, 1920 wide, quality 92, roughly 350KB each.
- `title` in the manifest is the largest type on the page. The wall does not
  show it, since each slide carries its own title, but it is worth a glance.

## Style

Tim writes plainly. No em dashes in docs, comments, or commit messages. Lead
with what works before naming gaps. Be specific: the exact file, the exact
line, the exact fix. No hedging.
