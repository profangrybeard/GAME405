# Idea Wall

Student pitch decks in, slides on the class Miro board out.

Board: https://miro.com/app/board/uXjVHoWCO8w=/

Every student pitches three ideas. Five become Amnesia Fortnight jam teams and
two reach production. The rest stay on the wall, visible and scavengeable, all
quarter.

The renderer picks the idea slides out of each deck and publishes them as JPEGs
in `slides/`, with a blurred copy of each in `slides/blur/`. GitHub Pages serves
them so Miro can fetch them. The placement step, which Claude runs through the
Miro connector, puts them on the board, and Miro keeps its own copy of each.
The board is the display. There is no web page.

Repo setup, the LFS rule, and takedowns are at the repo root in README.md,
.gitattributes, and NOTICE.md. The reasons behind all of it are in DECISIONS.md.

## What is public

Only the idea slides the renderer picked from decks it was sure about. Decks
are gitignored, so title, intro, and thank-you pages never leave your machine.
Students can email to have a slide pulled. NOTICE.md has the three steps.

## Setup, once

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, `python3` is the Microsoft Store stub. Use `py -m venv .venv` and
`source .venv/Scripts/activate` in Git Bash.

## Each round of decks

1. Save the Blackboard submissions into `decks/`. Export the roster
   (Gradebook, download, columns only) somewhere outside the repo. It carries
   student IDs.
2. Render:

   ```bash
   cd idea-wall
   python3 tools/render_decks.py --decks decks/ --out slides/ --roster ~/Downloads/<roster export>.xls
   ```

3. Read what it prints. `no deck yet:` lists students still missing, `REVIEW:`
   lists decks it would not publish. The run is done when `manifest.json` has
   empty `needs_review` and `problems`.
4. Commit and push, then check every slide and its blurred copy is live:

   ```bash
   python3 tools/verify_publish.py --base https://profangrybeard.github.io/GAME405/idea-wall/
   ```

5. Have Claude run the placement loop in CLAUDE.md. Anything it would delete
   from the board waits for your OK. Commit `placements.json` after.

## When a deck is flagged

A flagged deck publishes nothing, and every page of it lands in `review/<deck>/`.

- **The wrong number of pages picked.** Four ideas, one idea over two pages, a
  busy title page. List the right pages in `overrides.json` under `pages`,
  keyed by the deck's filename, 1-based, in idea order:
  `"ATL_A01_GAME405_DeeOkafor_GamePitch.pdf": [3, 4]`.
- **The filename does not name the student.** Rename the file in `decks/` to
  include their first and last name.
- **Two decks for one student.** Usually a resubmission. Delete the old one.

Do not loosen the page scoring to make one deck pass.

## The wall

- Every delivered pitch gets a tile, and the wall never drops below 63.
  Placeholders fill the gap, so it can be demoed any time.
- A slide keeps its spot once it is up. New ones fill open spots away from
  their designer's other slides. Past 63 the wall grows to the right and down.
- The frame is always 16:9, so it fills the classroom TV.
- PITCHED and the designer count update on every run. JAM TEAMS and PRODUCTION
  stay 5 and 2.
- `python3 tools/place_slides.py blur on` covers every slide with its blurred
  copy on the next run. `blur off` takes the covers off. That is the reveal.
- A student who registered after the roster export goes in `overrides.json`
  under `extra_students`, last name first.

## Files

```
tools/render_decks.py     picks and renders the idea slides
tools/check_renderer.py   renderer self-test, run after changing it
tools/verify_publish.py   checks every slide is live on Pages
tools/place_slides.py     plans the Miro wall and keeps its ledger; `check` self-tests it
decks/                    source PDFs, gitignored
review/                   every page of each flagged deck, gitignored
slides/                   published slides, with the blurred copies in slides/blur/
overrides.json            page picks, pulled slides, late registrations, blur
manifest.json             what the last render published
placements.json           what is on the wall, and where
placement_plan.json, placement_svg/, placement_read.svg   working files, gitignored
```

Slides are named `<lastname>_idea<N>.jpg` from the roster, not from what the
student called the file. Do not rename a published slide: the wall would treat
it as a new slide and the old one as removed.
