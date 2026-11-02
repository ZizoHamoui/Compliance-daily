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
NotebookLM is now called **Gemini Notebook**; `notebooklm.google.com` redirects to `notebook.google.com`. The account has PRO.
**Click controls by reference** (use `find` / `read_page`, then click the `ref`). The dialogs resize and shift, so
coordinates from an earlier screenshot often miss. Take a screenshot after each step to confirm it worked.
1. Go to `https://notebooklm.google.com`. If you see a sign-in page or a Google error → **stop** and report it.
   Close any "what's new" pop-ups (the X button) and dismiss "Get notified" banners ("Not now").
2. Open the notebook card titled **Tone at the Top — Daily audio** (search box at the top of My notebooks if needed).
   If it doesn't exist: **New notebook**, close pop-ups, select the "Untitled notebook" title textbox, type the name, press Enter.
3. **Sources panel:** remove every existing source (the source row's ⋮ "More" menu → Remove source → confirm).
4. **+ Sources → Websites** opens the "Website and YouTube URLs" dialog. Click the "Paste any links" box, type `SRC`, press **Insert**.
   Within about 10 seconds the source appears as "The Tone at the Top daily briefing, <weekday> <Month> <day>, <year>". Check that the
   date matches `D`. If it fails, open `SRC` in another tab to confirm the page exists (the site may still be deploying;
   wait 2 minutes and retry once).
5. **Studio panel:** if older Audio Overview items exist below the tiles, delete them (item ⋮ → Delete) so the notebook stays tidy.
6. Click the **Audio Overview** tile. It opens the **Customise Audio Overview** dialog:
   - Format **Deep dive** (selected by default) · Language **English** · Length: click the radio **Short**
   - Click the textbox "What should the AI hosts focus on in this episode?" and type the prompt from step 0 exactly.
   - Screenshot to confirm Short is ticked and the prompt is in the box, then click **Generate now** (not "Generate later").
7. A "Generating Audio Overview… Come back in a few minutes" item appears in Studio. Check every 60 seconds (a small screenshot)
   for up to 20 minutes. It is ready when the item shows a title and a play control. If a usage-limit or error message
   appears → **stop** and report the exact message. (The first run took about 4 minutes for a 6-minute episode.)
8. Note the episode's full title (hover it or use `find`). It becomes the episode title on the site.
   On the finished item, click its **More** (⋮) button, then the **Download** menu item. Chrome saves an `.m4a` named after the
   episode title (for example `DEA_Schedule_III_Registrations_Create_Compliance_Risks.m4a`, about 12 MB). Download may also open
   the item in a new tab; close that tab. Wait 10 seconds.
## 2. Collect the downloaded file (owner's computer → this session)
1. Get the device info. The **Downloads** folder must be a connected folder. If it isn't, request access to it once with a short reason.
2. List `/Users/hamoui/Downloads` and pick the newest file ending in .m4a, .wav or .mp3 whose `mtimeMs` is after START×1000.
   Ignore every other file in that folder; it holds the owner's personal documents, so never stage, open or mention them.
   If nothing matches yet, wait 15 seconds and look again (up to 2 minutes).
3. Stage that file into this session.

## 3. Hand it to GitHub
```bash
F="/mnt/user-data/uploads/Downloads/<file name>"     # the staged path reported by the stage tool
git checkout -q -b claude/podcast-$D
mkdir -p podcast/inbox
if command -v ffmpeg >/dev/null; then ffmpeg -hide_banner -loglevel error -y -i "$F" -vn -ac 1 -c:a aac -b:a 96k podcast/inbox/$D.m4a
else cp "$F" podcast/inbox/; fi
ls -la podcast/inbox
printf '%s' "<the episode title shown in NotebookLM>" > podcast/inbox/title.txt
git add -f podcast/inbox && git commit -qm "Podcast audio $D" && git push -q origin claude/podcast-$D
```
The push starts the "Publish podcast episode" workflow. It converts the audio, rejects anything under 2.5 or over 25 minutes,
publishes it and deletes the branch. Reply in one or two lines: the episode date, its length, and that it was handed off.
Leave the NotebookLM tab open; do not delete the generated audio from NotebookLM.
