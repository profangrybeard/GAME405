# Idea Wall

Turns student pitch deck PDFs into slide images and places them on the class
idea wall in Miro.

Board: https://miro.com/app/board/uXjVHoWCO8w=/

The board is the only display. Slides are served from `/idea-wall/slides/` on
the class Pages site so Miro can fetch them, and Miro keeps its own copy of
each one once it is placed. There is no web page. DECISIONS.md at the repo root
records why.

Repo-wide setup, the LFS decision, and the takedown policy live at the repo
root in README.md, .gitattributes and NOTICE.md. Read those first.

Every student pitches three ideas. Five go to Amnesia Fortnight jam teams, two
reach production. The rest stay on the wall, visible and scavengeable, for the
whole quarter.

## What is public

Only the idea slides the renderer selects from decks it is confident about.
Source decks are gitignored, so title pages, personal introduction slides, and
thank-you pages never leave your machine. A deck the renderer is not sure about
publishes nothing until you choose its pages. Students are told their idea
slides go on a public wall and can email to have one pulled.

To pull a slide, follow the three steps in NOTICE.md at the repo root.

## Setup, once

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, `python3` is usually the Microsoft Store stub. Use
`py -m venv .venv` and `source .venv/Scripts/activate` in Git Bash, then
`python` inside the venv.

Then on GitHub: Settings, Pages, deploy from branch `main`, folder `/ (root)`.
The repo has to be public for Miro to fetch the images.

## The loop

1. Download the pitch deck submissions from Blackboard into `decks/`.
2. Export the roster from Blackboard: Gradebook, download, columns only.
   Save it outside the repo. It carries student IDs.
3. Render:

```bash
cd idea-wall
python3 tools/render_decks.py \
  --decks decks/ \
  --out slides/ \
  --roster ~/Downloads/gc_GAME-405-A01-12734_202710_columns.xls
```

4. Read the output. It prints what is worth acting on:
   - `no deck yet:` the students who have not submitted
   - `REVIEW:` any deck the renderer was not confident about, and any file in
     `slides/` this run did not produce
5. Open `manifest.json` and check `needs_review` and `problems`. Every flagged
   deck is rendered page by page into `review/<deck name>/p<N>.jpg`, and nothing
   from it is published. Fix each one (see below), then re-run.
6. Commit and push. The images are live at the Pages URL within a minute.
7. Verify:

```bash
python3 tools/verify_publish.py --base https://profangrybeard.github.io/GAME405/idea-wall/
```

   It checks every manifest entry for a 200, an image content type, and a real
   byte count. Miro fetches from these URLs, so a slide that fails here would
   fail on the board.
8. Place: `python3 tools/place_slides.py`, then carry out the plan. See
   Placement below.

## When a deck is flagged

The renderer scores every page and keeps the ones that look like idea slides:
a moodboard plus a real paragraph of pitch copy, minus anything reading as
boilerplate. On a normal six-page deck this picks pages 3, 4 and 5.

A deck is flagged, and publishes nothing, when:

- **The pick count is not three.** Four ideas, one idea spread over two pages,
  a collage title page, or only two ideas. Look at its pages in `review/` and
  list the ones to publish in `overrides.json`, keyed by the deck's filename.
  Pages are 1-based, in idea order.

  ```json
  {
    "pages": {
      "ATL_A01_GAME405_DeeOkafor_GamePitch.pdf": [3, 4]
    },
    "pulled": []
  }
  ```

- **The filename does not name the student.** No roster last name in it, a
  match on last name only, or a shared last name with no first name to tell
  them apart. Rename the file in `decks/` to include the student's first and
  last name.
- **Two decks map to the same student.** Usually a resubmission. Delete the
  old one from `decks/`.

Do not loosen the scoring thresholds to make one deck pass. See CLAUDE.md.

`overrides.json` is committed, so page choices and takedowns survive a fresh
clone.

## Placement

`tools/place_slides.py` lays out the wall from what was delivered. It never
talks to Miro. Claude sends its SVG steps through the Miro connector, following
the placement loop in CLAUDE.md.

- **The wall shows every delivered pitch, and never fewer than 63 tiles.**
  Until enough pitches arrive, placeholder tiles fill the rest under the names
  the wall has always had, so it can be demoed any time. Past 63 it grows with
  the pitches, and a fourth idea gets a tile like any other.
- **Blur is a switch.** `python3 tools/place_slides.py blur on` shows every
  slide as its blurred twin from `slides/blur/` on the next run, so the wall
  suggests its contents without giving them away. `blur off` brings the sharp
  slides back.
- **The frame is always 16:9**, so presenting it fills the classroom TV. The
  grid is chosen to fit: 69 pitches lay out 9 across and 8 down.
- **No designer's slides touch**, diagonals included. The order is worked out,
  not random, so the same slides always give the same wall.
- **The counters are live.** PITCHED counts the slides on the wall, the line
  under it counts designers with at least one, and JAM TEAMS and PRODUCTION
  stay 5 and 2.

Each run sorts every slide, placeholder, and header line into place, keep,
rebuild, or remove. Miro cannot move an image inside a frame, so anything that
changes is rebuilt: the old copy is deleted and a new one created where it now
belongs. Rebuild and remove delete from the board, so they need Tim's OK.

`placements.json` is the ledger of what is on the wall: each slide's image, its
box, and a hash of the file it came from. It is committed. Running the plan
again with nothing new changes nothing.

A student registered after the roster export goes in `overrides.json` as
`"extra_students": [["Arafa", "Yoseph"]]`, last name first, until the next
export includes them.

## Naming

`<lastname>_idea<N>.jpg`, lowercase, punctuation stripped. Duplicate last names
get a first initial appended. Names come from the roster, not the filename the
student chose, so a submission named anything lands correctly as long as the
student's first and last name appear somewhere in the filename.

The placement ledger tracks each slide on the wall by this name. Renaming a
published file makes the wall treat it as a new slide and the old one as
removed.

## manifest.json

Written on every run. Not just a log, it is what the board placement reads.

```json
{
  "count": 66,
  "students": 22,
  "needs_review": [],
  "problems": [],
  "slides": [
    {
      "file": "broughton_idea1.jpg",
      "student": "broughton",
      "name": "Lex Broughton",
      "idea": 1,
      "title": "SAY CHEESE!",
      "source": "ATL_A01_GAME405_LexBroughton_GamePitch.pdf",
      "page": 3
    }
  ]
}
```

`needs_review` lists deck filenames, the same keys `overrides.json` uses.

`title` is the largest type on the page, skipping big idea numbers like "01".
That is the working title in every deck template seen so far. Worth a glance.

## Layout

```
tools/render_decks.py     the renderer
tools/check_renderer.py   runs the renderer against synthetic decks, run after any change
tools/verify_publish.py   confirms every slide is live and serving as an image
tools/place_slides.py     lays out the Miro wall, writes its SVG steps, keeps the ledger
decks/                    source PDFs, gitignored
review/                   every page of each flagged deck, gitignored
slides/                   published JPGs, served by Pages for Miro to fetch
overrides.json            chosen pages per deck, pulled slides, late registrations
manifest.json             what was published and what needs review
placements.json           what is on the wall, and where
placement_plan.json       the latest plan, gitignored
placement_svg/            the latest SVG steps for the Miro connector, gitignored
placement_read.svg        the wall as read back for `record`, gitignored
```
