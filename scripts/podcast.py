"""Weekly podcast (made by hand in Google NotebookLM; everything around it is automatic).

    python scripts/podcast.py digest [--date YYYY-MM-DD]     print the NotebookLM sources file (default: latest edition)
    python scripts/podcast.py prompt                         print the NotebookLM prompt and settings
    python scripts/podcast.py latest                         print the latest edition date and whether it has an episode
    python scripts/podcast.py kit-email [--date YYYY-MM-DD]  email the producer kit to the paper's owner
    python scripts/podcast.py add --input FILE [--tag T] [--title T]
                                                             convert an uploaded episode to MP3 and register it

The weekly routine is in docs/podcast.md. Episodes live in podcast/audio/, their details in podcast/episodes.json.
"""
import argparse
import os
import re
import smtplib
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from email.message import EmailMessage
from html import escape
from urllib.parse import quote

from common import EDITIONS, PAPER, ROOT, load_yaml, now_local, read_json, today_local, write_json

POD_CFG = PAPER.get("podcast", {}) or {}
DAYS = int(POD_CFG.get("days", 1))            # 1 = a daily episode of that day's edition; 7 = a weekly recap
KEEP = int(POD_CFG.get("keep", 14))           # episodes kept online (audio lives on the podcast-audio branch)
MINUTES = 6 if DAYS == 1 else 9
PODCAST = ROOT / "podcast"
AUDIO = Path(os.environ.get("PODCAST_AUDIO_DIR") or PODCAST / "audio")
REGISTRY = PODCAST / "episodes.json"
REPO = os.environ.get("GITHUB_REPOSITORY") or PAPER.get("repo", "zizohamoui/Compliance-daily")
TOPICS = load_yaml("topics.yaml")["topics"]
REGIONS = {"US": "United States", "CA": "Canada", "EU": "European Union"}
DEFAULT_TITLE = "Today in compliance" if DAYS == 1 else "This week in compliance"

# Pasted into NotebookLM's "Customize" box. NotebookLM limits this box (reportedly 500 characters),
# so the detailed direction lives in the PRODUCER NOTES at the top of the sources file instead.
if DAYS == 1:
    PROMPT = ("Audience: chief compliance officers in the US, Canada and EU. Make a ~6-minute daily briefing on this edition. "
              "Follow the PRODUCER NOTES and running order in the source: the day in one line, ACT NOW stories in depth "
              "(what happened, who is affected, what to do), the WATCH stories briefly, quick hits, then one thing to do today. "
              "Name the regulator for each story. Plain, calm, professional English. Stay strictly within the sources; no legal advice.")
else:
    PROMPT = ("Audience: chief compliance officers in the US, Canada and EU. Make a ~9-minute weekly briefing. "
              "Follow the PRODUCER NOTES and running order in the source: the week in one line, ACT NOW stories in depth "
              "(what happened, who is affected, what to do), the WATCH list briefly, quick hits, then one thing to do Monday. "
              "Name the regulator and date for each story. Plain, calm, professional English. "
              "Stay strictly within the sources; no legal advice.")
SETTINGS = [("Format", "Deep Dive"),
            ("Length", "Shorter" if DAYS == 1 else "Default (use Shorter if episodes run past 12 minutes)"),
            ("Language", "English")]

_NOTES = """PRODUCER NOTES FOR THE HOSTS
- Audience: chief compliance officers, general counsel and GRC teams in the United States, Canada and the European Union. They are experts: skip basic definitions and get to consequences.
- Target length: about {minutes} minutes. Spend most of the time on ACT NOW. Cover WATCH in a sentence or two each. Read QUICK HITS as a fast list.
- Running order:
  1. Open with the name of the show, "The Tone at the Top {show}", the {span} covered, and the {unit} in one sentence.
  2. ACT NOW: for each story say who acted (the regulator, court or agency), when, what happened, who is affected, and the practical step a compliance team should take.
  3. WATCH: what is coming and when it could bite.
  4. QUICK HITS: one line each.
  5. Close with ONE concrete thing to do {when}, then a reminder that this is AI-generated and not legal advice; listeners should check the linked sources.
- Always name the jurisdiction (U.S., Canada, EU or the member state).
- Use only facts in this document. Do not guess penalties, dates or names that are not written here.
- Tone: calm, precise and practical. No hype, no jokes about enforcement actions or victims.
"""
PRODUCER_NOTES = _NOTES.format(minutes=MINUTES, show="daily briefing" if DAYS == 1 else "weekly briefing",
                               span="date" if DAYS == 1 else "dates", unit="day" if DAYS == 1 else "week",
                               when="today" if DAYS == 1 else "on Monday morning")


def slug(s):  # same rule as build.py, so links match the briefing pages
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "briefing"


def fmt(d):
    return datetime.fromisoformat(d).strftime("%b %-d") if isinstance(d, str) else d.strftime("%b %-d")


def week_range(end, days=DAYS):
    end_d = date.fromisoformat(end)
    return (end_d - timedelta(days=days - 1)).isoformat(), end


def latest_edition(on_or_before=None):
    cap = on_or_before or today_local()
    eds = sorted(p.stem for p in EDITIONS.glob("*.json") if p.stem <= cap)
    return eds[-1] if eds else cap


def digest(end=None, days=DAYS):
    """Collect the stories from the `days` editions ending on `end` (default: the latest edition) into a NotebookLM sources file."""
    end = end or latest_edition()
    start, end = week_range(end, days)
    days = sorted((p.stem for p in EDITIONS.glob("*.json") if start <= p.stem <= end), reverse=True)
    seen, stories, notes, briefings = set(), [], [], []
    for d in days:
        ed = read_json(EDITIONS / f"{d}.json", {}) or {}
        if ed.get("editor_note"):
            notes.append((d, ed["editor_note"]))
        for c in ed.get("cards", []):
            key = c.get("id") or c.get("url")
            if key in seen:
                continue
            seen.add(key)
            s = dict(c, edition=d, level=(c.get("impact_level") or "Low").capitalize())
            s["weight"] = TOPICS.get(c.get("topic"), {}).get("weight", 1.0)
            if c.get("kind") == "briefing":
                b = (ed.get("briefings") or {}).get(c["id"], {})
                s["link"] = f"{PAPER['site_url']}editions/{d}/b/{slug(b.get('headline') or c['title'])}.html"
                if b.get("body_md"):
                    briefings.append((c["title"], b.get("body_md", "")))
            else:
                s["link"] = c.get("url", "")
            stories.append(s)
    rank = lambda s: (-s["weight"], s["edition"])
    high = sorted([s for s in stories if s["level"] == "High"], key=rank)[:20]
    medium = sorted([s for s in stories if s["level"] == "Medium"], key=rank)[:15]
    low = sorted([s for s in stories if s["level"] not in ("High", "Medium")], key=rank)[:15]

    def block(i, s, full=True):
        meta = " · ".join(x for x in [fmt(s.get("published") or s["edition"]), REGIONS.get(s.get("region"), s.get("region", "")),
                                      s.get("source", ""), TOPICS.get(s.get("topic"), {}).get("label", "")] if x)
        out = [f"{i}. {s['title']}", f"   {meta}"]
        if full:
            if s.get("summary"):
                out.append(f"   What happened: {s['summary']}")
            if s.get("impact"):
                out.append(f"   Why it matters: {s['impact']}")
        elif s.get("impact") or s.get("summary"):
            out.append(f"   {s.get('impact') or s.get('summary')}")
        out.append(f"   Source: {s['link']}")
        return "\n".join(out)

    if start == end:
        title = f"{PAPER['name']} daily briefing, {datetime.fromisoformat(end):%A %B %-d, %Y}"
    else:
        title = f"{PAPER['name']} weekly briefing, {fmt(start)} to {fmt(end)}, {end[:4]}"
    parts = [title.upper(), f"{PAPER['regions']} · {len(stories)} stories from {len(days)} edition{'s' if len(days) != 1 else ''}", "", PRODUCER_NOTES]
    if len(notes) == 1:
        parts += ["THE DAY IN ONE LINE (the editor's summary)", notes[0][1], ""]
    elif notes:
        parts += ["THE WEEK, DAY BY DAY (the editor's one-line summary of each edition)"]
        parts += [f"- {datetime.fromisoformat(d):%A %b %-d}: {n}" for d, n in notes] + [""]
    for name, group, full in [("ACT NOW", high, True), ("WATCH", medium, True), ("QUICK HITS", low, False)]:
        if group:
            parts += [f"SECTION: {name} ({len(group)} stor{'y' if len(group) == 1 else 'ies'})", ""]
            parts += [block(i, s, full or days == 1) + "\n" for i, s in enumerate(group, 1)]
    for t, body in briefings:
        parts += [f"BACKGROUND BRIEFING: {t}", body.strip()[:2500], ""]
    parts += ["END OF SOURCES. Everything above was summarised from official and free public sources by an AI editor."]
    show_notes = [{"title": s["title"], "url": s["link"], "source": s.get("source", ""), "level": s["level"]} for s in high + medium]
    return {"start": start, "end": end, "title": title, "text": "\n".join(parts), "stories": show_notes, "count": len(stories)}


def episodes():
    return sorted(read_json(REGISTRY, []), key=lambda e: e["date"], reverse=True)


def upload_link(end, title=DEFAULT_TITLE):
    body = "Attach the NotebookLM audio file here, then press Publish release. The site updates itself in a few minutes."
    return (f"https://github.com/{REPO}/releases/new?tag=podcast-{end}"
            f"&title={quote(title + ' — ' + fmt(end))}&body={quote(body)}")


# ---------------------------------------------------------------- kit email
def kit_email(end=None):
    d = digest(end)
    sender = os.environ.get("GMAIL_ADDRESS", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = os.environ.get("PODCAST_PRODUCER", "").strip() or sender   # the owner, not the reader list
    if not (sender and pw):
        print("GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set; printing the kit instead.\n")
        print(d["text"])
        return 0
    if d["count"] == 0:
        print("No editions this week; no kit sent.")
        return 0
    kit = PAPER["site_url"] + "podcast/kit/"
    up = upload_link(d["end"])
    fname = f"tone-at-the-top-week-{d['end']}.txt"
    li = "padding:0 0 12px;font:15px/1.5 Arial,sans-serif;color:#052962"
    settings = "".join(f"<b>{escape(k)}:</b> {escape(v)}<br>" for k, v in SETTINGS)
    html = f'''<!DOCTYPE html><html><body style="margin:0;background:#F5F8FC">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F8FC"><tr><td align="center" style="padding:24px 12px">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FFFFFF;border:1px solid #E1E8F1">
<tr><td style="padding:22px 28px 12px;border-bottom:4px solid #0A66C2">
<div style="font:700 11px Arial;letter-spacing:2px;color:#0A66C2;text-transform:uppercase">Podcast kit · about 5 minutes of your time</div>
<div style="font:900 26px Georgia,serif;color:#052962;margin:8px 0 4px">This week's episode: {escape(fmt(d['start']))} to {escape(fmt(d['end']))}</div>
<div style="font:14px Arial;color:#34435E">{d['count']} stories, {len(d['stories'])} in the show notes. The sources file is attached.</div></td></tr>
<tr><td style="padding:20px 28px 4px"><table cellpadding="0" cellspacing="0">
<tr><td style="{li}"><b>1.</b> Open <a href="https://notebooklm.google.com" style="color:#0A66C2">NotebookLM</a> and create a new notebook. Upload the attached <b>{escape(fname)}</b> as the only source.</td></tr>
<tr><td style="{li}"><b>2.</b> In Studio, open <b>Audio Overview → Customize</b> and choose:<br>{settings}</td></tr>
<tr><td style="{li}"><b>3.</b> Paste this into the prompt box, then press Generate:
<div style="margin-top:8px;padding:12px 14px;background:#EEF3F9;border-left:4px solid #0A66C2;font:14px/1.5 Georgia,serif;color:#052962">{escape(PROMPT)}</div></td></tr>
<tr><td style="{li}"><b>4.</b> Listen to the start and end to check it. Then use <b>⋮ → Download</b> (it saves a WAV file).</td></tr>
<tr><td style="{li}"><b>5.</b> Press the button below, drag the file onto the page and press <b>Publish release</b>. The site and the next morning email pick it up automatically.</td></tr>
</table></td></tr>
<tr><td align="center" style="padding:6px 28px 26px">
<a href="{up}" style="display:inline-block;background:#052962;color:#F5F8FC;font:700 14px Arial;letter-spacing:1px;text-decoration:none;padding:14px 28px">UPLOAD THE EPISODE</a>
<div style="font:12px Arial;color:#56687A;margin-top:12px">Lost the attachment? The <a href="{kit}" style="color:#0A66C2">producer kit page</a> always has the current week's file and this prompt.</div>
</td></tr></table></td></tr></table></body></html>'''
    msg = EmailMessage()
    msg["Subject"] = f"Podcast kit: week of {fmt(d['start'])} to {fmt(d['end'])}"
    msg["From"] = f"{PAPER['name']} <{sender}>"
    msg["To"] = to
    msg.set_content(f"Podcast kit for {fmt(d['start'])} to {fmt(d['end'])}.\n\n1. NotebookLM → new notebook → upload the attached file.\n"
                    f"2. Audio Overview → Customize: Deep Dive, Default length, English.\n3. Prompt:\n{PROMPT}\n\n"
                    f"4. Download the audio.\n5. Upload it here and press Publish release: {up}\n\nKit page: {kit}\n")
    msg.add_alternative(html, subtype="html")
    msg.add_attachment(d["text"].encode("utf-8"), maintype="text", subtype="plain", filename=fname)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(sender, pw)
        s.send_message(msg)
    print(f"Podcast kit sent to {to} ({d['count']} stories).")
    return 0


# ---------------------------------------------------------------- add an uploaded episode
def probe_seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return int(round(float(out)))


def add(input_path, tag="", title="", min_s=150, max_s=1500):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", tag or "")
    ep_date = m.group(1) if m else today_local()
    title = (title or "").strip()
    if not title or title == tag:
        title = f"{DEFAULT_TITLE} — {fmt(ep_date)}"
    AUDIO.mkdir(parents=True, exist_ok=True)
    out = AUDIO / f"{ep_date}.mp3"
    # 64 kbps mono, loudness-normalised to the podcast standard (-16 LUFS): about 0.5 MB per minute
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(input_path), "-vn",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "44100", "-b:a", "64k",
                    "-metadata", f"title={title}", "-metadata", f"artist={PAPER['name']}",
                    "-metadata", "comment=AI-generated with Google NotebookLM. Not legal advice.", str(out)], check=True)
    secs = probe_seconds(out)
    if not (min_s <= secs <= max_s):
        out.unlink()
        print(f"Rejected: episode is {secs // 60}m{secs % 60:02d}s, outside {min_s // 60}-{max_s // 60} minutes. Nothing published.")
        return 3
    d = digest(ep_date)
    eps = [e for e in read_json(REGISTRY, []) if e["date"] != ep_date]
    eps.append({"date": ep_date, "title": title, "file": out.name, "seconds": secs, "bytes": out.stat().st_size,
                "start": d["start"], "end": d["end"], "stories": d["stories"], "added": now_local().isoformat(timespec="minutes")})
    write_json(REGISTRY, sorted(eps, key=lambda e: e["date"])[-90:])
    for old in sorted(AUDIO.glob("*.mp3"))[:-KEEP]:   # the audio branch only ever holds the newest episodes
        old.unlink()
    print(f"Added episode {ep_date}: {title} ({eps[-1]['seconds'] // 60} min, {out.stat().st_size // 1024} KB)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["digest", "prompt", "latest", "kit-email", "add"])
    ap.add_argument("--date")
    ap.add_argument("--input")
    ap.add_argument("--tag", default="")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    if a.cmd == "digest":
        print(digest(a.date)["text"])
        return 0
    if a.cmd == "prompt":
        print(PROMPT)
        print("\n".join(f"{k}: {v}" for k, v in SETTINGS))
        return 0
    if a.cmd == "latest":
        d = latest_edition()
        done = any(e["date"] == d for e in read_json(REGISTRY, []))
        print(f"{d} {'done' if done else 'todo'}")
        return 0
    if a.cmd == "kit-email":
        return kit_email(a.date)
    if not a.input:
        ap.error("add needs --input")
    return add(a.input, a.tag, a.title)


if __name__ == "__main__":
    sys.exit(main())
