"""Give every story an image whose rights are clear, with attribution.

Rules (see docs/images.md):
  1. A source's own preview image is used only when the publisher's reuse terms allow it:
     U.S. federal agencies (public-domain government works), the Government of Canada (non-commercial
     reproduction with attribution) and EU institutions (reuse with source acknowledged).
  2. Otherwise the image comes from Wikimedia Commons, and only under an open licence:
     CC0, public domain, CC BY or CC BY-SA. Author, licence and file page are stored and shown.
  3. Never: logos, seals, emblems or coats of arms (trademark and endorsement risk), portraits or close-ups of
     people (personality rights), graphic or sensitive imagery, maps or charts, files flagged with restrictions,
     small or non-landscape images.
  4. Search order: the editor's `image_query` → the source's headquarters → a vetted query for the topic.
     If nothing passes, the story keeps its own topic illustration (made for this site, no third-party rights).

Usage:
  python scripts/images.py editions/2026-10-24.json      # fill/upgrade images in an edition
  python scripts/images.py data/candidates/2026-10-24.json
"""
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from common import DATA, read_json, write_json

UA = {"User-Agent": "ToneAtTheTopBot/1.0 (https://github.com/ZizoHamoui/Compliance-daily; personal news digest)"}
CACHE_FILE = DATA / "image_cache.json"

# ---- publisher images we may reuse, with the credit line they require -------------------------------------
OFFICIAL_IMAGE_TERMS = [
    (re.compile(r"(^|\.)(sec|justice|dol|eeoc|cftc|federalreserve|consumerfinance|treasury|nlrb|federalregister|ftc|osha)\.gov$"),
     "{source} (U.S. government work, public domain)"),
    (re.compile(r"(^|\.)(canada\.ca|gc\.ca)$"), "{source}, Government of Canada (reproduced for non-commercial use)"),
    (re.compile(r"(^|\.)europa\.eu$"), "© European Union ({source})"),
]


def official_credit(url, source):
    host = urllib.parse.urlparse(url or "").hostname or ""
    for rx, text in OFFICIAL_IMAGE_TERMS:
        if rx.search(host):
            return text.format(source=source)
    return None


# ---- Commons guardrails ---------------------------------------------------------------------------------
LICENSE_OK = re.compile(r"^(cc0|cc-zero|public domain|pdm|pd\b|pd-|no restrictions|cc[ -]by(-sa)?[ -]?[1-4]\.\d|cc[ -]by(-sa)?[ -]?2\.5)", re.I)
TITLE_BLOCK = re.compile(
    r"logo|seal of|\bseal\b|emblem|coat of arms|insignia|badge|wordmark|portrait|headshot|selfie|mugshot|official photo|"
    r"nude|naked|blood|wound|corpse|dead|injur|weapon|\bgun|rifle|riot|protest|map\b|diagram|chart|graph|signature|screenshot|"
    r"\bflag of\b|caricature|cartoon|scenario|"
    r"child|children|kids|\bboy\b|\bgirl\b|student|pupil|baby|people|crowd|airmen|soldier|ceremony|briefing|meeting|visit|"
    r"\bbar\b|restaurant|nightclub", re.I)
STOP = set("the of and a an in on for to at by with from de la le des du et u s us".split())

SOURCE_QUERIES = {
    "U.S. SEC": "Securities and Exchange Commission headquarters building",
    "U.S. Department of Justice": "Robert F. Kennedy Department of Justice Building",
    "U.S. Department of Labor": "Frances Perkins Building Department of Labor",
    "U.S. EEOC": "Equal Employment Opportunity Commission building",
    "U.S. CFTC": "Commodity Futures Trading Commission building",
    "U.S. CFTC Enforcement": "Commodity Futures Trading Commission building",
    "Federal Reserve Board": "Marriner S. Eccles Federal Reserve Board Building",
    "U.S. CFPB": "Consumer Financial Protection Bureau headquarters",
    "U.S. NLRB": "National Labor Relations Board building",
    "U.S. Treasury OFAC": "Treasury Building Washington",
    "Federal Register": "United States Capitol",
    "European Commission": "Berlaymont building Brussels",
    "European Parliament": "European Parliament building Brussels",
    "European Data Protection Board": "European Quarter Brussels buildings",
    "European Banking Authority": "Paris La Défense towers",
    "Competition Bureau Canada": "Place du Portage Gatineau",
    "Privacy Commissioner of Canada": "Parliament Hill Ottawa",
    "Financial Consumer Agency of Canada": "Parliament Hill Ottawa",
    "Department of Justice Canada": "Supreme Court of Canada building",
    "Canada Border Services Agency": "Canada border crossing",
    "AMF (France)": "La Défense Paris business district",
    "CNIL (France)": "Paris skyline",
    "Autorité de la concurrence (France)": "Paris skyline",
}
TOPIC_QUERIES = {
    "whistleblowing": ["whistle", "megaphone"], "false_claims": ["hospital corridor", "courthouse columns"],
    "third_party_risk": ["container port cranes", "shipping containers port"], "due_diligence": ["magnifying glass", "library archive shelves"],
    "employment_law": ["office interior desks", "factory workers hall"], "enforcement": ["courthouse columns", "gavel"],
    "anti_bribery": ["banknotes", "euro banknotes"], "aml_sanctions": ["bank building facade", "stock exchange trading floor"],
    "governance": ["boardroom table", "conference room"], "ai_governance": ["data center servers", "computer server room"],
    "privacy": ["padlock", "security camera"], "esg": ["wind turbines", "solar panels"], "cybersecurity": ["server room", "fiber optic cables"],
}


def _tokens(s):
    return {w for w in re.findall(r"[a-zà-ÿ0-9]+", s.lower()) if w not in STOP and len(w) > 2}


def _strip(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _get_json(url):
    """GET with polite pacing and retry on 429/5xx (Wikimedia asks bots to back off)."""
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                wait = int(e.headers.get("Retry-After") or 0) or 4 * (2 ** attempt)
                time.sleep(min(wait, 60))
                continue
            raise
    return {}


def commons_search(query, cache, strict=True):
    key = query.lower().strip()
    if key in cache:
        return cache[key]
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
              "gsrnamespace": 6, "gsrlimit": 15, "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1200}
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    results = []
    time.sleep(1.2)  # pace requests
    try:
        pages = _get_json(url).get("query", {}).get("pages", {})
    except Exception as e:  # noqa: BLE001
        print(f"  commons error for {query!r}: {e}", file=sys.stderr)
        return None  # not cached: try again next run
    qtok = _tokens(query)
    for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        m = ii.get("extmetadata", {})
        title = p.get("title", "")
        lic = _strip(m.get("LicenseShortName", {}).get("value", ""))
        restrictions = _strip(m.get("Restrictions", {}).get("value", ""))
        w, h = ii.get("width", 0), ii.get("height", 1)
        if not LICENSE_OK.search(lic) or restrictions or TITLE_BLOCK.search(title):
            continue
        if ii.get("mime") not in ("image/jpeg", "image/png") or w < 900 or not (1.2 <= w / h <= 2.4):
            continue
        overlap = len(qtok & _tokens(title + " " + _strip(m.get("ImageDescription", {}).get("value", ""))[:300]))
        need = max(1, (len(qtok) + 1) // 2) if strict else 1   # specific searches must match most of their words
        if overlap < need:
            continue
        author = _strip(m.get("Artist", {}).get("value", "")) or "Unknown author"
        results.append({
            "score": overlap,
            "image": (ii.get("thumburl") or ii.get("url") or "").split("?")[0],
            "credit": {"kind": "commons", "author": author[:80], "license": lic,
                       "license_url": _strip(m.get("LicenseUrl", {}).get("value", "")),
                       "source_url": ii.get("descriptionurl", ""), "provider": "Wikimedia Commons",
                       "title": title.replace("File:", "")},
        })
    results.sort(key=lambda r: -r["score"])
    cache[key] = results[:5]
    return cache[key]


def credit_text(c):
    if not c:
        return ""
    if c.get("kind") == "official":
        return c["text"]
    return f'{c["author"]} / {c["provider"]}, {c["license"]}'


def fill(items, cache, used=None):
    """items: dicts with url, source, topic, image, image_query (optional). Mutates in place."""
    used = used if used is not None else set()
    for it in items:
        if it.get("paywalled"):
            continue
        img, cred = it.get("image") or "", it.get("image_credit")
        if img and not cred:  # a preview image from the fetch step: keep only if reuse is allowed
            text = official_credit(it.get("url"), it.get("source", ""))
            if text:
                cred = {"kind": "official", "text": text, "source_url": it.get("url", "")}
            else:
                img = ""
        if img and cred and cred.get("kind") == "official":
            it["image"], it["image_credit"] = img, cred
            used.add(img)
            continue
        if img and cred and not it.get("image_query"):
            used.add(img)
            continue
        queries = [(q, True) for q in [it.get("image_query"), SOURCE_QUERIES.get(it.get("source", ""))] if q]
        queries += [(q, False) for q in TOPIC_QUERIES.get(it.get("topic"), ["office building"])]
        chosen = None
        for q, strict in queries:
            for r in commons_search(q, cache, strict) or []:
                if r["image"] not in used:
                    chosen = r
                    break
            if chosen:
                break
        if chosen:
            it["image"], it["image_credit"] = chosen["image"], chosen["credit"]
            used.add(chosen["image"])
        else:
            it["image"], it["image_credit"] = "", None   # site falls back to its own topic illustration
    return items


def main(path):
    path = Path(path)
    doc = read_json(path, None)
    if doc is None:
        print(f"{path} not found")
        return 1
    cache = read_json(CACHE_FILE, {})
    items = doc.get("cards") or doc.get("items") or []
    fill(items, cache)
    # trim the cache so it stays small
    if len(cache) > 600:
        cache = dict(list(cache.items())[-400:])
    write_json(CACHE_FILE, cache)
    write_json(path, doc)
    n = sum(1 for i in items if i.get("image"))
    print(f"{path.name}: {n}/{len(items)} items have a cleared image")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
