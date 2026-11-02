/* The Tone at the Top: persistent audio briefing player.
 * One bar fixed to the bottom of every page. static/nav.js swaps page content in place, so this element (and the
 * <audio> inside it) is never reloaded: playback continues while you move between Today, Storylines, Archive and the rest.
 * Remembers speed and position per episode (this browser only) and supports lock-screen controls (Media Session).
 */
(function () {
  "use strict";
  var bar = document.getElementById("player");
  if (!bar || bar.dataset.ready) return;
  bar.dataset.ready = "1";
  var KEY = "tatt-pod";
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } }
  function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* storage unavailable */ } }
  function clock(t) { t = Math.max(0, Math.floor(t || 0)); return Math.floor(t / 60) + ":" + ("0" + (t % 60)).slice(-2); }
  var SPEEDS = [1, 1.25, 1.5, 1.75, 2];

  var audio = bar.querySelector("audio");
  var play = bar.querySelector(".pl-play"), icon = play.querySelector(".ms");
  var seek = bar.querySelector(".pl-seek"), cur = bar.querySelector(".pl-cur"), dur = bar.querySelector(".pl-dur");
  var titleEl = bar.querySelector(".pl-title"), kicker = bar.querySelector(".pl-kicker");
  var speedBtn = bar.querySelector(".pl-speed"), notes = bar.querySelector(".pl-notes");
  // relative URLs would break once the page around the bar changes depth: make them absolute now
  audio.src = audio.src;
  notes.setAttribute("href", notes.href);

  var st = load(), ep = bar.dataset.ep, speed = st.speed || 1, resumeAt = 0;
  document.body.classList.add("has-player");

  function paint() {
    var max = +seek.max || 1;
    seek.style.setProperty("--p", (100 * seek.value / max).toFixed(2) + "%");
  }
  function setSpeed(v) { speed = v; audio.playbackRate = v; speedBtn.textContent = v + "×"; st = load(); st.speed = v; save(st); }
  function setPlaying(on) {
    bar.classList.toggle("is-playing", on);
    icon.textContent = on ? "pause" : "play_arrow";
    play.setAttribute("aria-label", (on ? "Pause " : "Play ") + titleEl.textContent);
    document.querySelectorAll("[data-play-ep]").forEach(function (b) {
      var mine = b.dataset.playEp === ep && on;
      b.classList.toggle("is-playing", mine);
      var i = b.querySelector(".ms"); if (i) i.textContent = mine ? "pause" : "play_arrow";
    });
  }
  function restore() {
    st = load();
    resumeAt = (st.pos && st.pos[ep]) || 0;
    seek.max = +bar.dataset.seconds || 1;
    seek.value = resumeAt; cur.textContent = clock(resumeAt); dur.textContent = clock(+bar.dataset.seconds);
    paint();
  }
  setSpeed(speed);
  restore();

  function loadEpisode(o, autoplay) {
    if (o.ep === ep) { if (autoplay) toggle(); return; }
    audio.pause();
    ep = bar.dataset.ep = o.ep;
    bar.dataset.seconds = o.seconds || 0;
    audio.src = new URL(o.src, location.href).href;
    titleEl.textContent = o.title;
    kicker.textContent = "Audio briefing · " + Math.max(1, Math.round((o.seconds || 0) / 60)) + " min";
    notes.setAttribute("href", new URL(o.notes || notes.href, location.href).href);
    restore();
    if (autoplay) toggle();
  }
  function toggle() {
    if (audio.paused) {
      if (resumeAt && !audio.currentTime) {
        audio.addEventListener("loadedmetadata", function once() { audio.removeEventListener("loadedmetadata", once); audio.currentTime = resumeAt; });
      }
      audio.playbackRate = speed;
      var p = audio.play(); if (p && p.catch) p.catch(function () { setPlaying(false); });
    } else audio.pause();
  }
  play.addEventListener("click", toggle);
  audio.addEventListener("play", function () { setPlaying(true); audio.playbackRate = speed; });
  audio.addEventListener("pause", function () { setPlaying(false); });
  audio.addEventListener("loadedmetadata", function () { if (audio.duration) { seek.max = Math.round(audio.duration); dur.textContent = clock(audio.duration); } });
  var lastSave = 0;
  audio.addEventListener("timeupdate", function () {
    if (document.activeElement !== seek) { seek.value = Math.floor(audio.currentTime); paint(); }
    cur.textContent = clock(audio.currentTime);
    if (Date.now() - lastSave > 4000) { st = load(); st.pos = st.pos || {}; st.pos[ep] = Math.floor(audio.currentTime); save(st); lastSave = Date.now(); }
  });
  audio.addEventListener("ended", function () { setPlaying(false); st = load(); if (st.pos) delete st.pos[ep]; save(st); resumeAt = 0; });
  seek.addEventListener("input", function () {
    paint(); cur.textContent = clock(seek.value);
    if (audio.readyState) audio.currentTime = +seek.value; else resumeAt = +seek.value;
  });
  bar.querySelectorAll(".pl-skip").forEach(function (b) {
    b.addEventListener("click", function () {
      var t = Math.min(Math.max((audio.currentTime || resumeAt) + +b.dataset.skip, 0), +seek.max);
      if (audio.readyState) audio.currentTime = t; else { resumeAt = t; seek.value = t; cur.textContent = clock(t); paint(); }
    });
  });
  speedBtn.addEventListener("click", function () { setSpeed(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length]); });

  // "Play" buttons on the Audio briefings page load that episode into this bar
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-play-ep]");
    if (!b) return;
    e.preventDefault();
    loadEpisode({ ep: b.dataset.playEp, src: b.dataset.playSrc, title: b.dataset.playTitle,
                  seconds: +b.dataset.playSeconds, notes: b.dataset.playNotes }, true);
  });
  // after an in-place navigation, sync the new page's play buttons with what is playing
  document.addEventListener("tatt:navigate", function () { setPlaying(!audio.paused); });

  if ("mediaSession" in navigator) {
    audio.addEventListener("play", function () {
      navigator.mediaSession.metadata = new MediaMetadata({ title: titleEl.textContent, artist: "The Tone at the Top", album: "Audio briefings" });
      navigator.mediaSession.setActionHandler("seekbackward", function () { audio.currentTime = Math.max(audio.currentTime - 10, 0); });
      navigator.mediaSession.setActionHandler("seekforward", function () { audio.currentTime = Math.min(audio.currentTime + 30, audio.duration || 1e9); });
    });
  }
})();
