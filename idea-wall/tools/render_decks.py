#!/usr/bin/env python3
"""
render_decks.py - turn GAME 405 pitch deck PDFs into idea-wall slides.

Usage:
    python3 render_decks.py --decks decks/ --out slides/ --roster roster.xls

For each PDF it:
  1. matches the deck to a roster student by the name in the filename
  2. picks the idea slides (moodboard + body copy), or reads overrides.json
  3. renders a confident deck to <lastname>_idea<N>.<ext> in --out
  4. renders every page of a flagged deck to --review instead, never --out
  5. writes manifest.json for review before anything is published

Page picking is a heuristic. A run is done when the manifest's "problems"
and "needs_review" are both empty.
"""

import argparse, csv, io, json, re, sys, unicodedata
from pathlib import Path

import pymupdf

# ---------- naming ----------

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def load_roster(path):
    """Blackboard gradebook column export: UTF-16 TSV, Last Name / First Name.
    Returns {key: (first, last)}."""
    raw = Path(path).read_text(encoding="utf-16")
    rows = list(csv.reader(io.StringIO(raw), delimiter="\t"))
    people = [(r[0].strip(), r[1].strip()) for r in rows[1:] if r and r[0].strip()]
    counts = {}
    for last, _ in people:
        counts[slug(last)] = counts.get(slug(last), 0) + 1
    out = {}
    for last, first in people:
        key = slug(last)
        if counts[key] > 1:
            key = slug(last) + slug(first)[:1]
        out[key] = (first, last)
    return out


def match_student(pdf_name, roster):
    """Find the roster student whose last name appears in the filename.
    Returns (key, note). A note means the match is not confident."""
    flat = slug(pdf_name)
    hits = [k for k, (_, last) in roster.items() if slug(last) and slug(last) in flat]
    if not hits:
        return None, "no roster match"
    # Longest last name wins, so "chen" beats the "ng" inside "chengame".
    best = max(len(slug(roster[k][1])) for k in hits)
    hits = [k for k in hits if len(slug(roster[k][1])) == best]
    named = [k for k in hits if slug(roster[k][0]) in flat]
    if len(named) == 1:
        return named[0], None
    if len(hits) == 1:
        return hits[0], f"matched {hits[0]} on last name only, first name not in filename"
    return None, f"shared last name, filename does not say which of {', '.join(hits)}"


# ---------- page picking ----------

BOILERPLATE = re.compile(
    r"\b(thank you|pitch deck|introduction|about me|my current skillset|questions)\b", re.I
)

# Template decoration like "01" or "IDEA 2", often set bigger than the title.
NUMBER_LABEL = re.compile(r"^(idea\s*)?#?\d{1,2}\.?$", re.I)


def page_stats(page):
    text = page.get_text().strip()
    return {
        "words": len(text.split()),
        "images": len(page.get_images(full=True)),
        "text": text,
        "boiler": bool(BOILERPLATE.search(text[:400])),
    }


def score(st):
    """An idea slide carries a moodboard and a real paragraph of pitch copy."""
    s = 0
    if st["images"] >= 3:
        s += 3
    elif st["images"] >= 1:
        s += 1
    if st["words"] >= 25:
        s += 2
    if st["words"] >= 45:
        s += 1
    if st["boiler"]:
        s -= 4
    if st["words"] < 12 and st["images"] == 0:
        s -= 3
    return s


def working_title(page):
    """Title is the largest type on the page. Titles wrap, so keep every line
    set at that size and join them in reading order."""
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            size = max((sp["size"] for sp in line["spans"]), default=0)
            txt = "".join(sp["text"] for sp in line["spans"]).strip()
            if txt and not NUMBER_LABEL.match(txt):
                lines.append((size, line["bbox"][1], line["bbox"][0], txt))
    if not lines:
        return ""
    top = max(l[0] for l in lines)
    title = [l for l in lines if l[0] >= top - 0.5]
    title.sort(key=lambda l: (round(l[1]), l[2]))
    return re.sub(r"\s+", " ", " ".join(t[3] for t in title)).strip()


def pick_pages(doc, expected=3):
    scored = []
    for i, page in enumerate(doc):
        st = page_stats(page)
        scored.append((i, score(st), st))
    keep = [i for i, sc, _ in scored if sc >= 4]
    notes = []
    if len(keep) != expected:
        picked = ", ".join(str(i + 1) for i in keep) or "none"
        notes.append(f"picked {len(keep)} pages ({picked}), expected {expected}")
    return keep, notes


def load_overrides(path):
    """overrides.json: {"pages": {deck filename: [page numbers]},
    "pulled": [published names without extension]}. Missing file is fine."""
    p = Path(path)
    data = json.loads(p.read_text()) if p.exists() else {}
    return data.get("pages", {}), set(data.get("pulled", []))


# ---------- rendering ----------

def render(page, dest, width, fmt, quality):
    zoom = width / page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    if fmt == "jpg":
        pix.pil_save(dest, format="JPEG", quality=quality, optimize=True)
    else:
        pix.save(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--roster")
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--overrides", default="overrides.json")
    ap.add_argument("--review", help="flagged decks render here (default: review/ beside --out)")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--format", choices=["jpg", "png"], default="jpg")
    ap.add_argument("--quality", type=int, default=92)
    ap.add_argument("--ideas", type=int, default=3)
    args = ap.parse_args()

    roster = load_roster(args.roster) if args.roster else {}
    page_overrides, pulled = load_overrides(args.overrides)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    review = Path(args.review) if args.review else out.parent / "review"
    # Clear last run's review renders. Only p<N> images inside deck folders,
    # so a mistyped --review cannot take anything else with it.
    for f in review.glob("*/p*.*"):
        if f.suffix in (".jpg", ".png"):
            f.unlink()

    pdfs = sorted(Path(args.decks).glob("*.pdf"))
    if not pdfs:
        sys.exit(f"no PDFs in {args.decks}")

    # Pass 1: decide who each deck belongs to and which pages it publishes.
    plans = []
    for pdf in pdfs:
        doc = pymupdf.open(pdf)
        key, note = match_student(pdf.stem, roster) if roster else (slug(pdf.stem), None)
        notes = [note] if note else []
        if pdf.name in page_overrides:
            pages = [p - 1 for p in page_overrides[pdf.name]]
            bad = [p + 1 for p in pages if not 0 <= p < len(doc)]
            if bad:
                notes.append(f"override pages {bad} not in a {len(doc)} page deck")
        else:
            pages, pick_notes = pick_pages(doc, args.ideas)
            notes += pick_notes
        doc.close()
        plans.append({"pdf": pdf, "key": key, "pages": pages, "notes": notes})

    # Two publishable decks on one key would silently overwrite each other's
    # slides. A deck already flagged publishes nothing, so it cannot collide.
    by_key = {}
    for pl in plans:
        if pl["key"] and not pl["notes"]:
            by_key.setdefault(pl["key"], []).append(pl)
    for key, group in by_key.items():
        for pl in group if len(group) > 1 else []:
            others = ", ".join(o["pdf"].name for o in group if o is not pl)
            pl["notes"].append(f"same student key '{key}' as {others}")

    # Pass 2: confident decks publish. Flagged decks render every page to
    # review/ so an override can be written, and publish nothing.
    entries, problems, needs_review, skipped = [], [], [], []
    for pl in plans:
        pdf = pl["pdf"]
        doc = pymupdf.open(pdf)
        if pl["notes"]:
            problems += [f"{pdf.name}: {n}" for n in pl["notes"]]
            needs_review.append(pdf.name)
            dest = review / pdf.stem
            dest.mkdir(parents=True, exist_ok=True)
            for pno, page in enumerate(doc):
                render(page, dest / f"p{pno + 1}.{args.format}",
                       args.width, args.format, args.quality)
            doc.close()
            continue
        first, last = roster.get(pl["key"], ("", ""))
        for n, pno in enumerate(pl["pages"], start=1):
            name = f"{pl['key']}_idea{n}.{args.format}"
            if Path(name).stem in pulled:
                skipped.append(name)
                continue
            page = doc[pno]
            render(page, out / name, args.width, args.format, args.quality)
            entries.append({
                "file": name,
                "student": pl["key"],
                "name": f"{first} {last}".strip(),
                "idea": n,
                "title": working_title(page),
                "source": pdf.name,
                "page": pno + 1,
            })
        doc.close()

    # Anything in --out that this run did not produce is still public.
    published = {e["file"] for e in entries}
    for f in sorted(out.iterdir()):
        if f.suffix.lower() in (".jpg", ".jpeg", ".png") and f.name not in published:
            why = "on the pulled list" if f.stem in pulled else "not in this run's manifest"
            problems.append(f"{out.name}/{f.name}: {why}, delete it or it stays public")

    manifest = {
        "count": len(entries),
        "students": len({e["student"] for e in entries}),
        "needs_review": needs_review,
        "problems": problems,
        "slides": entries,
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2), newline="\n")

    print(f"{len(entries)} slides from {len(pdfs)} decks -> {out}")
    if needs_review:
        print(f"{len(needs_review)} flagged decks rendered to {review}, none published")
    if skipped:
        print("pulled, not rendered:", ", ".join(skipped))
    if roster:
        missing = sorted(set(roster) - {pl["key"] for pl in plans})
        if missing:
            print("no deck yet:", ", ".join(missing))
    for p in problems:
        print("REVIEW:", p)


if __name__ == "__main__":
    main()
