# The Tone at the Top — daily GRC newspaper

If you are running as the daily scheduled task (curation run): read and follow `prompts/curate.md` exactly.
Do not explore the repo, install packages, or modify anything other than `editions/<today>.json`
and (only when repairing a dead feed) `config/sources.yaml`.

Layout: `scripts/fetch.py` (headlines, no AI) → `editions/*.json` (AI curation) → `scripts/build.py` (site) →
`scripts/send_email.py` (6 a.m. email). Workflows live in `.github/workflows/`.
