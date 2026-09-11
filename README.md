# GAME 405 · Game Development Studio I

Class repository. SCAD Atlanta, Fall 2026. Mon/Wed 11:00 to 1:30, FORTY5 156.

This repo holds the tools and published assets for the class. It is expected to
grow more than one subproject over the quarter, so everything lives in its own
folder with its own README rather than at the root.

## Subprojects

| Folder | What it is | Published at |
|---|---|---|
| [`idea-wall/`](idea-wall/) | Renders pitch deck PDFs into slide images and places them on the class idea wall in Miro | `/idea-wall/slides/`, images only |

The idea wall itself is a Miro board:
**https://miro.com/app/board/uXjVHoWCO8w=/**

The repo renders and hosts the images. The placement step puts them on the
board, and Miro keeps its own copy of each one. Changing a file here does not
change the board until the placement step runs.

## Why this repo is public

GitHub Pages gives each slide a URL, and the placement step has Miro fetch each
slide from it. Pages is an image host and nothing more. There is no web page;
the board is the display.

That makes student work world-readable, so read [NOTICE.md](NOTICE.md) before
adding anything. The short version: only the idea slides get published, never
the full decks, and students can email to have a slide pulled.

## First-time setup

Run these once, in order. Steps 3 and 5 are the ones people skip and regret.

**1. Create the repo, public, no auto-generated files.**

```bash
git init -b main
git add .
git commit -m "Class repo scaffold with idea-wall subproject"
gh repo create GAME405 --public --source=. --remote=origin --push
```

**2. Turn on Pages.** Repo Settings, Pages, deploy from branch `main`, folder
`/ (root)`. Root, not `/docs`, because subprojects are served as subfolders.

**3. Confirm `.nojekyll` is committed at the root.** Without it Pages runs the
files through Jekyll, which skips anything starting with an underscore and adds
a build step that can fail on filenames you did not choose. The file is empty
on purpose. Do not delete it.

**4. Set the About panel.** Description, and put the Miro board URL in the
website field. The Pages site has no page of its own to link to.

**5. Do not add Git LFS.** Pages does not serve LFS-tracked files, it serves the
pointer text, so an LFS-tracked slide reaches Miro as about 130 bytes of ASCII
instead of an image. The full reasoning is in [`.gitattributes`](.gitattributes).
The published slides are around 25MB total and do not need it.

**6. Verify before trusting it.** After the first push with real content:

```bash
cd idea-wall
python3 tools/verify_publish.py --base https://profangrybeard.github.io/GAME405/idea-wall/
```

That catches 404s, wrong content types, and LFS pointers. Run it before anything
is placed on the board.

## Conventions

- One folder per subproject, each with its own README and its own `tools/`.
- Source material that should not be public is gitignored, not trusted to care.
- No em dashes in docs, comments, or commit messages.
- Filenames published to Pages are load-bearing. The Miro board references them
  by name, so renaming a file breaks a tile.
- Decisions and the reasons for them live in [DECISIONS.md](DECISIONS.md).

## Adding a subproject

```
<name>/
  README.md      what it is, how to run it, what it publishes
  tools/         scripts
```

Then add a row to the table above. If the new subproject needs large binaries,
give it a separate repo with LFS rather than dragging this one off Pages.
