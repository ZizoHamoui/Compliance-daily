"""Step 4 (GitHub Actions, no AI): email the morning link via Gmail SMTP.

Env: GMAIL_ADDRESS (sender), GMAIL_APP_PASSWORD, optional EMAIL_TO (defaults to sender).
Usage: python scripts/send_email.py [--force]
"""
import argparse
import os
import smtplib
import sys
from email.message import EmailMessage
from datetime import datetime
from html import escape

from common import CANDIDATES, EDITIONS, PAPER, ROOT, get_state, load_yaml, now_local, read_json, set_state, today_local

TOPICS = load_yaml("topics.yaml")["topics"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    today = today_local()
    if not args.force:
        n = now_local()
        mins = n.hour * 60 + n.minute
        if get_state().get("last_email") == today:
            print("Email already sent today.")
            return 0
        if mins < 5 * 60 + 30:
            print(f"Local time {n:%H:%M} is before 05:30; skipping.")
            return 0

    sender = os.environ.get("GMAIL_ADDRESS", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = os.environ.get("EMAIL_TO", "").strip() or sender
    if not sender or not pw:
        print("GMAIL_ADDRESS / GMAIL_APP_PASSWORD secrets are not set.", file=sys.stderr)
        return 1

    ed = read_json(EDITIONS / f"{today}.json", None)
    express = ed is None
    if express:
        cand = read_json(CANDIDATES / f"{today}.json", {"items": []})
        cards = [i for i in cand["items"] if not i["paywalled"]][:25]
        note = "Express edition: headlines only today."
    else:
        cards = ed["cards"]
        note = ed.get("editor_note", "")
        lead = next((c for c in cards if c["id"] == ed.get("lead_id")), None)
        if lead:
            cards = [lead] + [c for c in cards if c is not lead]
    url = PAPER["site_url"]
    date_long = now_local().strftime("%A, %B %-d, %Y")
    n_brief = sum(1 for c in cards if c.get("kind") == "briefing")

    regions = [("US", "US"), ("CA", "Canada"), ("UK", "UK"), ("EU", "EU")]
    rc = {r: sum(1 for c in cards if c.get("region") == r) for r, _ in regions}
    stats = (f'{len(cards)} stories · ' + " · ".join(f"{name} {rc[r]}" for r, name in regions if rc[r])) if not express else ""
    by_id = {c["id"]: c for c in cards}
    things = [] if express else [b for b in (ed.get("bottom_line") or []) if b.get("id") in by_id][:3]
    stat = None if express else ed.get("stat")
    if stat and stat.get("id") not in by_id:
        stat = None
    sec_h = 'padding:18px 28px 0;font:700 11px Arial;letter-spacing:2px;color:#0A66C2;text-transform:uppercase'
    things_html = ""
    if things:
        lis = "".join(f'<tr><td valign="top" style="padding:6px 12px 6px 0;font:700 20px Georgia,serif;color:#0A66C2">{i}</td>'
                      f'<td style="padding:6px 0;font:15px/1.45 Arial,sans-serif;color:#052962">{escape(t["text"])}</td></tr>'
                      for i, t in enumerate(things, 1))
        things_html = (f'<tr><td style="{sec_h}">{["", "One thing", "Two things", "Three things"][len(things)]} to know</td></tr>'
                       f'<tr><td style="padding:6px 28px 0"><table cellpadding="0" cellspacing="0">{lis}</table></td></tr>')
    stat_html = ""
    if stat:
        stat_html = (f'<tr><td style="padding:14px 28px 0"><table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F8FC;border-left:4px solid #0A66C2">'
                     f'<tr><td style="padding:12px 16px"><div style="font:700 10px Arial;letter-spacing:1.5px;color:#0A66C2">STAT OF THE DAY</div>'
                     f'<div style="font:700 17px/1.35 Georgia,serif;color:#052962;margin-top:4px">{escape(stat["text"])}</div></td></tr></table></td></tr>')
    rows = []
    for c in cards[:5]:
        topic = TOPICS.get(c.get("topic"), {}).get("label", "")
        why = c.get("impact") or (c.get("snippet") or "")[:200]
        rows.append(f'''<tr><td style="padding:14px 0;border-bottom:1px solid #E1E8F1">
<div style="font:600 10px Arial;letter-spacing:1.5px;color:#0A66C2;text-transform:uppercase">{escape(c.get("region", ""))} · {escape(topic)}{" · AI BRIEFING" if c.get("kind") == "briefing" else ""}</div>
<div style="font:700 18px/1.25 Georgia,serif;color:#052962;margin:4px 0">{escape(c["title"])}</div>
{f'<div style="font:14px/1.45 Arial,sans-serif;color:#052962"><b style="color:#0A66C2">Why it matters.</b> {escape(why)}</div>' if why else ""}
<div style="margin-top:6px;font:11px Arial;color:#56687A">{escape(c.get("source", ""))}</div>
</td></tr>''')

    # podcast button: the newest episode, while it's at most 2 days old (episodes are made after the 6 a.m. email)
    listen = ""
    ep = next(iter(read_json(ROOT / "podcast" / "episodes.json", [])[::-1]), None)
    if ep and (now_local().date() - datetime.fromisoformat(ep["date"]).date()).days <= 2:
        mins = max(1, round(ep["seconds"] / 60))
        listen = (f'<tr><td style="padding:14px 28px 0"><table width="100%" cellpadding="0" cellspacing="0" style="background:#EEF3F9;border-radius:16px">'
                  f'<tr><td style="padding:14px 18px"><div style="font:700 10px Arial;letter-spacing:1.5px;color:#0A66C2">AUDIO BRIEFING · {mins} MIN LISTEN</div>'
                  f'<div style="font:700 16px/1.3 Georgia,serif;color:#052962;margin:4px 0 0">{escape(ep["title"])}</div></td>'
                  f'<td align="right" style="padding:14px 18px"><a href="{url}podcast/index.html#ep-{ep["date"]}" style="display:inline-block;background:#0A66C2;color:#FFFFFF;'
                  f'font:700 13px Arial;letter-spacing:1px;text-decoration:none;padding:11px 18px;border-radius:999px;white-space:nowrap">&#9654;&nbsp; LISTEN</a></td></tr></table></td></tr>')
    subtitle_html = " ".join(
        (f'<span style="color:#0A66C2;font-weight:800">T</span>{escape(w[1:])}' if w[:1].upper() == "T" else escape(w))
        for w in PAPER.get("subtitle", "").split())
    html = f'''<!DOCTYPE html><html><body style="margin:0;background:#F5F8FC">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F8FC"><tr><td align="center" style="padding:24px 12px">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FFFFFF;border:1px solid #E1E8F1">
<tr><td style="padding:22px 28px 10px;text-align:center;border-bottom:4px solid #0A66C2">
<div style="font:11px Arial;letter-spacing:2px;color:#34435E;text-transform:uppercase">{date_long}</div>
<div style="font:11px Arial;letter-spacing:2px;color:#56687A;text-transform:uppercase;margin:8px 0 6px">{escape(PAPER["tagline"])}</div>
<div style="font:900 38px Georgia,serif;color:#052962;margin:0 0 4px">{escape(PAPER["name"])}</div>
<div style="font:600 15px Georgia,serif;color:#052962">{subtitle_html}</div></td></tr>
<tr><td style="padding:18px 28px 4px;font:15px/1.5 Georgia,serif;color:#052962">{escape(note)}</td></tr>
<tr><td style="padding:8px 28px 0;font:13px/1.6 Arial,sans-serif;color:#56687A">{stats}</td></tr>
{things_html}
{stat_html}
{listen}
<tr><td style="{sec_h}">{"Top stories" if not express else "Today's headlines"}</td></tr>
<tr><td style="padding:6px 28px"><table width="100%" cellpadding="0" cellspacing="0">{"".join(rows)}</table></td></tr>
<tr><td align="center" style="padding:22px 28px 28px">
<a href="{url}" style="display:inline-block;background:#052962;color:#F5F8FC;font:700 14px Arial;letter-spacing:1px;text-decoration:none;padding:14px 28px">READ TODAY'S PAPER · {len(cards)} STORIES{f" · {n_brief} BRIEFING{'S' if n_brief > 1 else ''}" if n_brief else ""}</a>
</td></tr></table>
<div style="font:11px/1.5 Arial;color:#56687A;padding:12px">Internal reference only: AI-assisted, not legal advice, not for forwarding to clients.<br>Sent automatically at 6:00 a.m. Pacific.</div>
</td></tr></table></body></html>'''

    msg = EmailMessage()
    msg["Subject"] = f"{PAPER['name']} — {now_local():%a %b %-d}: {cards[0]['title'][:80] if cards else 'today'}"
    msg["From"] = f"{PAPER['name']} <{sender}>"
    msg["To"] = to
    msg.set_content(f"{PAPER['name']} — {date_long}\n\n{note}\n\nRead today's paper: {url}\n")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(sender, pw)
        s.send_message(msg)
    set_state(last_email=today)
    print(f"Sent to {to} ({'express' if express else 'curated'} edition, {len(cards)} stories).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
