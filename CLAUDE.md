# The Tone at the Top — daily GRC newspaper

If you are running as the daily scheduled task (curation run): read and follow `prompts/curate.md` exactly.
Do not explore the repo or modify anything other than `editions/<today>.json` and (only when repairing a dead feed)
`config/sources.yaml`. If today's candidates are missing, request a fetch exactly as `prompts/curate.md` describes and wait for it.

Layout: `scripts/fetch.py` (headlines, no AI) → `editions/*.json` (AI curation) → `scripts/build.py` (site) →
`scripts/send_email.py` (6 a.m. email). Workflows live in `.github/workflows/`.
Daily podcast: if you are running as the **podcast task**, read and follow `prompts/podcast.md` exactly instead (it drives NotebookLM in
the owner's Chrome and pushes `claude/podcast-<date>`). Code: `scripts/podcast.py`, `podcast/`, `docs/podcast.md`. The curation run never touches it.
