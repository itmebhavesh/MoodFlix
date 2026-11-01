/* MoodFlix router + boot. Hash routes: #home #discover #mood #surprise #thriller #genie #taste
 * #library[-watchlist|-watched|-liked|-disliked|-hidden] #profile #login #signup */
(() => {
  "use strict";
  const { $ } = MF;
  const ROUTES = { home: MF.home, discover: MF.discover, mood: () => MF.mode("today_mood"), surprise: () => MF.mode("surprise_me"), thriller: MF.thriller,
    genie: MF.genieGuess, taste: MF.taste, profile: MF.profile, login: MF.login, signup: MF.signup };
  const SECTION = { home: "home", discover: "discover", mood: "discover", surprise: "discover", thriller: "discover", genie: "discover", taste: "taste", library: "library" };

  MF.route = () => {
    MF.nav++; MF.backFn = null; MF.inSearch = false; MF.sq = (MF.sq || 0) + 1;
    const raw = location.hash.slice(1) || "home", isLib = raw.startsWith("library"), name = isLib ? "library" : raw;
    document.querySelectorAll(".subnav a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + (SECTION[name] || "")));
    if (isLib) return MF.library(raw.split("-")[1] || "watchlist");
    (ROUTES[name] || ROUTES.home)();
  };
  window.addEventListener("hashchange", MF.route);

  // Search: submit = instant; typing = debounced live results.
  const form = $("searchForm"), box = $("q");
  let timer;
  form.addEventListener("submit", (e) => { e.preventDefault(); clearTimeout(timer); const q = box.value.trim(); if (q) { MF.inSearch = true; MF.search(q); } });
  box.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => { const q = box.value.trim(); if (q.length >= 2) { MF.inSearch = true; MF.search(q); } else if (!q && MF.inSearch) MF.route(); }, 350);
  });

  MF.loadCatalog().catch(() => {});          // warm the 870-movie catalog
  MF.refreshUser().finally(MF.route);        // restore session cookie, then render
})();
