"""Checks an edition JSON written by the AI curator. Prints OK or a list of problems (exit 1).

Most importantly: every link card must use a URL that exists in that day's candidates, so no
invented links ever reach the paper.
"""
import json
import re
import sys
from pathlib import Path

from common import CANDIDATES, PAPER, load_yaml
import storylines as storylines_mod

TOPICS = set(load_yaml("topics.yaml")["topics"])
REGIONS = {"US", "CA", "UK", "EU"}
INDUSTRIES = set(PAPER.get("industries", {}))
PERSONAS = set(PAPER.get("personas", {}))
ADVICE = re.compile(r"\b(should|make sure|be sure to|ensure (?:that|your)|(?:check|review|update|revisit|test) (?:your|their|its)|consider whether)\b", re.I)
VENDORS = re.compile(r"\b(diligent|navex|eqs group|onetrust|convercent|logicgate|auditboard|workiva|metricstream)\b", re.I)
TYPES = {"enforcement", "rule", "ruling", "proposal", "analysis"}


def words(s):
    return len((s or "").split())


def main(path):
    errs = []
    try:
        ed = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"Invalid JSON: {e}")
        return 1
    date = ed.get("date")
    cand = CANDIDATES / f"{date}.json"
    if not cand.exists():
        errs.append(f"no candidates file for date {date!r}")
        items = {}
    else:
        items = {i["id"]: i for i in json.loads(cand.read_text(encoding="utf-8"))["items"]}
    urls = {i["url"] for i in items.values() if i.get("url")}

    cards = ed.get("cards") or []
    n = PAPER.get("cards_per_edition", 25)
    if not (1 <= len(cards) <= n):
        errs.append(f"expected 1 to {n} cards, got {len(cards)}")
    ids = [c.get("id") for c in cards]
    if len(set(ids)) != len(ids):
        errs.append("duplicate card ids")
    if ed.get("lead_id") not in ids:
        errs.append("lead_id is not one of the cards")
    briefs = ed.get("briefings") or {}
    nb = 0
    for i, c in enumerate(cards):
        tag = f"card {i + 1} ({c.get('id')})"
        for k in ("id", "title", "summary", "impact", "topic", "region", "source", "kind"):
            if not c.get(k):
                errs.append(f"{tag}: missing {k}")
        if c.get("topic") not in TOPICS:
            errs.append(f"{tag}: unknown topic {c.get('topic')!r}")
        if c.get("region") not in REGIONS:
            errs.append(f"{tag}: region must be US, CA, UK or EU")
        inds, pers = c.get("industries") or [], c.get("personas") or []
        if not inds or not set(inds) <= INDUSTRIES or len(inds) > 3:
            errs.append(f"{tag}: industries must be 1-3 of {sorted(INDUSTRIES)}")
        if not pers or not set(pers) <= PERSONAS:
            errs.append(f"{tag}: personas must be 1-4 of {sorted(PERSONAS)}")
        if ADVICE.search(c.get("impact") or ""):
            errs.append(f"{tag}: 'why it matters' must state significance, not advice (found {ADVICE.search(c['impact']).group(0)!r})")
        if VENDORS.search((c.get("title") or "") + " " + (c.get("summary") or "")):
            errs.append(f"{tag}: vendor or market news is out of scope")
        if c.get("item_type") not in TYPES:
            errs.append(f"{tag}: item_type must be one of {sorted(TYPES)}")
        if words(c.get("summary")) > 55:
            errs.append(f"{tag}: summary too long ({words(c.get('summary'))} words, max 45)")
        if words(c.get("impact")) > 38:
            errs.append(f"{tag}: impact too long ({words(c.get('impact'))} words, max 30)")
        if c.get("kind") == "link":
            if c.get("url") not in urls:
                errs.append(f"{tag}: url is not from today's candidates")
            if c.get("id") in items and items[c["id"]].get("paywalled"):
                errs.append(f"{tag}: paywalled items must be briefings, not links")
        elif c.get("kind") == "briefing":
            nb += 1
            b = briefs.get(c.get("id"))
            if not b:
                errs.append(f"{tag}: briefing body missing in briefings{{}}")
                continue
            if not (250 <= words(b.get("body_md")) <= 700):
                errs.append(f"{tag}: briefing should be 300-550 words (has {words(b.get('body_md'))})")
            srcs = [s for s in b.get("sources") or [] if str(s.get("url", "")).startswith("http")]
            if len(srcs) < 2:
                errs.append(f"{tag}: briefing needs at least 2 free sources with URLs")
            for sec in ("What this means for legal and compliance leaders", "Questions you may hear"):
                if sec not in (b.get("body_md") or ""):
                    errs.append(f"{tag}: briefing missing the '{sec}' section")
        else:
            errs.append(f"{tag}: kind must be link or briefing")
    bl = ed.get("bottom_line") or []
    if len(bl) != min(3, len(cards)):
        errs.append("bottom_line (Three things to know) needs exactly 3 items")
    for b in bl:
        if b.get("id") not in ids or not b.get("text") or words(b.get("text")) > 25:
            errs.append(f"bottom_line item invalid (unknown id or text missing/over 25 words): {b}")
        elif ADVICE.search(b["text"]):
            errs.append(f"bottom_line items are news, not advice: {b['text']!r}")
    st = ed.get("stat")
    if st is None:
        print("warning: no stat of the day")
    elif st.get("id") not in ids or not st.get("text") or words(st.get("text")) > 25 or not re.search(r"\d", st.get("text", "")):
        errs.append(f"stat must reference a card id and give a number in ≤ 25 words: {st}")
    pb = (ed.get("podcast_brief") or "").strip()
    if not pb:
        print("warning: podcast_brief missing; the podcast kit will fall back to card summaries")
    else:
        low = pb.lower()
        if words(pb) < 800:
            errs.append(f"podcast_brief too short ({words(pb)} words; aim for 1,500-2,600)")
        for need in ("## the day in one line", "## story 1", "**the facts.**", "**background.**", "**who's affected.**",
                     "**why it matters.**", "**how this comes up with a gc or clo.**", "**questions a buyer might ask.**"):
            if need not in low.replace("\u2019", "'"):
                errs.append(f"podcast_brief is missing the section {need!r}")
        if VENDORS.search(pb):
            errs.append("podcast_brief must not mention vendors or products")
        for banned in ("act now", "quick hits", "good to know", "what compliance teams should do", "what to do"):
            if banned in low:
                errs.append(f"podcast_brief must not contain {banned!r} (no priority labels, no advice)")
    known = {k: v["title"] for k, v in storylines_mod.collect(exclude_date=date).items()}
    declared = ed.get("storylines") or {}
    for slug, title in declared.items():
        if not storylines_mod.SLUG_RX.match(slug) or len(slug) > 60:
            errs.append(f"storyline slug {slug!r} must be lowercase-with-hyphens, ≤ 60 characters")
        if not title or len(title) > 70:
            errs.append(f"storyline {slug!r} needs a title of ≤ 70 characters")
        if slug in known:
            errs.append(f"storyline {slug!r} already exists; reuse it without redeclaring it")
    for c in cards:
        s = c.get("storyline")
        if s and s not in known and s not in declared:
            errs.append(f"card {c.get('id')}: storyline {s!r} is unknown; declare it under 'storylines' or use an existing one")
    if nb > PAPER.get("max_briefings", 3):
        errs.append(f"too many briefings ({nb})")

    if errs:
        print("\n".join(errs))
        return 1
    print(f"OK — {len(cards)} cards, {nb} briefing(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
