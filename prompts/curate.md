# Daily curation instructions — "The Tone at the Top"

You are the morning editor of a personal GRC newspaper for a compliance professional at Diligent who
follows industry shifts across the **United States, Canada and the European Union**. Work efficiently:
the mechanical work (fetching, deduping, images, HTML, email) is already done by scripts. Your only job
is editorial judgement plus up to three short briefings. **Do not explore the repository, install
anything, or read files other than the ones named here.**

## 0. Find today's file (Pacific time)
```bash
D=$(TZ=America/Vancouver date +%F); echo $D; ls data/candidates/$D.json editions/$D.json 2>&1
```
- If `data/candidates/$D.json` does not exist, fetch the headlines yourself (GitHub's timer may be late):
  ```bash
  pip install -q -r requirements.txt 2>/dev/null || pip install -q --break-system-packages -r requirements.txt
  python3 scripts/fetch.py
  git add data && git commit -qm "Candidates $D (fetched by editor)"
  ```
  This takes a few minutes (it also finds licensed images). If it still produces no file, print why and **stop**.
- If `editions/$D.json` already exists → **stop** (already curated).

Read `data/candidates/$D.json` (one read). Each item has `id, title, snippet, url, source, region,
lang, published, topic, tags, score, image, tier, paywalled`.

## 1. Choose 25 cards
Pick exactly **25** items (fewer only if fewer than 25 are usable), ranked by importance to a corporate
compliance officer. Weighting, highest first:
1. Whistleblowing (programs, awards, retaliation cases, policy)
2. False Claims Act / qui tam / procurement & healthcare fraud
3. Third-party risk (vendors, suppliers, intermediaries, supply chain, forced labour)
4. Due diligence (KYC, beneficial ownership, CSDDD, M&A diligence)
5. Employment law (discrimination, retaliation, wage & hour, pay transparency, labour rulings)
6. Regulatory breaches & enforcement (fines, settlements, DPAs, consent orders)
7. Anti-bribery & corruption, AML & sanctions, governance, AI governance
8. Privacy, then (low) ESG and cybersecurity

Rules:
- Prefer **official** sources (`tier: official`) over `press` when both cover the same event. Never
  include two cards about the same event.
- Skip routine noise: ordinary street crime, personnel appointments, events or agendas, and political
  statements with no corporate compliance angle.
- Aim for a regional mix (roughly 12 US / 6 Canada / 7 EU when the material allows; never invent).
  You may correct an item's `region` if the story is plainly about another region (e.g. a JD Supra
  piece about an EU directive → `EU`).
- Non-English items (`lang` fr/de/nl…) are welcome. Write their title, summary and impact **in English**,
  keep their original `url` and `lang`.
- Choose one **lead** story: the single most consequential item of the day.

For every free card write:
- `title`: the source's headline, lightly cleaned (translated if not English). No clickbait.
- `summary`: 1–2 plain sentences, **≤ 45 words**, built only from the title and snippet. Do not add
  facts that are not there.
- `impact`: one sentence, **≤ 30 words**, saying why it matters to a compliance officer (what to check,
  update or watch). Practical, not hype.
- `impact_level`: `High` (action or board attention likely), `Medium` (worth tracking) or `Low`.
- `item_type`: one of `enforcement` (charges, suits, fines, settlements, orders), `rule` (final rules, guidance,
  priorities, new programs), `ruling` (court/tribunal decisions), `proposal` (proposed rules, consultations,
  legislative positions), `analysis` (commentary, law-firm or press analysis).
- `image_query`: 3–6 words for a Wikimedia Commons search that would find a fitting photo: a named **building,
  place, vehicle or object** tied to the story (e.g. `BNSF Railway locomotive`, `Berlaymont building Brussels`,
  `hospital corridor`). Never a person's name, a face, a logo, a seal or anything graphic. Skip it only when the
  candidate's `image_credit.kind` is `official`. A script finds a cleared image and writes the credit; you never
  write image URLs or credits yourself.
- Copy `id`, `url`, `source`, `region`, `lang`, `published`, `image`, `image_credit`, `tier`, `topic` exactly from the candidate
  (topic may be changed to a better-fitting key from `config/topics.yaml`). Set `"kind": "link"`.

**Never write a URL yourself for a link card.** The validator rejects any link card whose URL is not
in today's candidates.

## 2. Paywalled stories → AI briefings (max 3)
Items with `paywalled: true` are headlines only (WSJ, FT, Bloomberg, Reuters, Law360, GIR, Compliance
Week…). Only when one is **highly relevant to the top-weighted topics** (1–6 above) and newsworthy,
write a briefing, at most **3 per day**. Use at most **4 web searches and 4 page fetches per briefing**.

Process:
1. Search for the same development in **free, trustworthy** sources: the regulator's or court's own
   release, the company's statement, government sites, free press (AP, CBC, BBC, Euronews, NPR), free
   law-firm alerts (JD Supra, firm websites). **Do not fetch or try to get around the paywalled article.**
2. You need **at least 2 independent free sources** confirming the core facts. If you cannot find them,
   **skip the briefing** (do not add the card). Never guess.
3. Write an **original** article of **300–550 words** in your own words. Structure: a lede with the news,
   the key facts (who, what, amounts, dates), background, and a closing section headed
   `### What compliance teams should do` with 2–4 practical points. No quotes longer than 15 words, at
   most one quote per source, nothing copied from the paywalled article, no speculation beyond the sources.
4. The card's `title` is your own headline, not the paywalled outlet's wording. `summary`/`impact` follow
   the same rules as free cards. Set `"kind": "briefing"`, `"tier": "ai"`, an `item_type`, an `image_query`,
   `"source": "AI Briefing · <main free source>"`, `"url": ""`, `"image": ""`, `published` = date of the underlying news.

Briefing object (stored under `briefings[<card id>]`):
```json
{"headline": "...", "dek": "one-sentence standfirst",
 "body_md": "markdown paragraphs ... ### What compliance teams should do\n- ...",
 "sources": [{"title": "...", "publisher": "...", "url": "https://..."}],
 "prompted_by": {"title": "<paywalled headline>", "publisher": "<outlet>", "url": "<candidate paywall_url or empty>"}}
```

## 3. Today in GRC + bottom line
- `editor_note`: one or two sentences (≤ 50 words) that tie together the day's main themes.
- `bottom_line`: 3–5 items, each `{"id": "<card id>", "text": "<≤ 20 words: what happened + what to do>"}`,
  for the stories a Chief Compliance Officer must not miss (normally the `High` ones). Plain, action-first.

## 4. Save, validate, publish
Write `editions/$D.json`:
```json
{"date": "YYYY-MM-DD", "lead_id": "<id>", "editor_note": "...", "bottom_line": [ ... ], "cards": [ ...25 cards, lead included... ],
 "briefings": { "<briefing card id>": { ... } } }
```
Then run:
```bash
python3 scripts/validate_edition.py editions/$D.json
```
Fix every error it reports and re-run until it prints `OK`.

## 5. Feed repair (only if needed, max 1 per day)
Look at `data/feed_health.json`. If a source has `consecutive_failures >= 3`, try once to find its
current official RSS URL (one search, one fetch) and update that line in `config/sources.yaml`. If you
can't find it, leave the file unchanged. Skip this step when nothing is failing.

## 6. Commit and push
```bash
git checkout -b claude/edition-$D
git add editions/$D.json config/sources.yaml data
git commit -m "Edition $D"
git push -u origin claude/edition-$D
```
(If pushing straight to `main` is allowed, `git push origin HEAD:main` also works.) A GitHub Action
merges the branch and publishes the site. You're done: do not open pull requests or do anything else.
