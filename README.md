# The Tone at the Top

A free, fully automated morning newspaper of governance, risk and compliance news from the **United States,
Canada and the European Union**, published to GitHub Pages and emailed at 6 a.m. Pacific.

**Read it:** https://zizohamoui.github.io/Compliance-daily/

## How it works (no laptop needed)

| Time (Pacific) | What | Runs on | Cost |
|---|---|---|---|
| ~2:35–3:35 a.m. | `fetch.py` pulls ~30 official/free feeds, filters by weighted topics (EN/FR/DE/NL), dedupes, grabs preview images → `data/candidates/DATE.json` | GitHub Actions | free |
| ~4:30 a.m. | Claude scheduled task picks 25 stories, writes summary + "news impact" for each, and up to 3 **AI briefings** for important paywalled stories (rebuilt from ≥2 free sources) → `editions/DATE.json` | Claude (1 of 5 daily Pro runs) | included in Pro |
| ~5:55 a.m. | Merge the edition, build the site, deploy Pages, send the email | GitHub Actions | free |

If the Claude run ever fails, an **Express edition** (headlines only, still linking to official sources) is
published and emailed instead, so the paper is never missing.

**Done once, reused daily:** sources, topic weights, templates, prompt and validator live in the repo; Claude only
reads one ~15k-token file each morning. `data/seen.json` makes sure no story repeats.

## Customise

- `config/topics.yaml`: topic weights and multilingual keywords (whistleblowing, FCA, third-party risk, due diligence and employment law are weighted highest)
- `config/sources.yaml`: feeds. Broken feeds are logged in `data/feed_health.json` and repaired by the daily run.
- `config/paper.yaml`: name, number of cards, number of briefings
- `templates/` + `static/`: the look of the paper

## Manual controls

- Edit `.github/run-fetch` and commit → fetch now
- Edit `.github/send-test-email` and commit → send the email now
- Repo secrets: `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` (Gmail app password), optional `EMAIL_TO`
