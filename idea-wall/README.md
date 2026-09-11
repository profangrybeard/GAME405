# Idea Wall

Turns student pitch deck PDFs into the slide images behind the class idea wall.

Board: https://miro.com/app/board/uXjVHoWCO8w=/
Published at: `/idea-wall/` on the class Pages site.

Repo-wide setup, the LFS decision, and the takedown policy live at the repo
root in README.md, .gitattributes and NOTICE.md. Read those first.

Every student pitches three ideas. Five go to Amnesia Fortnight jam teams, two
reach production. The rest stay on the wall, visible and scavengeable, for the
whole quarter. This repo publishes the images the wall is built from.

The Miro board is the display surface. This repo is the source of truth for
what goes on it.

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

## When a deck is flagged

The renderer scores every page and keeps the ones that look like idea slides:
a moodboard plus a real paragraph of pitch copy, minus anything reading as
boilerplate. On a normal six-page deck this picks pages 3, 4 and 5.

A deck is flagged, and publishes nothing, when:

- **The pick count is not three.** Four ideas, one idea spread over two pages,
  a collage title page, or only two ideas. Look at its pages in `review/` and
  list the ones to publish in `overrides.json`, keyed by the deck's filename.
  Pages are 1-based, in idea order. An override can publish four ideas.

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

## Naming

`<lastname>_idea<N>.jpg`, lowercase, punctuation stripped. Duplicate last names
get a first initial appended. Names come from the roster, not the filename the
student chose, so a submission named anything lands correctly as long as the
student's first and last name appear somewhere in the filename.

These names match the placeholder tiles on the Miro board one to one.

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
That is the working title in every deck template seen so far. It becomes the
tile label on the board, so a wrong title here is a wrong label there. Worth a
glance.

## Layout

```
tools/render_decks.py     the renderer
tools/check_renderer.py   runs the renderer against synthetic decks, run after any change
tools/verify_publish.py   confirms every slide is live and serving as an image
decks/                    source PDFs, gitignored
review/                   every page of each flagged deck, gitignored
slides/                   published JPGs, served by Pages
overrides.json            chosen pages per deck, and pulled slides
manifest.json             what was published and what needs review
index.html                contact sheet, the /idea-wall/ landing page
```

## Verify after pushing

```bash
python3 tools/verify_publish.py --base https://profangrybeard.github.io/GAME405/idea-wall/
```

Checks every manifest entry for a 200, an image content type, and a real byte
count. Run it before anyone places images on the board. A broken slide shows up
as a dead tile on a classroom TV, which is a bad place to find out.
