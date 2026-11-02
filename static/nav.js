/* The Tone at the Top: in-place navigation.
 * Clicking a link to another page of this site fetches that page and swaps only its content (.wrap), so the audio
 * player at the bottom keeps playing. Anything unusual (new tab, download, external site, failed request) falls back
 * to a normal page load. Back and forward buttons work as usual.
 */
(function () {
  "use strict";
  if (!window.fetch || !window.history || !history.pushState || !window.DOMParser) return;

  function target(a) {
    if (!a || !a.href || a.hasAttribute("download") || (a.target && a.target !== "_self")) return null;
    var u;
    try { u = new URL(a.href, location.href); } catch (e) { return null; }
    if (u.origin !== location.origin) return null;
    if (!/(\.html?|\/)$/.test(u.pathname)) return null;          // pages only (not audio, text or images)
    if (u.pathname === location.pathname && u.search === location.search && u.hash) return null;  // same-page anchors
    return u;
  }

  var pending = 0;
  var loaded = location.pathname + location.search;   // the page whose content is currently shown
  function go(url, push) {
    var ticket = ++pending;
    document.documentElement.classList.add("is-navigating");
    fetch(url, { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(function (html) {
        if (ticket !== pending) return;                 // a newer click won
        var doc = new DOMParser().parseFromString(html, "text/html");
        var next = doc.querySelector(".wrap"), cur = document.querySelector(".wrap");
        if (!next || !cur) throw new Error("layout");
        if (push) history.pushState({ tatt: 1 }, "", url);  // first, so relative links in the new content resolve correctly
        loaded = location.pathname + location.search;
        document.title = doc.title;
        document.body.classList.remove("view-compact");
        delete document.body.dataset.group;
        var fresh = document.importNode(next, true);
        cur.parentNode.replaceChild(fresh, cur);
        fresh.querySelectorAll("script").forEach(function (old) {   // page-specific inline scripts
          var s = document.createElement("script"); s.text = old.textContent; old.parentNode.replaceChild(s, old);
        });
        var hash = new URL(url, location.href).hash;
        var anchor = hash && document.getElementById(decodeURIComponent(hash.slice(1)));
        if (anchor) anchor.scrollIntoView(); else window.scrollTo(0, 0);
        try { if (window.tattInit) window.tattInit(); } catch (err) { if (window.console) console.error(err); }
        try { document.dispatchEvent(new Event("tatt:navigate")); } catch (err) { /* keep the page */ }
      })
      .catch(function () { location.href = url; })
      .then(function () { if (ticket === pending) document.documentElement.classList.remove("is-navigating"); });
  }

  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest && e.target.closest("a");
    var u = target(a);
    if (!u) return;
    e.preventDefault();
    if (u.href === location.href) return;
    go(u.href, true);
  });
  window.addEventListener("popstate", function () {
    if (location.pathname + location.search === loaded) return;   // only the #fragment changed
    go(location.href, false);
  });
  history.replaceState({ tatt: 1 }, "", location.href);
})();
