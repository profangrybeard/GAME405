# Notice on student work

## Who owns what

The slides published in this repo were made by students in GAME 405 at SCAD
Atlanta. They own their work. Nothing here is licensed for reuse. Publishing a
slide to the class idea wall is a display permission for the purpose of the
course, not a transfer of anything.

The tools in `*/tools/` are the instructor's and may be reused freely.

## What gets published

Only the idea slides the renderer selects: the pages carrying a working title,
a moodboard, and a pitch paragraph.

Source decks are gitignored and never committed. That matters, because decks
routinely contain a personal introduction slide with the student's own photo.
Those pages stay on the instructor's machine.

## What students are told

Before the decks are due, the class is told that idea slides go on a public
wall, and that anyone can email to have a slide pulled, no reason required.

## Pulling a slide

It lives in three places. Removing it from one is not removing it.

1. Add its name without the extension, for example `"tanaka_idea2"`, to
   `pulled` in `idea-wall/overrides.json`. Without this the next render run
   puts it back, because the source deck is still in `decks/`.
2. Delete the file from `idea-wall/slides/` and re-run the renderer. Its
   manifest entry drops out, and the run reports the file if it is still there.
3. Delete the image from the Miro board by hand.

Commit steps 1 and 2 together so the manifest never points at a file that is
gone. Step 3 has no automation and is easy to forget. The board is the copy the
class actually sees.

If the request arrives after the quarter ends, honor it anyway.

## Retention

The wall is built for one quarter. When the course is archived, the published
slides come down unless a student has said they are happy for their work to
stay up.
