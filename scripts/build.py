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
ACTION = {"High": ("required", "Action required"), "Medium": ("monitor", "Monitor"), "Low": ("fyi", "FYI")}
TYPES = {"enforcement": "Enforcement action", "rule": "New rule / guidance", "ruling": "Court ruling",
         "proposal": "Proposal / consultation", "analysis": "Analysis"}
TIERS = {"official": "Official source", "press": "Expert analysis", "ai": "AI briefing"}
LANGS = {"en": "English", "fr": "French", "de": "German", "nl": "Dutch", "es": "Spanish", "it": "Italian"}

# palette per topic for the generated card illustrations (used when an article has no image)
TOPIC_COLORS = {k: ("#052962", "#DCE6F1") for k in ["whistleblowing", "false_claims", "third_party_risk", "due_diligence", "employment_law", "enforcement", "anti_bribery", "aml_sanctions", "governance", "ai_governance", "privacy", "esg", "cybersecurity"]}
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


NAVY_TILE, VERD_TILE = ("#DCE6F1", "#052962"), ("#DCEBFA", "#0A66C2")  # Guardian Blue / LinkedIn Blue tiles
TOPIC_TINTS = {  # on-brand tiles: alternate Ink and Verdigris so the grid has rhythm without leaving the palette
    "whistleblowing": VERD_TILE, "false_claims": NAVY_TILE, "third_party_risk": VERD_TILE, "due_diligence": NAVY_TILE,
    "employment_law": VERD_TILE, "enforcement": NAVY_TILE, "anti_bribery": VERD_TILE, "aml_sanctions": NAVY_TILE,
    "governance": NAVY_TILE, "ai_governance": VERD_TILE, "privacy": NAVY_TILE, "esg": VERD_TILE, "cybersecurity": NAVY_TILE,
}


def topic_svg(key):
    light, deep = TOPIC_TINTS.get(key, ("#ececf0", "#454753"))
    glyph = TOPIC_GLYPH.get(key, TOPIC_GLYPH["governance"])
    label = TOPICS.get(key, {}).get("label", "Compliance").upper().replace("&", "&amp;")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 200" preserveAspectRatio="xMidYMid slice">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="{light}"/></linearGradient>
<filter id="s" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="{deep}" flood-opacity=".18"/></filter></defs>
<rect width="480" height="200" fill="url(#g)"/>
<circle cx="410" cy="30" r="90" fill="{light}" opacity=".9"/><circle cx="60" cy="190" r="70" fill="{light}" opacity=".7"/>
<rect x="200" y="46" width="80" height="80" rx="24" fill="#ffffff" filter="url(#s)"/>
<g transform="translate(212,58) scale(.56)" fill="none" stroke="{deep}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"><path d="{glyph}"/></g>
<text x="240" y="160" text-anchor="middle" font-family="Roboto Flex,Helvetica,Arial,sans-serif" font-size="13" font-weight="600" letter-spacing="1.5" fill="{deep}">{label}</text>
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


TYPE_HINTS = [
    ("ruling", r"\b(court|judge|circuit|tribunal|verdict|ruling|rules that|held that|appeal)\b"),
    ("proposal", r"\b(propos|consultation|draft|seeks comment|call for evidence|mandate|trilogue|position on)"),
    ("rule", r"\b(guidance|final rule|regulation|directive|priorities|code|launch|pilot|program|framework|withdraw)"),
    ("enforcement", r"\b(sue|sues|charged|charges|settle|penalt|fine|fined|order|judgment|plead|sentenc|takedown|violat|resolv)"),
]


def guess_type(c):
    if c.get("kind") == "briefing":
        return c.get("item_type") or "analysis"
    text = (c.get("title", "") + " " + c.get("summary", "")).lower()
    if c.get("tier") == "press":
        return "analysis"
    for key, rx in TYPE_HINTS:
        if re.search(rx, text):
            return key
    return "analysis"


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
    if ed.get("_normalised"):
        return ed
    ed["_normalised"] = True
    cand = read_json(CANDIDATES / f"{ed['date']}.json", {"items": []})
    cand_tiers = {i["id"]: i.get("tier") for i in cand["items"]}
    order = {"High": 0, "Medium": 1, "Low": 2}
    ed["cards"].sort(key=lambda c: order.get((c.get("impact_level") or "Low").capitalize(), 3))
    for c in ed["cards"]:
        c.setdefault("kind", "link")
        c["topic"] = c.get("topic") if c.get("topic") in TOPICS else "governance"
        c["topic_label"] = TOPICS[c["topic"]]["label"]
        c["region_label"] = REGIONS.get(c.get("region"), c.get("region", ""))
        c["lang"] = c.get("lang") or "en"
        c["lang_label"] = LANGS.get(c["lang"], c["lang"].upper())
        c["date_label"] = fmt_date(c.get("published"))
        c["impact_level"] = (c.get("impact_level") or "").capitalize()
        c["action"], c["action_label"] = ACTION.get(c["impact_level"], ("fyi", "FYI"))
        if c["kind"] == "briefing":
            c["tier"] = "ai"
        c["tier"] = c.get("tier") if c.get("tier") in TIERS else (cand_tiers.get(c["id"]) or "official")
        c["tier_label"] = TIERS[c["tier"]]
        c["item_type"] = c.get("item_type") if c.get("item_type") in TYPES else guess_type(c)
        c["type_label"] = TYPES[c["item_type"]]
        c["band"] = TOPIC_COLORS.get(c["topic"], ("#2a2a2a",))[0]
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
    ed["topic_options"] = [(k, TOPICS[k]["label"]) for k in ed["topics_present"]]
    ed["regions_present"] = [r for r in REGIONS if any(c.get("region") == r for c in ed["cards"])]
    ids = {c["id"]: c for c in ed["cards"]}
    bl = [b for b in (ed.get("bottom_line") or []) if b.get("id") in ids and b.get("text")]
    if not bl:  # fallback: the High-impact stories' impact lines
        bl = [{"id": c["id"], "text": c["impact"]} for c in ed["cards"] if c["action"] == "required" and c.get("impact")][:4]
    ed["bottom_line"] = bl
    ed["counts"] = {
        "action": {k: sum(1 for c in ed["cards"] if c["action"] == k) for k in ("required", "monitor", "fyi")},
        "region": {r: sum(1 for c in ed["cards"] if c.get("region") == r) for r in REGIONS},
    }
    return ed


def main():
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    env.filters["md"] = lambda s: markdown.markdown(s or "", extensions=["extra", "sane_lists"])
    env.globals.update(paper=PAPER, topics=TOPICS, regions=REGIONS, types=TYPES, tiers=TIERS)

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
    (SITE / "saved.html").write_text(env.get_template("saved.html.j2").render(root=""), encoding="utf-8")
    (SITE / "archive.html").write_text(
        env.get_template("archive.html.j2").render(archive=list(reversed(archive)), root=""), encoding="utf-8")
    (SITE / ".nojekyll").write_text("")
    print(f"Built {len(dates)} edition(s); latest = {dates[-1] if dates else None}")


if __name__ == "__main__":
    main()
