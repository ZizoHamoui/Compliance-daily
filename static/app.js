// Filters: region chips, topic chips (incl. AI Briefings), and free-text search. Choices are remembered per browser.
(function () {
  var state = { region: "all", topic: "all", q: "" };
  try { var saved = JSON.parse(localStorage.getItem("tatt-filters") || "{}"); state.region = saved.region || "all"; } catch (e) {}

  var cards = Array.prototype.slice.call(document.querySelectorAll("#grid .card"));
  var empty = document.querySelector(".empty");

  function apply() {
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (state.region === "all" || c.dataset.region === state.region) &&
        (state.topic === "all" || c.dataset.topic === state.topic || (state.topic === "briefing" && c.dataset.kind === "briefing")) &&
        (!state.q || c.dataset.text.indexOf(state.q) !== -1);
      c.hidden = !ok; if (ok) shown++;
    });
    if (empty) empty.hidden = shown !== 0;
    document.querySelectorAll(".chips").forEach(function (g) {
      g.querySelectorAll(".chip").forEach(function (b) { b.classList.toggle("on", b.dataset.v === state[g.dataset.group]); });
    });
    try { localStorage.setItem("tatt-filters", JSON.stringify({ region: state.region })); } catch (e) {}
  }

  document.querySelectorAll(".chips").forEach(function (g) {
    g.addEventListener("click", function (ev) {
      var b = ev.target.closest(".chip"); if (!b) return;
      state[g.dataset.group] = b.dataset.v; apply();
    });
  });
  var s = document.querySelector(".search");
  if (s) s.addEventListener("input", function () { state.q = s.value.trim().toLowerCase(); apply(); });
  if (!document.querySelector('.chips[data-group="region"] .chip[data-v="' + state.region + '"]')) state.region = "all";
  apply();
})();
