# The weekly podcast

A roughly 9-minute audio briefing each week, made in Google NotebookLM (free). The only manual part is about five minutes on Sunday;
everything around it is automatic.

## Your weekly routine (about 5 minutes)

1. **Sunday morning** you get an email, *Podcast kit: week of …*, with the week's sources file attached.
   (Workflow `6 · Weekly podcast kit`; run it from the Actions tab any time. The same file and prompt are always at
   `<site>/podcast/kit/`.)
2. Open [NotebookLM](https://notebooklm.google.com) → **New notebook** → upload the attached `.txt` as the only source.
3. **Studio → Audio Overview → Customize**:
   - Format: **Deep Dive**
   - Length: **Default** (switch to *Shorter* if episodes run past 12 minutes)
   - Language: English
4. Paste the prompt below into the prompt box → **Generate** (takes a few minutes).
5. Spot-check the start and end, then **⋮ → Download**. It saves a WAV file.
6. Press **Upload the episode** in the email. It opens a pre-filled GitHub *New release* page. Drag the WAV onto it and press
   **Publish release**.

That's it. Workflow `5 · Publish podcast episode` then:
- converts the file to a 64 kbps mono MP3, about 0.5 MB per minute, at standard podcast loudness;
- saves it in `podcast/audio/` and adds it to `podcast/episodes.json`, with show notes built from that week's Act now and Watch stories;
- deletes the release and republishes the site.

The **Listen** bar appears at the top of every edition, on the Podcast page and in the morning email for the next 8 days.

## The NotebookLM prompt

NotebookLM's prompt box is short (about 500 characters), so detailed direction sits in the **PRODUCER NOTES** at the top of the
sources file. Paste this:

> Audience: chief compliance officers in the US, Canada and EU. Make a ~9-minute weekly briefing. Follow the PRODUCER NOTES and
> running order in the source: the week in one line, ACT NOW stories in depth (what happened, who is affected, what to do), the
> WATCH list briefly, quick hits, then one thing to do Monday. Name the regulator and date for each story. Plain, calm,
> professional English. Stay strictly within the sources; no legal advice.

To change the prompt, edit `PROMPT` in `scripts/podcast.py`; the email and kit page update automatically.
To change the running order or tone, edit `PRODUCER_NOTES` in the same file.

## Good to know

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
