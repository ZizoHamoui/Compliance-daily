#!/usr/bin/env bash
# Merge editions pushed by the Claude scheduled task (branches claude/*) into main.
# Each new edition must pass the validator; otherwise it is skipped and the express edition stays.
set -euo pipefail
git config user.name "tone-at-the-top-bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

branches=$(git ls-remote --heads origin 'claude/*' | awk '{print $2}' | sed 's#refs/heads/##' || true)
changed=0
for b in $branches; do
  echo "Ingesting $b"
  git fetch --depth=1 origin "$b"
  for f in $(git diff --name-only HEAD "origin/$b" -- editions/ config/sources.yaml); do
    git checkout "origin/$b" -- "$f" 2>/dev/null || continue
    if [[ "$f" == editions/*.json ]]; then
      if ! python scripts/validate_edition.py "$f"; then
        echo "::warning::$f failed validation; keeping express edition"
        if git cat-file -e "HEAD:$f" 2>/dev/null; then git checkout HEAD -- "$f"; else git rm -q --cached "$f" || true; rm -f "$f"; fi
        continue
      fi
    fi
    git add "$f"; changed=1
  done
  git push origin --delete "$b" || true
done

if [[ $changed == 1 ]] && ! git diff --cached --quiet; then
  git commit -m "Ingest curated edition"
  git push origin HEAD:main
fi
echo "changed=$changed" >> "${GITHUB_OUTPUT:-/dev/null}"
