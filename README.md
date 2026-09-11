# GAME 405 · Game Development Studio I

Class repository. SCAD Atlanta, Fall 2026. Mon/Wed 11:00 to 1:30, FORTY5 156.

This repo holds the tools and published assets for the class. It is expected to
grow more than one subproject over the quarter, so everything lives in its own
folder with its own README rather than at the root.

## Subprojects

| Folder | What it is | Published at |
|---|---|---|
| [`idea-wall/`](idea-wall/) | Renders pitch deck PDFs into the slide images behind the class idea wall | `/idea-wall/` |

The idea wall itself is a Miro board:
**https://miro.com/app/board/uXjVHoWCO8w=/**

The repo publishes the images. The board displays them. Changing one does not
change the other.

## Why this repo is public

GitHub Pages is what gives each slide a URL, and Miro can only pull an image
it can fetch. Public Pages is the price of a board that builds itself.

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

**4. Set the About panel.** Description, and put the Pages URL in the website
field. Six weeks from now you will be looking for this link from your phone.

**5. Do not add Git LFS.** Pages does not serve LFS-tracked files, it serves the
pointer text, so an LFS-tracked slide reaches Miro as about 130 bytes of ASCII
instead of an image. The full reasoning is in [`.gitattributes`](.gitattributes).
The published slides are around 25MB total and do not need it.

**6. Verify before trusting it.** After the first push with real content:

```bash
cd idea-wall
python3 tools/verify_publish.py --base https://profangrybeard.github.io/GAME405/idea-wall/
```

That catches 404s, wrong content types, and LFS pointers. Run it before anyone
places images on the board.

## Conventions

- One folder per subproject, each with its own README and its own `tools/`.
- Source material that should not be public is gitignored, not trusted to care.
- No em dashes in docs, comments, or commit messages.
- Filenames published to Pages are load-bearing. The Miro board references them
  by name, so renaming a file breaks a tile.

## Adding a subproject

```
<name>/
  README.md      what it is, how to run it, what it publishes
  tools/         scripts
  index.html     only if it needs a page
```

Then add a row to the table above. If the new subproject needs large binaries,
give it a separate repo with LFS rather than dragging this one off Pages.
