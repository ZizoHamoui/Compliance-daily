/* The Tone at the Top: weekly podcast player.
 * Progressive enhancement over a plain <audio controls>: play/pause, seek, skip, speed,
 * resume where you left off (this browser only) and lock-screen controls via Media Session.
 */
(function () {
  "use strict";
  var KEY = "tatt-pod";
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } }
  function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* storage unavailable */ } }
  function clock(t) { t = Math.max(0, Math.floor(t || 0)); return Math.floor(t / 60) + ":" + ("0" + (t % 60)).slice(-2); }
  var SPEEDS = [1, 1.25, 1.5, 1.75, 2];

  document.querySelectorAll(".listen").forEach(function (box) {
    var audio = box.querySelector(".listen-audio");
    var play = box.querySelector(".listen-play"), icon = play.querySelector(".ms");
    var seek = box.querySelector(".listen-seek"), cur = box.querySelector(".listen-cur");
    var speedBtn = box.querySelector(".listen-speed");
    var ep = box.dataset.ep, st = load();
    audio.removeAttribute("controls");
    audio.hidden = true;
    box.querySelectorAll("[hidden]").forEach(function (el) { if (el !== audio) el.hidden = false; });
    box.classList.add("is-enhanced");

    var speed = st.speed || 1;
    function setSpeed(v) { speed = v; audio.playbackRate = v; speedBtn.textContent = (v % 1 ? v : v + "") + "×"; st.speed = v; save(st); }
    setSpeed(speed);
    var resumeAt = (st.pos && st.pos[ep]) || 0;
    if (resumeAt > 5) { seek.value = resumeAt; cur.textContent = clock(resumeAt); box.classList.add("is-resume"); }

    function paint() {
      var max = +seek.max || audio.duration || 1;
      seek.style.setProperty("--p", (100 * seek.value / max).toFixed(2) + "%");
    }
    paint();
    function setPlaying(on) {
      box.classList.toggle("is-playing", on);
      icon.textContent = on ? "pause" : "play_arrow";
      play.setAttribute("aria-label", (on ? "Pause " : "Play ") + box.dataset.title);
    }
    play.addEventListener("click", function () {
      if (audio.paused) {
        if (resumeAt && !audio.currentTime) {
          audio.addEventListener("loadedmetadata", function once() { audio.removeEventListener("loadedmetadata", once); audio.currentTime = resumeAt; });
        }
        audio.playbackRate = speed;
        audio.play();
      } else audio.pause();
    });
    audio.addEventListener("play", function () { setPlaying(true); audio.playbackRate = speed; });
    audio.addEventListener("pause", function () { setPlaying(false); });
    audio.addEventListener("loadedmetadata", function () { if (audio.duration) seek.max = Math.round(audio.duration); });
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
    box.querySelectorAll(".listen-skip").forEach(function (b) {
      b.addEventListener("click", function () {
        var t = Math.min(Math.max((audio.currentTime || resumeAt) + +b.dataset.skip, 0), +seek.max);
        if (audio.readyState) audio.currentTime = t; else { resumeAt = t; seek.value = t; cur.textContent = clock(t); paint(); }
      });
    });
    speedBtn.addEventListener("click", function () { setSpeed(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length]); });

    if ("mediaSession" in navigator) {
      audio.addEventListener("play", function () {
        navigator.mediaSession.metadata = new MediaMetadata({ title: box.dataset.title, artist: "The Tone at the Top", album: "The weekly briefing" });
        navigator.mediaSession.setActionHandler("seekbackward", function () { audio.currentTime = Math.max(audio.currentTime - 10, 0); });
        navigator.mediaSession.setActionHandler("seekforward", function () { audio.currentTime = Math.min(audio.currentTime + 30, audio.duration || 1e9); });
      });
    }
  });
})();
