# The Tone at the Top — daily GRC newspaper

If you are running as the daily scheduled task (curation run): read and follow `prompts/curate.md` exactly.
Do not explore the repo or modify anything other than `editions/<today>.json`, the `data/` files written by
`scripts/fetch.py` (only when today's candidates are missing), and (only when repairing a dead feed) `config/sources.yaml`.
Installing `requirements.txt` is allowed for that fetch step.

Layout: `scripts/fetch.py` (headlines, no AI) → `editions/*.json` (AI curation) → `scripts/build.py` (site) →
`scripts/send_email.py` (6 a.m. email). Workflows live in `.github/workflows/`.
