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
- Takedown requests: see NOTICE.md. It is three steps, and the third one, the
  Miro board, has no automation. Say so out loud every time.

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

## Known state, September 11 2026

- Roster: 22 students, so 66 idea slides expected. Students were still adding,
  so treat the count as a moving number.
- The Miro board has 69 placeholder tiles named `studentNN_ideaN`, which leaves
  three spare. Tiles get renamed to `lastname_ideaN` as decks arrive.
- Output: JPEG, 1920 wide, quality 92, roughly 350KB each.
- `title` in the manifest is the largest type on the page. It becomes the tile
  label, so a wrong title is a visible error on a classroom TV.

## Style

Tim writes plainly. No em dashes in docs, comments, or commit messages. Lead
with what works before naming gaps. Be specific: the exact file, the exact
line, the exact fix. No hedging.
