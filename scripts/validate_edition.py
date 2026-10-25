"""Checks an edition JSON written by the AI curator. Prints OK or a list of problems (exit 1).

Most importantly: every link card must use a URL that exists in that day's candidates, so no
invented links ever reach the paper.
"""
import json
import sys
from pathlib import Path

from common import CANDIDATES, PAPER, load_yaml

TOPICS = set(load_yaml("topics.yaml")["topics"])
LEVELS = {"High", "Medium", "Low"}
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
    if not (min(15, n) <= len(cards) <= n):
        errs.append(f"expected up to {n} cards (at least 15), got {len(cards)}")
    ids = [c.get("id") for c in cards]
    if len(set(ids)) != len(ids):
        errs.append("duplicate card ids")
    if ed.get("lead_id") not in ids:
        errs.append("lead_id is not one of the cards")
    briefs = ed.get("briefings") or {}
    nb = 0
    for i, c in enumerate(cards):
        tag = f"card {i + 1} ({c.get('id')})"
        for k in ("id", "title", "summary", "impact", "impact_level", "topic", "region", "source", "kind"):
            if not c.get(k):
                errs.append(f"{tag}: missing {k}")
        if c.get("topic") not in TOPICS:
            errs.append(f"{tag}: unknown topic {c.get('topic')!r}")
        if c.get("region") not in {"US", "CA", "EU"}:
            errs.append(f"{tag}: region must be US, CA or EU")
        if c.get("item_type") not in TYPES:
            errs.append(f"{tag}: item_type must be one of {sorted(TYPES)}")
        if c.get("impact_level") not in LEVELS:
            errs.append(f"{tag}: impact_level must be High, Medium or Low")
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
            if "What compliance teams should do" not in (b.get("body_md") or ""):
                errs.append(f"{tag}: briefing missing 'What compliance teams should do' section")
        else:
            errs.append(f"{tag}: kind must be link or briefing")
    bl = ed.get("bottom_line") or []
    if not (1 <= len(bl) <= 5):
        errs.append("bottom_line needs 1-5 items")
    for b in bl:
        if b.get("id") not in ids or not b.get("text") or words(b.get("text")) > 25:
            errs.append(f"bottom_line item invalid (unknown id or text missing/over 20 words): {b}")
    if nb > PAPER.get("max_briefings", 3):
        errs.append(f"too many briefings ({nb})")

    if errs:
        print("\n".join(errs))
        return 1
    print(f"OK — {len(cards)} cards, {nb} briefing(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
