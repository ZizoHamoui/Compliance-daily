# The daily podcast

A ~10 minute audio briefing on each edition, made by Google's Gemini Notebook (formerly NotebookLM).

## The source document (podcast kit)
NotebookLM can't open links, so each day's kit is a self-contained briefing: notes for the hosts, the day in one line, then
every story numbered in order of importance, each with **The facts**, **Background**, **Who's affected**, **Why it matters** and
**Questions to explore**. There are no priority labels and no "what to do" advice. The morning editor writes the stories into the
edition (`podcast_brief`, rules in `prompts/curate.md` §3b), the validator checks the structure, and `scripts/podcast.py` adds the
host notes, sign-off and source list. If a day has no brief, a simpler version in the same format is built from the cards.

## One click (normal way)
Open your scheduled tasks and press **Run now** on **"Tone at the Top daily podcast"**, any time after the 6 a.m. paper.
Your Mac must be awake with Chrome open, the Claude extension connected and the Claude desktop app running.
The agent follows `prompts/podcast.md`:
1. It opens the notebook "Tone at the Top — Daily audio" and swaps in today's sources link (`<site>/podcast/kit/<date>.html`).
2. It runs Customise Audio Overview with Deep dive, Default length, English and the prompt, and waits for it to finish (a few minutes).
3. It downloads the `.m4a`, picks it up from your Downloads folder and pushes it to `claude/podcast-<date>`.
4. Workflow `5 · Publish podcast episode` converts it, rejects anything under 2.5 or over 25 minutes, and stores it on the
   `podcast-audio` branch (newest 14 only). It then records it and rebuilds the site.
5. The Listen bar appears on that edition, and the next morning's email has a Listen button.

If a step in Gemini Notebook changes, edit `prompts/podcast.md`; the scheduled task reads it fresh on every run.

## By hand (fallback)

1. Run the workflow `6 · Podcast kit (manual fallback)` from the Actions tab. You get an email, *Podcast kit: …*, with the sources file attached.
   (The same file and prompt are always at `<site>/podcast/kit/`.)
2. Open [NotebookLM](https://notebooklm.google.com) → **New notebook** → upload the attached `.txt` as the only source.
3. **Studio → Audio Overview → Customize**:
   - Format: **Deep Dive**
   - Length: **Default**
   - Language: English
4. Paste the prompt below into the prompt box → **Generate** (takes a few minutes).
5. Spot-check the start and end, then **⋮ → Download**. It saves a WAV file.
6. Press **Upload the episode** in the email. It opens a pre-filled GitHub *New release* page. Drag the WAV onto it and press
   **Publish release**.

That's it. Workflow `5 · Publish podcast episode` then:
- converts the file to a 64 kbps mono MP3, about 0.5 MB per minute, at standard podcast loudness;
- saves it in `podcast/audio/` and adds it to `podcast/episodes.json`, with show notes listing that edition's stories in the editor's order;
- deletes the release and republishes the site.

The new episode loads into the audio bar at the bottom of every page, appears on the Podcast page, and is linked from the next morning's email (for 2 days).

## The NotebookLM prompt

NotebookLM's prompt box is short (about 500 characters), so detailed direction sits in the **Notes for the hosts** at the top of the
source document. Paste this (it is also printed by `python scripts/podcast.py prompt`):

> Audience: solution engineers who meet general counsel, chief legal officers and compliance analysts. Make a ~10-minute daily briefing. Follow the Notes for the hosts in the source: open with the day in one line, cover every story in order (most time on the first three), and use each story's "How this comes up with a GC or CLO" and "Questions a buyer might ask" to drive the conversation. Calm, professional English. Stay strictly within the source; no legal advice.

To change the prompt, edit `PROMPT` in `scripts/podcast.py`; the kit email and kit page update automatically.
To change the timing or tone, edit `HOST_NOTES` in the same file.

## Notes

- **Tag = episode date.** The upload link uses the tag `podcast-YYYY-MM-DD`. Any release with an audio file attached is
  treated as an episode (WAV, M4A, MP3, AAC, OGG and WebM all work), and a missing date means today. Uploading the same date again
  replaces that episode.
- **Missed a week?** Nothing breaks. Editions keep showing the latest episode, and the email button hides once it's more than 8 days old.
- **A different recipient for the kit:** add a repository secret `PODCAST_PRODUCER` with that email address.
- **Storage:** the site keeps the 12 newest episodes. Each one is about 5 MB in git history, which is fine for years.
- **Disclosure:** the player, the Podcast page and each MP3's metadata say the audio is AI-generated with NotebookLM and not legal advice.
  The producer notes ask the hosts to say so at the end.
- **Terms:** this uses your personal NotebookLM account. If the podcast is shared with a wider team or company, check that
  Google's terms for your account type allow that use, or move it to a Workspace account.
