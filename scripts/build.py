"""Step 3 (GitHub Actions, no AI): render editions/*.json into the static newspaper site in ./site.

If today's curated edition is missing but today's candidates exist, an "Express edition"
(headlines only) is generated so the morning paper is never empty.
"""
import re
import shutil
from datetime import datetime

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from common import CANDIDATES, EDITIONS, PAPER, SITE, STATIC, TEMPLATES, load_yaml, read_json, today_local

TOPICS = load_yaml("topics.yaml")["topics"]
REGIONS = {"US": "United States", "CA": "Canada", "EU": "European Union"}
LANGS = {"en": "English", "fr": "French", "de": "German", "nl": "Dutch", "es": "Spanish", "it": "Italian"}

# palette per topic for the generated card illustrations (used when an article has no image)
TOPIC_COLORS = {
    "whistleblowing": ("#7a1f1f", "#c9a227"), "false_claims": ("#3b2a5a", "#d98c5f"),
    "third_party_risk": ("#1f4a5a", "#9cc5c9"), "due_diligence": ("#2f4a2f", "#c8d5a3"),
    "employment_law": ("#5a3b1f", "#e3c08a"), "enforcement": ("#1d1d1d", "#c0392b"),
    "anti_bribery": ("#4a1f3b", "#e0a3c2"), "aml_sanctions": ("#1f2f5a", "#a3b5e0"),
    "governance": ("#2a2a2a", "#bfb6a2"), "ai_governance": ("#123c3c", "#7fd1c7"),
    "privacy": ("#2c3e50", "#95a5a6"), "esg": ("#1e4d2b", "#9bd19f"), "cybersecurity": ("#101826", "#4fa3d1"),
}
TOPIC_GLYPH = {
    "whistleblowing": "M50 30 L70 30 L80 50 L70 70 L50 70 Z M20 45 L50 40 L50 60 L20 55 Z",
    "false_claims": "M30 25 H70 V75 H30 Z M38 38 H62 M38 50 H62 M38 62 H54",
    "third_party_risk": "M30 50 m-12 0 a12 12 0 1 0 24 0 a12 12 0 1 0 -24 0 M70 50 m-12 0 a12 12 0 1 0 24 0 a12 12 0 1 0 -24 0 M42 50 H58",
    "due_diligence": "M45 45 m-18 0 a18 18 0 1 0 36 0 a18 18 0 1 0 -36 0 M58 58 L78 78",
    "employment_law": "M30 40 H70 V72 H30 Z M42 40 V32 H58 V40",
    "enforcement": "M25 72 H75 M30 66 H70 M35 66 V44 M50 66 V44 M65 66 V44 M27 44 H73 L50 28 Z",
    "anti_bribery": "M50 50 m-22 0 a22 22 0 1 0 44 0 a22 22 0 1 0 -44 0 M34 66 L66 34",
    "aml_sanctions": "M28 36 H72 V66 H28 Z M50 51 m-8 0 a8 8 0 1 0 16 0 a8 8 0 1 0 -16 0",
    "governance": "M50 26 L76 40 H24 Z M30 44 V68 M43 44 V68 M57 44 V68 M70 44 V68 M24 72 H76",
    "ai_governance": "M34 34 H66 V66 H34 Z M42 42 H58 V58 H42 Z M40 34 V26 M50 34 V26 M60 34 V26 M40 66 V74 M50 66 V74 M60 66 V74",
    "privacy": "M36 48 V40 a14 14 0 0 1 28 0 V48 M30 48 H70 V74 H30 Z",
    "esg": "M50 76 V48 M50 52 C30 50 26 32 32 24 C48 26 54 38 50 52 M50 58 C64 56 72 44 70 36 C58 36 50 46 50 58",
    "cybersecurity": "M50 24 L74 34 V50 C74 64 64 72 50 78 C36 72 26 64 26 50 V34 Z",
}


def topic_svg(key):
    bg, fg = TOPIC_COLORS.get(key, ("#2a2a2a", "#bfb6a2"))
    glyph = TOPIC_GLYPH.get(key, TOPIC_GLYPH["governance"])
    label = TOPICS.get(key, {}).get("label", "Compliance").upper().replace("&", "&amp;")
    lines = "".join(f'<line x1="{x}" y1="0" x2="{x - 225}" y2="225" stroke="{fg}" stroke-opacity=".08" stroke-width="10"/>'
                    for x in range(0, 640, 28))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 225" preserveAspectRatio="xMidYMid slice">
<rect width="400" height="225" fill="{bg}"/>{lines}
<g transform="translate(150,40) scale(1.0)" fill="none" stroke="{fg}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="{glyph}"/></g>
<text x="200" y="190" text-anchor="middle" font-family="Georgia,serif" font-size="{13 if len(label) < 26 else 10}" letter-spacing="{4 if len(label) < 26 else 2}" fill="{fg}">{label}</text>
</svg>'''


def fmt_date(iso):
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%b %-d, %Y")
    except ValueError:
        return iso[:10]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "briefing"


def express_edition(date):
    """Headlines-only edition built straight from candidates (no AI)."""
    cand = read_json(CANDIDATES / f"{date}.json", None)
    if not cand:
        return None
    items = [i for i in cand["items"] if not i["paywalled"]][: PAPER.get("cards_per_edition", 25)]
    cards = [{**i, "summary": i["snippet"][:240], "impact": "", "impact_level": "", "kind": "link"} for i in items]
    return {"date": date, "express": True, "lead_id": cards[0]["id"] if cards else None,
            "editor_note": "", "cards": cards, "briefings": {}}


def normalise(ed):
    for c in ed["cards"]:
        c.setdefault("kind", "link")
        c["topic"] = c.get("topic") if c.get("topic") in TOPICS else "governance"
        c["topic_label"] = TOPICS[c["topic"]]["label"]
        c["region_label"] = REGIONS.get(c.get("region"), c.get("region", ""))
        c["lang"] = c.get("lang") or "en"
        c["lang_label"] = LANGS.get(c["lang"], c["lang"].upper())
        c["date_label"] = fmt_date(c.get("published"))
        c["impact_level"] = (c.get("impact_level") or "").capitalize()
        if c["kind"] == "briefing":
            b = ed["briefings"].get(c["id"], {})
            b["slug"] = slug(b.get("headline") or c["title"])
            c["href"] = f"b/{b['slug']}.html"
        else:
            c["href"] = c["url"]
    lead = next((c for c in ed["cards"] if c["id"] == ed.get("lead_id")), ed["cards"][0] if ed["cards"] else None)
    ed["lead"] = lead
    ed["rest"] = [c for c in ed["cards"] if c is not lead]
    ed["date_long"] = datetime.fromisoformat(ed["date"]).strftime("%A, %B %-d, %Y")
    ed["topics_present"] = sorted({c["topic"] for c in ed["cards"]}, key=lambda k: -TOPICS[k]["weight"])
    ed["regions_present"] = [r for r in REGIONS if any(c.get("region") == r for c in ed["cards"])]
    return ed


def main():
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    env.filters["md"] = lambda s: markdown.markdown(s or "", extensions=["extra", "sane_lists"])
    env.globals.update(paper=PAPER, topics=TOPICS, regions=REGIONS)

    editions = {p.stem: read_json(p, None) for p in sorted(EDITIONS.glob("*.json"))}
    today = today_local()
    if today not in editions:
        ex = express_edition(today)
        if ex:
            editions[today] = ex
    if not editions:  # nothing yet: use the newest candidates file
        latest = sorted(CANDIDATES.glob("*.json"))
        if latest:
            editions[latest[-1].stem] = express_edition(latest[-1].stem)

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "img").mkdir(parents=True)
    shutil.copytree(STATIC, SITE / "static")
    for key in TOPICS:
        (SITE / "img" / f"topic-{key}.svg").write_text(topic_svg(key), encoding="utf-8")

    dates = sorted(d for d, e in editions.items() if e)
    archive = []
    for n, date in enumerate(dates, start=1):
        ed = normalise(editions[date])
        ed["edition_no"] = n
        out = SITE / "editions" / date
        (out / "b").mkdir(parents=True, exist_ok=True)
        page = env.get_template("edition.html.j2").render(ed=ed, root="../../", base="", is_latest=(date == dates[-1]))
        (out / "index.html").write_text(page, encoding="utf-8")
        for c in ed["cards"]:
            if c["kind"] == "briefing" and c["id"] in ed["briefings"]:
                b = ed["briefings"][c["id"]]
                html = env.get_template("briefing.html.j2").render(ed=ed, card=c, b=b, root="../../../")
                (out / "b" / f"{b['slug']}.html").write_text(html, encoding="utf-8")
        archive.append({"date": date, "date_long": ed["date_long"], "no": n, "express": ed.get("express", False),
                        "lead": ed["lead"]["title"] if ed["lead"] else "", "count": len(ed["cards"]),
                        "briefings": sum(1 for c in ed["cards"] if c["kind"] == "briefing")})

    if dates:
        latest = dates[-1]
        # the front page renders the latest edition with links pointing into its folder
        front = env.get_template("edition.html.j2").render(
            ed=normalise(editions[latest]) | {"edition_no": len(dates)}, root="", base=f"editions/{latest}/", is_latest=True)
        (SITE / "index.html").write_text(front, encoding="utf-8")
    (SITE / "archive.html").write_text(
        env.get_template("archive.html.j2").render(archive=list(reversed(archive)), root=""), encoding="utf-8")
    (SITE / ".nojekyll").write_text("")
    print(f"Built {len(dates)} edition(s); latest = {dates[-1] if dates else None}")


if __name__ == "__main__":
    main()
