"""Step 1 (GitHub Actions, no AI): collect, filter, score and dedupe headlines.

Writes data/candidates/YYYY-MM-DD.json — the only file the AI curator reads.
Usage: python scripts/fetch.py [--force]
  --force skips the "already fetched today / wrong hour" guard (used for manual runs).
"""
import argparse
import calendar
import concurrent.futures as cf
import html
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import feedparser

from common import (CANDIDATES, DATA, PAPER, get_state, load_yaml, now_local, read_json,
                    set_state, today_local, uid, write_json)

UA = ("Mozilla/5.0 (compatible; ToneAtTheTopBot/1.0; personal compliance news digest; "
      "+https://github.com/ZizoHamoui/compliance-daily)")
HEADERS = {"User-Agent": UA, "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml,*/*"}

SOURCES = load_yaml("sources.yaml")
TOPICS = load_yaml("topics.yaml")
PAYWALLED = [p.lower() for p in SOURCES.get("paywalled_publishers", [])]


# ---------------------------------------------------------------- keyword matching
def compile_kw(kw):
    kw = kw.strip().lower()
    if kw.endswith("*"):
        return re.compile(r"(?<!\w)" + re.escape(kw[:-1]))
    return re.compile(r"(?<!\w)" + re.escape(kw) + r"(?!\w)")


TOPIC_RX = {k: (v["weight"], [compile_kw(w) for w in v["keywords"]]) for k, v in TOPICS["topics"].items()}
EXCLUDE_RX = [compile_kw(w) for w in TOPICS.get("exclude", [])]


def score(title, summary):
    t, s = title.lower(), summary.lower()
    if any(rx.search(t) or rx.search(s) for rx in EXCLUDE_RX):
        return 0.0, None, []
    per_topic = {}
    for key, (w, rxs) in TOPIC_RX.items():
        hits = sum(3 for rx in rxs if rx.search(t)) + sum(1 for rx in rxs if rx.search(s))
        if hits:
            per_topic[key] = min(hits, 7) * w
    if not per_topic:
        return 0.0, None, []
    ranked = sorted(per_topic.items(), key=lambda kv: -kv[1])
    total = ranked[0][1] + 0.35 * sum(v for _, v in ranked[1:])
    return round(total, 2), ranked[0][0], [k for k, _ in ranked[:3]]


# ---------------------------------------------------------------- fetching
def http_get(url, timeout=25, limit=None):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit) if limit else r.read()


def clean(text, n=None):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:n].rsplit(" ", 1)[0] + "…" if n and len(text) > n else text


def entry_time(e):
    for k in ("published_parsed", "updated_parsed"):
        if e.get(k):
            return datetime.fromtimestamp(calendar.timegm(e[k]), tz=timezone.utc)
    return None


BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def fetch_source(src):
    last = None
    for attempt in range(3):
        try:
            feed = feedparser.parse(http_get(src["url"]))
            if not feed.entries:  # some sites serve bots an empty/HTML page: retry once as a browser
                req = urllib.request.Request(src["url"], headers={**HEADERS, "User-Agent": BROWSER_UA})
                with urllib.request.urlopen(req, timeout=25) as r:
                    feed = feedparser.parse(r.read())
            if not feed.entries and not src.get("may_be_empty"):
                raise ValueError("feed returned no items (blocked or moved?)")
            return src, feed.entries, None
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"[:200]
            time.sleep(2 * (attempt + 1))
    return src, [], last


OG_RX = re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)(?::src)?["\'][^>]+content=["\']([^"\']+)["\']', re.I)
OG_RX2 = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']', re.I)
BAD_IMG = ("logo", "favicon", "default", "placeholder", "sprite", "wmms", "icon", "seal")


def find_image(url):
    try:
        page = http_get(url, timeout=12, limit=300_000).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return ""
    m = OG_RX.search(page) or OG_RX2.search(page)
    if not m:
        return ""
    img = html.unescape(m.group(1)).strip()
    if img.startswith("//"):
        img = "https:" + img
    elif img.startswith("/"):
        img = re.match(r"https?://[^/]+", url).group(0) + img
    if not img.startswith("http") or any(b in img.lower() for b in BAD_IMG):
        return ""
    # make sure the image actually loads for a browser (some sites block hotlinking)
    try:
        req = urllib.request.Request(img, headers={"User-Agent": "Mozilla/5.0", "Referer": ""})
        with urllib.request.urlopen(req, timeout=8) as r:
            if r.status != 200 or not r.headers.get("Content-Type", "").startswith("image/"):
                return ""
            if int(r.headers.get("Content-Length") or 99999) < 4000:  # tiny = icon/spacer
                return ""
    except Exception:  # noqa: BLE001
        return ""
    return img


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    today = today_local()
    state = get_state()
    if not args.force:
        hour = now_local().hour
        if state.get("last_fetch") == today:
            print(f"Already fetched for {today}; nothing to do.")
            return
        if not (0 <= hour < 5):
            print(f"Local hour {hour} outside fetch window; skipping (use --force to override).")
            return

    seen = read_json(DATA / "seen.json", {})
    health = read_json(DATA / "feed_health.json", {})
    cutoff = datetime.now(timezone.utc) - timedelta(hours=PAPER.get("lookback_hours", 72))
    first_run = not seen
    if first_run:  # first ever run: look back a week so the paper is full
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    with cf.ThreadPoolExecutor(10) as ex:
        results = list(ex.map(fetch_source, SOURCES["sources"]))

    items, now_iso = [], datetime.now(timezone.utc).isoformat(timespec="seconds")
    for src, entries, err in results:
        h = health.get(src["id"], {})
        if err:
            h.update(consecutive_failures=h.get("consecutive_failures", 0) + 1, last_error=err, url=src["url"])
            print(f"  FAIL {src['id']}: {err}", file=sys.stderr)
        else:
            h.update(consecutive_failures=0, last_ok=now_iso, last_count=len(entries), url=src["url"], last_error=None)
        health[src["id"]] = h

        for e in entries:
            link = (e.get("link") or "").strip()
            title = clean(e.get("title"))
            if not link or not title:
                continue
            published = entry_time(e)
            if published and published < cutoff:
                continue
            default_topic, base = src.get("topic"), src.get("base", 0)
            if src["kind"] == "gcnews":
                dept = e.get("author", "")
                if dept not in src.get("departments", {}):
                    continue
                source_name = dept
                default_topic, base = src["departments"][dept]
            else:
                source_name = src["name"]
            paywalled = False
            if src["kind"] == "paywall":
                # Google News titles look like "Headline - Publisher"
                pub = src.get("publisher") or (e.get("source") or {}).get("title") or (
                    title.rsplit(" - ", 1)[-1] if " - " in title else "")
                if not src.get("publisher") and pub.lower() not in PAYWALLED:
                    continue  # free outlets are not used; only official sources are linked
                title = title.rsplit(" - ", 1)[0] if title.endswith(pub) else title
                source_name, paywalled = pub, True
            key = uid(link if not paywalled else title.lower())
            if key in seen:
                continue
            summary = clean(e.get("summary") or e.get("description"), 420)
            s, topic, tags = score(title, summary)
            if s == 0 and base >= 2 and not any(rx.search(title.lower()) for rx in EXCLUDE_RX) and default_topic:
                topic, tags = default_topic, [default_topic]  # high-signal agency: keep even without keyword hits
            s = s * src.get("weight", 1.0) + base
            if not topic or s <= 0:
                continue
            if paywalled and s < 8:  # only very relevant paywalled headlines are worth a briefing
                continue
            items.append({
                "id": key, "title": title, "snippet": summary if not paywalled else "",
                "url": link if not paywalled else "", "paywall_url": link if paywalled else "", "source": source_name, "source_id": src["id"],
                "region": src["region"], "lang": src.get("lang", "en"), "tier": src.get("tier", "official") if not paywalled else "paywalled",
                "published": published.isoformat(timespec="minutes") if published else None,
                "topic": topic, "tags": tags, "score": round(s, 2), "paywalled": paywalled,
                "image": "",
            })

    # Same story from two feeds (e.g. DOJ + SEC on one case): keep the best-scored copy.
    by_title = {}
    for it in sorted(items, key=lambda x: -x["score"]):
        k = re.sub(r"\W+", " ", it["title"].lower())[:80]
        by_title.setdefault(k, it)
    items = list(by_title.values())

    # Balance: best items per region, cap per source, then paywalled extras.
    limit = PAPER.get("candidate_limit", 90)
    free = sorted([i for i in items if not i["paywalled"]], key=lambda x: -x["score"])
    pay = sorted([i for i in items if i["paywalled"]], key=lambda x: -x["score"])[:12]
    per_source, per_region, chosen = {}, {}, []
    region_cap = {"US": 40, "CA": 20, "EU": 26}
    for it in free:
        if per_source.get(it["source_id"], 0) >= 12 or per_region.get(it["region"], 0) >= region_cap.get(it["region"], 30):
            continue
        chosen.append(it)
        per_source[it["source_id"]] = per_source.get(it["source_id"], 0) + 1
        per_region[it["region"]] = per_region.get(it["region"], 0) + 1
        if len(chosen) >= limit - len(pay):
            break
    chosen += pay

    # Preview images (free articles only), fetched in parallel.
    with cf.ThreadPoolExecutor(12) as ex:
        no_img = {x["id"] for x in SOURCES["sources"] if x.get("images") is False}
        imgs = ex.map(lambda it: find_image(it["url"]) if it["url"] and it["source_id"] not in no_img else "", chosen)
        for it, img in zip(chosen, imgs):
            it["image"] = img
    # the same picture on several stories is a stock banner (e.g. "Press Release"), not a news photo
    counts = {}
    for it in chosen:
        if it["image"]:
            counts[it["image"]] = counts.get(it["image"], 0) + 1
    for it in chosen:
        if counts.get(it["image"], 0) > 1:
            it["image"] = ""

    for it in items:  # everything scored today is marked seen, so nothing repeats tomorrow
        seen[it["id"]] = today
    horizon = (now_local() - timedelta(days=60)).strftime("%Y-%m-%d")
    seen = {k: v for k, v in seen.items() if v >= horizon}

    prev = read_json(CANDIDATES / f"{today}.json", None)
    if prev:  # a second run on the same day only adds new items
        known = {i["id"] for i in prev["items"]}
        chosen = prev["items"] + [i for i in chosen if i["id"] not in known]
        per_region = {}
        for i in chosen:
            if not i["paywalled"]:
                per_region[i["region"]] = per_region.get(i["region"], 0) + 1
        pay = [i for i in chosen if i["paywalled"]]
    out = {"date": today, "generated": now_iso, "count": len(chosen),
           "by_region": per_region, "paywalled": len(pay), "items": chosen}
    write_json(CANDIDATES / f"{today}.json", out)
    write_json(DATA / "seen.json", seen)
    write_json(DATA / "feed_health.json", health)
    set_state(last_fetch=today)

    # keep only the last 14 days of candidate files
    for f in sorted(CANDIDATES.glob("*.json"))[:-14]:
        f.unlink()
    print(f"Wrote {len(chosen)} candidates for {today} ({per_region}, {len(pay)} paywalled).")


if __name__ == "__main__":
    main()
