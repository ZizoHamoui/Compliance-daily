"""Step 4 (GitHub Actions, no AI): email the morning link via Gmail SMTP.

Env: GMAIL_ADDRESS (sender), GMAIL_APP_PASSWORD, optional EMAIL_TO (defaults to sender).
Usage: python scripts/send_email.py [--force]
"""
import argparse
import os
import smtplib
import sys
from email.message import EmailMessage
from html import escape

from common import CANDIDATES, EDITIONS, PAPER, get_state, load_yaml, now_local, read_json, set_state, today_local

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
        if not (5 * 60 + 30 <= mins <= 9 * 60):
            print(f"Local time {n:%H:%M} outside 05:30–09:00 window; skipping.")
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

    lvl_of = lambda c: (c.get("impact_level") or "").capitalize()
    n_req = sum(1 for c in cards if lvl_of(c) == "High")
    n_mon = sum(1 for c in cards if lvl_of(c) == "Medium")
    n_fyi = len(cards) - n_req - n_mon
    regions = {r: sum(1 for c in cards if c.get("region") == r) for r in ("US", "CA", "EU")}
    act_now = [c for c in cards if lvl_of(c) == "High"] or cards
    stats = (f'<span style="color:#b3261e;font-weight:700">{n_req} Action required</span> &nbsp;·&nbsp; '
             f'<span style="color:#9a6200;font-weight:700">{n_mon} Monitor</span> &nbsp;·&nbsp; {n_fyi} FYI'
             f'<br><span style="color:#6f6a60">US {regions["US"]} · Canada {regions["CA"]} · EU {regions["EU"]}</span>') if not express else ""
    rows = []
    for c in act_now[:4]:
        topic = TOPICS.get(c.get("topic"), {}).get("label", "")
        lvl = c.get("impact_level") or ""
        badge = (f'<span style="font:700 10px Arial;letter-spacing:1px;color:{"#9c1c1c" if lvl == "High" else "#a86b00" if lvl == "Medium" else "#4b5b6b"}">'
                 f'{ {"High": "ACTION REQUIRED", "Medium": "MONITOR", "Low": "FYI"}.get(lvl, "")}</span>&nbsp;&nbsp;') if lvl else ""
        rows.append(f'''<tr><td style="padding:14px 0;border-bottom:1px solid #d8cfbd">
<div style="font:600 10px Arial;letter-spacing:1.5px;color:#9c1c1c;text-transform:uppercase">{escape(c.get("region", ""))} · {escape(topic)}{" · AI BRIEFING" if c.get("kind") == "briefing" else ""}</div>
<div style="font:700 18px/1.25 Georgia,serif;color:#1a1916;margin:4px 0">{escape(c["title"])}</div>
<div style="font:14px/1.45 Arial,sans-serif;color:#1a1916"><b style="font-size:10px;letter-spacing:1px;color:#b3261e">WHY IT MATTERS</b> {escape(c.get("impact") or (c.get("snippet") or "")[:200])}</div>
<div style="margin-top:6px">{badge}<span style="font:11px Arial;color:#7b766b">{escape(c.get("source", ""))}</span></div>
</td></tr>''')

    html = f'''<!DOCTYPE html><html><body style="margin:0;background:#f5f0e6">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f0e6"><tr><td align="center" style="padding:24px 12px">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fffdf8;border:1px solid #d8cfbd">
<tr><td style="padding:22px 28px 10px;text-align:center;border-bottom:4px double #1a1916">
<div style="font:11px Arial;letter-spacing:2px;color:#4a4740;text-transform:uppercase">{date_long}</div>
<div style="font:900 34px Georgia,serif;color:#1a1916;margin:8px 0 4px">{escape(PAPER["name"])}</div>
<div style="font:italic 13px Georgia,serif;color:#4a4740">{escape(PAPER["tagline"])}</div></td></tr>
<tr><td style="padding:18px 28px 4px;font:15px/1.5 Georgia,serif;color:#1a1916">{escape(note)}</td></tr>
<tr><td style="padding:8px 28px 0;font:13px/1.6 Arial,sans-serif">{stats}</td></tr>
<tr><td style="padding:16px 28px 0;font:700 11px Arial;letter-spacing:2px;color:#b3261e">{"ACT NOW" if not express else "TOP HEADLINES"}</td></tr>
<tr><td style="padding:6px 28px"><table width="100%" cellpadding="0" cellspacing="0">{"".join(rows)}</table></td></tr>
<tr><td align="center" style="padding:22px 28px 28px">
<a href="{url}" style="display:inline-block;background:#1a1916;color:#f5f0e6;font:700 14px Arial;letter-spacing:1px;text-decoration:none;padding:14px 28px">READ TODAY'S PAPER · {len(cards)} STORIES{f" · {n_brief} BRIEFING{'S' if n_brief > 1 else ''}" if n_brief else ""}</a>
</td></tr></table>
<div style="font:11px Arial;color:#7b766b;padding:12px">Sent automatically at 6:00 a.m. Pacific by your Tone at the Top pipeline.</div>
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
