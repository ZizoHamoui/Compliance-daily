# Podcast run: "The Tone at the Top" daily audio briefing

You make today's audio episode in **Google NotebookLM in the owner's Chrome** (Claude in Chrome, already signed in),
then hand the audio to GitHub, which publishes it. You do not write the script; NotebookLM does.
Be efficient. Do not explore the repository. Do not change anything in NotebookLM except the one notebook named below.
Never touch other notebooks, Google settings or anything outside notebooklm.google.com.

## 0. Check there is work to do (cloud shell)
```bash
cd compliance-daily 2>/dev/null || git clone -q --depth 1 https://github.com/ZizoHamoui/compliance-daily && cd compliance-daily
git pull -q
python3 scripts/podcast.py latest      # prints "<date> todo" or "<date> done"
python3 scripts/podcast.py prompt      # the prompt and settings you will paste
date -u +%s                            # START: used to find the download
```
- If it says `done` → reply "Today's episode already exists" and **stop**.
- `D` = that date. The NotebookLM source URL is `SRC=https://zizohamoui.github.io/Compliance-daily/podcast/kit/<D>.html`.

## 1. Make the episode in Chrome
Load the Claude in Chrome tools (and the chrome-browser skill if listed). Start with the tab context, then work in a **new tab**.
1. Go to `https://notebooklm.google.com`. If you see a sign-in page or a Google error → **stop** and report it.
2. Open the notebook titled **Tone at the Top — Daily audio**. If it doesn't exist: **Create new** notebook, close the
   add-sources dialog, click the "Untitled notebook" title and rename it to exactly that name.
3. **Sources panel:** remove every existing source (each source's ⋮ menu → Remove source → confirm).
4. **Add source → Website** (may be labelled "Websites" or "Link"), paste `SRC`, press Insert.
   Wait until the source appears with a title containing "daily briefing" and the date. If it fails to load, open `SRC`
   in another tab to confirm the page exists (the site may still be deploying; wait 2 minutes and retry once).
5. **Studio panel:** if older Audio Overview items exist, delete them (⋮ → Delete) so the notebook stays tidy.
6. **Audio Overview → Customize** (the pencil icon on the Audio Overview card):
   - Format **Deep Dive** · Length **Shorter** · Language **English**
   - Prompt box: paste the prompt from step 0 exactly.
   - Press **Generate**.
7. Wait for it to finish: check every 60 seconds (a quick screenshot or find), for up to 20 minutes. It is ready when the item shows a
   play control instead of "Generating". If NotebookLM shows a limit or error message → **stop** and report the exact message.
8. On the finished audio item: **⋮ → Download**. Wait 15 seconds.

## 2. Collect the downloaded file (owner's computer → this session)
1. Get the device info. The **Downloads** folder must be a connected folder. If it isn't, request access to it once with a short reason.
2. List Downloads and pick the newest file ending in .wav, .m4a or .mp3 whose modified time is after START (mtime is in ms).
   If nothing yet, wait 15 seconds and look again (up to 2 minutes).
3. Stage that file into this session.

## 3. Hand it to GitHub
```bash
F="/mnt/user-data/uploads/Downloads/<file name>"     # the staged path reported by the stage tool
git checkout -q -b claude/podcast-$D
mkdir -p podcast/inbox
if command -v ffmpeg >/dev/null; then ffmpeg -hide_banner -loglevel error -y -i "$F" -vn -ac 1 -c:a aac -b:a 96k podcast/inbox/$D.m4a
else cp "$F" podcast/inbox/; fi
ls -la podcast/inbox
git add -f podcast/inbox && git commit -qm "Podcast audio $D" && git push -q origin claude/podcast-$D
```
The push starts the "Publish podcast episode" workflow. It converts the audio, rejects anything under 2.5 or over 25 minutes,
publishes it and deletes the branch. Reply in one or two lines: the episode date, its length, and that it was handed off.
Leave the NotebookLM tab open; do not delete the generated audio from NotebookLM.
