/* The Tone at the Top: reader interactions.
 * - Faceted filters (action, region, topic, story type, source) with live counts, applied chips, URL state
 * - Group by priority / topic / region; Cards or List view (remembered)
 * - Read state and Saved stories, kept in this browser only (localStorage)
 * - Keyboard: / search, j/k move, s save, Esc close
 */
(function () {
  "use strict";
  var LS = {
    get: function (k, d) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } }
  };
  var saved = LS.get("tatt-saved", {});
  var read = LS.get("tatt-read", {});

  // forget read marks older than 45 days
  var cutoff = Date.now() - 45 * 864e5;
  Object.keys(read).forEach(function (k) { if (read[k] < cutoff) delete read[k]; });
  LS.set("tatt-read", read);

  function updateSavedCount() {
    var n = Object.keys(saved).length;
    document.querySelectorAll(".saved-count").forEach(function (el) { el.textContent = n ? String(n) : ""; });
  }
  updateSavedCount();

  function cardInfo(card) {
    var a = card.querySelector(".stretch");
    var why = card.querySelector(".why");
    return {
      id: card.dataset.id, title: a.textContent.trim(), href: a.href, external: a.target === "_blank",
      source: (card.querySelector(".src") || {}).textContent || "", date: card.dataset.date || "",
      topic: (card.querySelector(".topic") || {}).textContent || "", action: card.dataset.action,
      actionLabel: card.dataset.actionLabel || "",
      why: why ? why.textContent.replace(/^\s*Why it matters\.?\s*/, "") : "",
      edition: card.dataset.edition, savedAt: Date.now()
    };
  }

  function setSaved(card, on) {
    var id = card.dataset.id, btn = card.querySelector(".save");
    if (on) saved[id] = cardInfo(card); else delete saved[id];
    LS.set("tatt-saved", saved);
    if (btn) btn.setAttribute("aria-pressed", on ? "true" : "false");
    card.classList.toggle("is-saved", on);
    updateSavedCount();
  }

  /* ------------------------------------------------------------ saved page */
  var savedList = document.getElementById("saved-list");
  if (savedList) {
    var renderSaved = function () {
      var items = Object.keys(saved).map(function (k) { return saved[k]; })
        .sort(function (a, b) { return b.savedAt - a.savedAt; });
      document.getElementById("saved-empty").hidden = items.length > 0;
      savedList.innerHTML = "";
      items.forEach(function (it) {
        var row = document.createElement("article");
        row.className = "saved-row act-" + (it.action || "fyi");
        var a = document.createElement("a");
        a.href = it.href; a.textContent = it.title; a.className = "saved-title";
        if (it.external) { a.target = "_blank"; a.rel = "noopener"; }
        var meta = document.createElement("div");
        meta.className = "saved-meta";
        meta.textContent = [it.actionLabel, it.topic, it.source, it.date, "edition " + it.edition].filter(Boolean).join(" · ");
        var why = document.createElement("p");
        why.className = "saved-why"; why.textContent = it.why;
        var rm = document.createElement("button");
        rm.type = "button"; rm.className = "linkish"; rm.textContent = "Remove";
        rm.addEventListener("click", function () { delete saved[it.id]; LS.set("tatt-saved", saved); updateSavedCount(); renderSaved(); });
        row.appendChild(a); row.appendChild(meta); if (it.why) row.appendChild(why); row.appendChild(rm);
        savedList.appendChild(row);
      });
    };
    renderSaved();
    return;
  }

  /* ------------------------------------------------------------ edition page */
  var feed = document.getElementById("feed");
  if (!feed) return;
  var allCards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  var lead = document.querySelector(".card-lead");
  var feedCards = allCards.filter(function (c) { return c !== lead; });
  var FACETS = ["action", "region", "topic", "type", "tier"];
  var GROUPS = {
    priority: { attr: "action", order: ["required", "monitor", "fyi"],
      title: { required: "Act now", monitor: "Watch", fyi: "Good to know" } },
    topic: { attr: "topic", order: [], title: {} },
    region: { attr: "region", order: ["US", "CA", "EU"], title: { US: "United States", CA: "Canada", EU: "European Union" } }
  };
  document.querySelectorAll('[data-facet="topic"] input').forEach(function (i) {
    GROUPS.topic.order.push(i.value); GROUPS.topic.title[i.value] = i.parentNode.querySelector(".opt-l").textContent;
  });
  var facetLabel = {};
  document.querySelectorAll(".facet").forEach(function (f) {
    f.querySelectorAll("input").forEach(function (i) { facetLabel[f.dataset.facet + ":" + i.value] = i.parentNode.querySelector(".opt-l").textContent; });
  });

  var state = { f: {}, q: "", group: "priority", view: LS.get("tatt-view", "cards"), hideRead: LS.get("tatt-hideread", false) };
  FACETS.forEach(function (k) { state.f[k] = []; });

  // URL hash -> state (ignore plain #c-id anchors)
  (function readHash() {
    var h = location.hash.slice(1);
    if (!h || /^c-/.test(h)) return;
    h.split("&").forEach(function (p) {
      var kv = p.split("="), k = decodeURIComponent(kv[0]), v = decodeURIComponent(kv[1] || "");
      if (FACETS.indexOf(k) >= 0 && v) state.f[k] = v.split(",");
      else if (k === "q") state.q = v;
      else if (k === "group" && GROUPS[v]) state.group = v;
      else if (k === "view" && (v === "cards" || v === "compact")) state.view = v;
    });
  })();

  function writeHash() {
    var parts = [];
    FACETS.forEach(function (k) { if (state.f[k].length) parts.push(k + "=" + state.f[k].map(encodeURIComponent).join(",")); });
    if (state.q) parts.push("q=" + encodeURIComponent(state.q));
    if (state.group !== "priority") parts.push("group=" + state.group);
    var h = parts.length ? "#" + parts.join("&") : " ";
    history.replaceState(null, "", h === " " ? location.pathname + location.search : h);
  }

  function matches(card, except) {
    for (var i = 0; i < FACETS.length; i++) {
      var k = FACETS[i];
      if (k === except || !state.f[k].length) continue;
      if (state.f[k].indexOf(card.dataset[k]) < 0) return false;
    }
    if (state.q && card.dataset.text.indexOf(state.q) < 0) return false;
    if (state.hideRead && read[card.dataset.id]) return false;
    return true;
  }

  var WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"];
  function num(n) { return n < WORDS.length ? WORDS[n] : String(n); }
  function groupDek(key, n) {
    var s = n === 1;
    if (state.group === "priority") {
      if (key === "required") return num(n) + (s ? " story that likely needs" : " stories that likely need") + " a decision, a policy check or a word with leadership.";
      if (key === "monitor") return num(n) + (s ? " development" : " developments") + " to track. No action yet, but " + (s ? "it could become one." : "any could become one.");
      return num(n) + (s ? " item" : " items") + " for context and background.";
    }
    return num(n) + (s ? " story." : " stories.");
  }

  function regroup() {
    var g = GROUPS[state.group];
    feed.innerHTML = "";
    g.order.forEach(function (key) {
      var members = feedCards.filter(function (c) { return c.dataset[g.attr] === key; });
      if (!members.length) return;
      var sec = document.createElement("section");
      sec.className = "group"; sec.dataset.group = key;
      sec.innerHTML = '<header class="group-head"><h2 class="group-h"></h2><p class="group-dek"></p></header><div class="grid"></div>';
      sec.querySelector(".group-h").textContent = g.title[key] || key;
      var grid = sec.querySelector(".grid");
      members.forEach(function (c) { grid.appendChild(c); });
      feed.appendChild(sec);
    });
  }

  function renderApplied(visible) {
    var box = document.querySelector(".applied");
    box.innerHTML = "";
    var any = false;
    FACETS.forEach(function (k) {
      state.f[k].forEach(function (v) {
        any = true;
        var b = document.createElement("button");
        b.type = "button"; b.className = "chip-x";
        b.setAttribute("aria-label", "Remove filter " + facetLabel[k + ":" + v]);
        b.innerHTML = '<span class="ms" aria-hidden="true">check</span>';
        b.appendChild(document.createTextNode(facetLabel[k + ":" + v]));
        var x = document.createElement("span"); x.className = "ms"; x.setAttribute("aria-hidden", "true"); x.textContent = "close"; b.appendChild(x);
        b.addEventListener("click", function () { state.f[k] = state.f[k].filter(function (x) { return x !== v; }); apply(); });
        box.appendChild(b);
      });
    });
    if (state.q) {
      any = true;
      var qb = document.createElement("button");
      qb.type = "button"; qb.className = "chip-x"; qb.textContent = "“" + state.q + "” ×";
      qb.addEventListener("click", function () { state.q = ""; search.value = ""; apply(); });
      box.appendChild(qb);
    }
    var count = document.createElement("span");
    count.className = "result-n";
    count.textContent = any || state.hideRead ? "Showing " + visible + " of " + allCards.length : allCards.length + " stories";
    box.insertBefore(count, box.firstChild);
    if (any) {
      var clr = document.createElement("button");
      clr.type = "button"; clr.className = "linkish clear-all"; clr.textContent = "Clear all";
      clr.addEventListener("click", clearAll);
      box.appendChild(clr);
    }
  }

  function apply() {
    var visible = 0;
    allCards.forEach(function (c) {
      var ok = matches(c);
      c.hidden = !ok; if (ok) visible++;
      c.classList.toggle("is-read", !!read[c.dataset.id]);
      var on = !!saved[c.dataset.id];
      c.classList.toggle("is-saved", on);
      var sb = c.querySelector(".save"); if (sb) sb.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (lead) lead.parentNode.hidden = lead.hidden;
    // facet counts (each facet counted against the other active filters)
    document.querySelectorAll(".facet").forEach(function (f) {
      var k = f.dataset.facet, sel = state.f[k];
      f.querySelectorAll("label").forEach(function (lab) {
        var inp = lab.querySelector("input");
        var n = allCards.filter(function (c) { return c.dataset[k] === inp.value && matches(c, k); }).length;
        inp.checked = sel.indexOf(inp.value) >= 0;
        lab.querySelector(".opt-n").textContent = n;
        inp.disabled = n === 0 && !inp.checked;
        lab.classList.toggle("is-disabled", inp.disabled);
      });
      f.querySelector(".facet-n").textContent = sel.length ? " · " + sel.length : "";
      f.classList.toggle("is-active", sel.length > 0);
    });
    feed.querySelectorAll(".group").forEach(function (sec) {
      var n = sec.querySelectorAll(".card:not([hidden])").length;
      sec.hidden = n === 0;
      sec.querySelector(".group-dek").textContent = groupDek(sec.dataset.group, n);
    });
    document.querySelector(".empty").hidden = visible !== 0;
    document.body.classList.toggle("view-compact", state.view === "compact");
    document.body.dataset.group = state.group;   // lets CSS drop labels the section heading already states
    document.querySelectorAll(".seg button").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.view === state.view ? "true" : "false"); });
    groupSel.value = state.group;
    hideRead.checked = state.hideRead;
    renderApplied(visible);
    markLastRows();
    writeHash();
  }

  // no divider under the final row of each section (the row count depends on screen width)
  function markLastRows() {
    feed.querySelectorAll(".grid").forEach(function (g) {
      var cards = Array.prototype.filter.call(g.children, function (c) { return !c.hidden; });
      var maxTop = Math.max.apply(null, cards.map(function (c) { return c.offsetTop; }).concat([-1]));
      Array.prototype.forEach.call(g.children, function (c) { c.classList.toggle("last-row", !c.hidden && c.offsetTop === maxTop); });
    });
  }
  var rz; window.addEventListener("resize", function () { clearTimeout(rz); rz = setTimeout(markLastRows, 150); });
  window.addEventListener("load", markLastRows);

  function clearAll() {
    FACETS.forEach(function (k) { state.f[k] = []; });
    state.q = ""; search.value = ""; apply();
  }

  /* ---- controls ---- */
  var search = document.querySelector(".search");
  var groupSel = document.querySelector(".group-by");
  var hideRead = document.querySelector(".hide-read");
  search.value = state.q;
  var t;
  search.addEventListener("input", function () {
    clearTimeout(t);
    t = setTimeout(function () { state.q = search.value.trim().toLowerCase(); apply(); }, 120);
  });
  groupSel.addEventListener("change", function () { state.group = groupSel.value; regroup(); apply(); });
  hideRead.addEventListener("change", function () { state.hideRead = hideRead.checked; LS.set("tatt-hideread", state.hideRead); apply(); });
  document.querySelectorAll(".seg button").forEach(function (b) {
    b.addEventListener("click", function () { state.view = b.dataset.view; LS.set("tatt-view", state.view); apply(); });
  });
  document.querySelectorAll(".clear-all").forEach(function (b) { b.addEventListener("click", clearAll); });
  var topBtn = document.querySelector(".dock-top");
  if (topBtn) topBtn.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: smoothOK() ? "smooth" : "auto" }); });
  // the app bar gains a stronger glass once content scrolls beneath it
  var appbar = document.querySelector(".appbar");
  var onScroll = function () { if (appbar) appbar.classList.toggle("scrolled", window.scrollY > 8); };
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();

  // facet popovers
  function closePanels(except) {
    document.querySelectorAll(".facet").forEach(function (f) {
      if (f === except) return;
      f.querySelector(".facet-panel").hidden = true;
      f.querySelector(".facet-btn").setAttribute("aria-expanded", "false");
    });
  }
  document.querySelectorAll(".facet").forEach(function (f) {
    var btn = f.querySelector(".facet-btn"), panel = f.querySelector(".facet-panel");
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = panel.hidden;
      closePanels(f);
      panel.hidden = !open;
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    panel.addEventListener("click", function (e) { e.stopPropagation(); });
    panel.querySelectorAll("input").forEach(function (inp) {
      inp.addEventListener("change", function () {
        var k = f.dataset.facet;
        state.f[k] = state.f[k].filter(function (x) { return x !== inp.value; });
        if (inp.checked) state.f[k].push(inp.value);
        apply();
      });
    });
  });
  document.addEventListener("click", function () { closePanels(); });

  // quick filters from the Morning brief counts
  document.querySelectorAll("[data-quick]").forEach(function (b) {
    b.addEventListener("click", function () {
      var kv = b.dataset.quick.split(":");
      var already = state.f[kv[0]].length === 1 && state.f[kv[0]][0] === kv[1];
      state.f[kv[0]] = already ? [] : [kv[1]];
      apply();
      document.querySelector(".toolbar").scrollIntoView({ behavior: smoothOK() ? "smooth" : "auto" });
    });
  });

  function smoothOK() { return !window.matchMedia("(prefers-reduced-motion: reduce)").matches; }

  // Morning brief bullets jump to their story
  document.querySelectorAll("[data-jump]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      var card = document.getElementById("c-" + a.dataset.jump);
      if (!card) return;
      if (card.hidden) clearAll();
      card.scrollIntoView({ behavior: smoothOK() ? "smooth" : "auto", block: "center" });
      card.classList.add("flash");
      setTimeout(function () { card.classList.remove("flash"); }, 1600);
      card.querySelector(".stretch").focus({ preventScroll: true });
    });
  });

  // read + save
  allCards.forEach(function (c) {
    var link = c.querySelector(".stretch");
    var markRead = function () { read[c.dataset.id] = Date.now(); LS.set("tatt-read", read); c.classList.add("is-read"); };
    link.addEventListener("click", markRead);
    link.addEventListener("auxclick", markRead);
    c.querySelector(".save").addEventListener("click", function (e) {
      e.preventDefault(); e.stopPropagation();
      setSaved(c, !saved[c.dataset.id]);
    });
  });

  // keyboard
  function visibleCards() { return allCards.filter(function (c) { return !c.hidden && !(c === lead && lead.parentNode.hidden); }); }
  document.addEventListener("keydown", function (e) {
    var tag = (e.target.tagName || "").toLowerCase();
    if (e.key === "Escape") { closePanels(); if (tag === "input") e.target.blur(); return; }
    if (tag === "input" || tag === "select" || tag === "textarea" || e.metaKey || e.ctrlKey || e.altKey) return;
    var cards = visibleCards();
    var cur = document.activeElement && document.activeElement.closest ? document.activeElement.closest(".card") : null;
    var idx = cur ? cards.indexOf(cur) : -1;
    if (e.key === "/") { e.preventDefault(); search.focus(); }
    else if (e.key === "j" || e.key === "k") {
      e.preventDefault();
      var next = cards[Math.max(0, Math.min(cards.length - 1, idx + (e.key === "j" ? 1 : -1)))];
      if (next) { next.querySelector(".stretch").focus(); next.scrollIntoView({ block: "nearest", behavior: smoothOK() ? "smooth" : "auto" }); }
    } else if (e.key === "s" && cur) { e.preventDefault(); setSaved(cur, !saved[cur.dataset.id]); }
  });

  // relative times ("2 days ago"), with the full date kept as a tooltip
  var rtf = window.Intl && Intl.RelativeTimeFormat ? new Intl.RelativeTimeFormat("en", { numeric: "auto" }) : null;
  document.querySelectorAll("time.when[datetime]").forEach(function (t) {
    var iso = t.getAttribute("datetime"); if (!iso || !rtf) return;
    var d = new Date(iso); if (isNaN(d)) return;
    var hrs = Math.round((d - Date.now()) / 36e5);
    t.title = t.textContent;
    t.textContent = Math.abs(hrs) < 24 ? (hrs === 0 ? "just now" : rtf.format(hrs, "hour")) : rtf.format(Math.round(hrs / 24), "day");
  });
  // greeting that matches the reader's time of day
  var gw = document.querySelector(".greet-word");
  if (gw) { var h = new Date().getHours(); gw.textContent = h < 12 ? "Good morning." : h < 18 ? "Good afternoon." : "Good evening."; }

  if (state.group !== "priority") regroup();
  apply();
})();
