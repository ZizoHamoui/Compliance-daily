"""Decides whether a scheduled job should run now (handles DST double-crons). Writes go=true/false."""
import os
import sys

from common import get_state, now_local, today_local

job = sys.argv[1]
force = "--force" in sys.argv
n, today, st = now_local(), today_local(), get_state()
mins = n.hour * 60 + n.minute
if job == "email":
    go = force or (st.get("last_email") != today and 5 * 60 + 30 <= mins <= 9 * 60)
else:
    go = force or (st.get("last_fetch") != today and n.hour < 5)
print(f"{job}: local {n:%Y-%m-%d %H:%M}, go={go}")
with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
    f.write(f"go={'true' if go else 'false'}\nforce={'true' if force else 'false'}\n")
