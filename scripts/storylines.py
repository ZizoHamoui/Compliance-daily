"""Storylines: ongoing threads that link stories across editions into one dated timeline.

A card joins a storyline with `"storyline": "<slug>"`. A new storyline is declared once, in the edition that starts it,
with `"storylines": {"<slug>": "<title>"}`. Later editions just reuse the slug.

    python scripts/storylines.py list        # existing storylines (for the morning editor)
"""
import re
import sys

from common import EDITIONS, PAPER, read_json

SLUG_RX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slug_href(card, date):
    if card.get("kind") == "briefing":
        return None  # filled by build.py, which knows the briefing page slug
    return card.get("url", "")


def collect(exclude_date=None):
    """{slug: {"title", "stories": [ {date, card}... newest first ], "first", "last"}} across all editions."""
    titles, stories = {}, {}
    for p in sorted(EDITIONS.glob("*.json")):
        if p.stem == exclude_date:
            continue
        ed = read_json(p, None) or {}
        for slug, title in (ed.get("storylines") or {}).items():
            if SLUG_RX.match(slug) and title:
                titles[slug] = title  # later editions may refine the title
        for c in ed.get("cards", []):
            s = c.get("storyline")
            if s and SLUG_RX.match(s):
                stories.setdefault(s, []).append({"date": ed.get("date", p.stem), "card": c})
    out = {}
    for slug, items in stories.items():
        if slug not in titles:
            continue
        items.sort(key=lambda x: x["date"], reverse=True)
        out[slug] = {"slug": slug, "title": titles[slug], "stories": items,
                     "first": items[-1]["date"], "last": items[0]["date"], "count": len(items)}
    return dict(sorted(out.items(), key=lambda kv: kv[1]["last"], reverse=True))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        sl = collect()
        if not sl:
            print("(no storylines yet)")
        for s in sl.values():
            print(f"{s['slug']}  |  {s['title']}  |  {s['count']} stories, last {s['last']}")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
