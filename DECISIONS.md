# Idea Wall: decisions

A record of what was settled and why, so the project does not get relitigated
every time a new session starts.

If you are an AI assistant working on this: read this file before proposing
anything. Most of the obvious suggestions have already been made, argued, and
rejected for stated reasons. Re-proposing them costs Tim time and tells him you
did not read.

Written September 11 2026, and updated the same day after the pipeline test.
Anything not listed here is genuinely open.

---

## The goal, in Tim's words

> I am asking them to do work they will not present. I want that work to live on
> and be referenceable. I also require the scope be visible. We are going from 60
> plus ideas to 2. I want that process to be visible on my class room TV. I want
> to walk in the Monday after AF with the board and impress everyone with their
> collaboration right out of the gate.

Three things follow from that, and every design decision traces back to one of
them:

1. **Unpresented work survives.** Each student pitches three ideas. Five reach
   jam teams, two reach production. The other sixty-odd do not disappear.
2. **Scope is legible.** The volume of what the room made in one week is the
   point, and it should be readable from across a room.
3. **Monday is a reveal.** The wall is up before Tim says anything.

The wall is a display artifact. It is not a participation surface, not a
collaboration tool, and not a place students edit.

---

## Decided and closed

**Miro, not a custom build.** Tim usually prefers custom tools and explicitly
did not want one here. Miro is a mosaic by default, zoom is the mechanism for
looking closely at a single slide, and frames give a presentation surface for
the TV. The board is live and already linked in Blackboard.

Board: https://miro.com/app/board/uXjVHoWCO8w=/

**A mosaic, not a funnel.** Sixty-nine tiles tiled edge to edge, all at full
strength, all in the same plane. The 5 and the 2 are marks added on top later,
never subtractions from the field.

**Students' own slide art, not a typeset system.** Tim: "We need their art. The
mess is the point." Do not normalize, restyle, crop, or re-typeset student
slides.

**Shuffled placement, not grouped by designer.** Tim's reason: grouping puts a
designer's three slides adjacent, and since they share a deck background that
produces visible color blocks. Placement uses a fixed stride of 23 across a
9-column grid, which guarantees zero same-author adjacency including diagonals.
Verified across all 69 positions. Do not replace this with a random shuffle;
random reintroduces the adjacency.

**Grid geometry.** 9 columns. Tiles 320x180 with a 16px gutter, mosaic origin at
(80, 170) inside the frame. Frame is 3168x1782, which is exactly 16:9 so
presenting to it fills a classroom TV with no letterboxing. Last row is ragged
and deliberately not centered.

**Palette matches the GAME 405 Studio Board.** Ground #101B2A, tile #1E2E45,
edge #2C3E56, cream #EAE6DC, slate #8FA0B6, amber #F0A93B. The wall should read
as the same object as the board students already open.

**Filenames are `lastname_ideaN`.** Roster-derived, lowercase, punctuation
stripped, first initial appended on duplicate last names. These match Miro tile
names one to one. Renaming a published file breaks a tile with no error
anywhere.

**PDFs in, JPEGs out, handled by us.** Tim: "We are taking their pdfs and
handling this formatting on our own." Students submit decks as they already
planned. 1920 wide, quality 92, roughly 350KB per slide.

**Public repo, with consent and a takedown path.** Pages has to be public for
Miro to fetch images. Tim is telling the class their idea slides go on a public
wall and that they can email to have one pulled. Only renderer-selected idea
slides are published. Source decks never leave his machine. See NOTICE.md.

**Class repo, not a project repo.** `game405` with `idea-wall/` as the first
subproject. Expected to hold more subprojects this quarter.

---

## Decided September 11, after the pipeline test

**All Miro. The board is the only display.** Tim: "my expectation all along was
a miro board product." The standalone contact sheet at `/idea-wall/` and the
repo landing page were removed the same day. The wall is presented from the
Miro frame and nowhere else.

**Pages is the image host and nothing more.** Tim: "we are going all Miro so
Pages is not necessary beyond being an image host for our pipeline." Slides are
pushed to Pages, and Miro fetches each one from its Pages URL when it is placed.
The slides being public is fine. Tim has that handled.

**Why a Pages URL and not a direct upload.** Both routes were run back to back
on September 11 with Lex Broughton's deck. Both put each slide exactly on its
tile, and both times Miro stored its own copy, byte-identical to the rendered
JPEG. So the wall does not depend on Pages once a slide is placed. Placing from
a URL takes one call per slide against three for an upload, has no upload slot
that expires after ten minutes, and leaves git history as the record of what was
published.

**Placement is a pipeline step, not hand work.** `idea-wall/tools/place_slides.py`
plans every placement and keeps the ledger in `idea-wall/placements.json`.
Claude carries out the plan through the claude.ai Miro connector and records
each image back. A second run with nothing new does nothing, so it is safe to
re-run.

**Slots are first come and never reshuffled.** Each student owns one slot from 1
to 23, and a new student takes the lowest free one. A tile name on the board is
load-bearing, and the stride of 23 makes every slot equal, so reordering gains
nothing and risks a broken tile.

**Tiles are renamed when their slide is placed.** `studentNN_ideaN` becomes
`lastname_ideaN` in the same step that puts the image on it. First done for Lex
Broughton, slot 1, on September 11, with Tim's approval.

**Per-deck page overrides exist.** `idea-wall/overrides.json` holds the chosen
pages for a deck and a `pulled` list for takedowns. Built after test decks
showed the old fallback publishing the wrong pages, including an About Me page
with a personal photo. A deck the renderer is unsure about now publishes nothing
until its pages are chosen.

**Takedowns reach the board.** A pulled slide drops out of the manifest, and the
placement step lists it for removal from the wall. Nothing comes off the board
without Tim's OK.

---

## Rejected. Do not re-propose.

**Any visual that dims, greys, crosses out, or removes the unpicked ideas.**
This is the single thing most likely to get proposed and it directly contradicts
the goal. A funnel is a picture of attrition. Sixty-seven people did not lose.

**Grouping tiles by designer.** Rejected on color-blocking grounds. See above.

**Printing slides and hanging them physically.** Proposed as a pitch-day ritual.
Tim's goals are served by a persistent TV display, not a one-day installation.

**Extending GAME405_Studio_Board.html with an IDEAS array.** This was the
recommended path before Tim clarified the goal. He wants the mosaic and he does
not want a custom tool for it.

**A standalone web page for the wall.** The repo shipped a contact sheet and a
landing page on Pages. Both were removed on September 11. Tim: "it is redundant
and not how I want to present." The Miro frame is the presentation.

**Google Slides, Padlet, Blackboard Discussions.** All considered. Slides loses
because you cannot zoom into one tile and it visibly looks like an editing
interface on a TV. Padlet caps at three boards on the free tier. Discussions is
where ideas go to die.

**Changing the pitch brief to require PNG exports from students.** Proposed
twice, rejected firmly: "I am not changing the plan now." The decks were already
in progress. The pipeline absorbs the work instead.

**Git LFS.** Not a preference, a hard technical block. GitHub Pages does not
serve LFS-tracked files, it serves the pointer, so a slide in LFS reaches Miro
as about 130 bytes of ASCII. Full reasoning and the doc link are in
`.gitattributes` at the repo root. The slides total roughly 25MB and do not need
it. If a future subproject needs large binaries, give it a separate repo.

**Loosening the page-picking thresholds to make one stubborn deck pass.** That
trades one visible problem for invisible ones across the other twenty-one. Fix
the single deck, or use a per-deck page override.

---

## Open

**Final roster count.** 22 students as of September 11, so 66 idea slides. The
board carries 69 tiles, leaving three spare. Tim is still getting adds and said
to expect a few more. Do not trim the board down to match; extend it when the
number settles.

**Ground color.** The dark navy placeholder fill is deliberate, since a dark
ground makes slide art read like a gallery hang. If the decks come back mostly
dark, this may want to go lighter. Decide by looking at it on the actual TV, not
in the abstract.

---

## Proposed but never answered

Listed so nobody mistakes silence for agreement, and so nobody re-pitches them
as new ideas.

- **Claim threads.** Any team may scavenge a shelved idea at any point and must
  credit its author in the GDD, with a connector drawn from the tile to the
  project that took it. By week 10 the board would show which of the 69 fed the
  2. Raised, not responded to.
- **Ambient mode.** Cycling one full-screen slide at a time on the TV during
  work sessions, so a student sees their shelved idea come up in week 7. Raised,
  not responded to.
- **A timed reveal sequence** for the Monday open. Raised, not responded to.

---

## How Tim works, which matters here

He signals mode. During ideation he is conversational and pushes back hard on
framing before touching implementation. When he shifts to production he expects
finished artifacts, not options and not drafts.

He has corrected Claude more than once for raising issues out of sequence.
Resolve the problem in front of you before moving to downstream concerns.

Prose rules for anything written into this repo: no em dashes, no hedging, no
filler. Lead with what works before naming the gap. Name the exact file, the
exact line, the exact fix.
