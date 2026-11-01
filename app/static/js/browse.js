/* MoodFlix browse views. Backend: /api/movies/catalog, /api/library, /api/profile*, /api/history/*, /api/auth/* */
(() => {
  "use strict";
  const { h, $, title } = MF;
  const PAGE = 48;
  const rank = (a, b) => (b.rating || 0) - (a.rating || 0) || b.votes - a.votes;
  const countBy = (list, pick) => { const c = new Map(); list.forEach((m) => pick(m).forEach((k) => c.set(k, (c.get(k) || 0) + 1))); return [...c.entries()].sort((a, b) => b[1] - a[1]); };
  const today = () => new Date().toISOString().slice(0, 10);

  MF.openTitle = (m) => {
    const back = MF.backFn || MF.route;
    MF.nav++;
    MF.render(MF.wide(h("button", { class: "link", type: "button", onclick: back, style: "padding-left:0" }, "← Back"), h("div", { class: "movie-wrap" }, MF.detail(MF.norm(m), { big: true }))));
  };

  const row = (t, list, sub) => h("section", { class: "sec" }, h("h2", { class: "bar-title" }, t, sub ? h("small", null, sub) : null), h("div", { class: "scroll" }, list.map((m) => MF.card(m))));

  function hero(list) {
    let i = 0;
    const box = h("section", { class: "hero", "aria-label": "Featured" });
    const draw = () => {
      const m = list[i], ups = list.filter((_, k) => k !== i).slice(0, 3);
      box.replaceChildren(
        h("div", { class: "hero-main", style: `--h:${MF.hue(m.title)}` }, MF.poster(m),
          h("div", { class: "hero-txt" }, h("div", { class: "kicker" }, "TOP RATED · FEATURED"), h("h2", null, m.title), h("p", { class: "meta" }, MF.metaLine(m)),
            h("div", { class: "badges" }, h("span", { class: "badge imdb" }, `★ ${m.rating.toFixed(1)}`), m.genres.slice(0, 3).map((g) => h("span", { class: "badge" }, g))),
            m.plot ? h("p", { class: "plot" }, m.plot) : null,
            h("div", { class: "center", style: "justify-content:flex-start;margin-top:12px" }, h("button", { class: "btn primary", onclick: () => { MF.backFn = null; MF.openTitle(m); } }, "View details"),
              MF.stateBtn(m, "watchlist", "btn", { off: "+ Watchlist", on: "✓ In Watchlist" })))),
        h("aside", { class: "upnext" }, h("div", { class: "bar-title" }, "Up next"),
          ups.map((u) => h("button", { class: "up", type: "button", onclick: () => { i = list.indexOf(u); draw(); } }, MF.poster(u), h("div", null, MF.star(u), h("b", null, u.title), h("small", null, u.year))))));
    };
    draw();
    return box;
  }

  const discoverBand = () => h("section", { class: "band" }, h("div", { class: "orb", "aria-hidden": "true" }, h("i")),
    h("div", null, h("h3", null, "Samajh nahi aa raha kya dekhein?"), h("p", null, "Today’s Mood, Surprise Me ya Thriller Quiz: Genie sawaal poochhega aur movie suggest karega.")),
    h("a", { class: "btn primary", href: "#discover", style: "text-decoration:none" }, "Find my movie →"));

  /* Grid with filters + load-more over the whole catalog */
  function browseAll(all) {
    const genres = countBy(all, (m) => m.genres).map((x) => x[0]).sort(), langs = countBy(all, (m) => m.languages).slice(0, 14).map((x) => x[0]);
    let g = "", l = "", s = "rating", shown = PAGE;
    const grid = h("div", { class: "grid" }), count = h("small", null), more = h("button", { class: "btn", type: "button", onclick: () => { shown += PAGE; paint(); } }, "Load more");
    const sel = (label, opts, set) => h("label", { class: "flt" }, label, h("select", { onchange: (e) => { set(e.target.value); shown = PAGE; paint(); } }, opts.map(([v, t]) => h("option", { value: v }, t))));
    const paint = () => {
      let r = all.filter((m) => (!g || m.genres.includes(g)) && (!l || m.languages.includes(l)));
      r = r.sort(s === "rating" ? rank : s === "new" ? (a, b) => (b.year || 0) - (a.year || 0) : s === "old" ? (a, b) => (a.year || 9999) - (b.year || 9999) : (a, b) => a.title.localeCompare(b.title));
      count.textContent = `${r.length} movies`;
      grid.replaceChildren(...(r.length ? r.slice(0, shown).map((m) => MF.card(m)) : [MF.notice("Is filter mein koi movie nahi mili. Filters badal ke dekho.")]));
      more.hidden = shown >= r.length;
    };
    paint();
    return h("section", { class: "sec", id: "all" }, h("h2", { class: "bar-title" }, "Browse all movies", count),
      h("div", { class: "filters" }, sel("Genre", [["", "All genres"], ...genres.map((x) => [x, x])], (v) => (g = v)), sel("Language", [["", "All languages"], ...langs.map((x) => [x, x])], (v) => (l = v)),
        sel("Sort", [["rating", "Top rated"], ["new", "Newest"], ["old", "Oldest"], ["az", "A–Z"]], (v) => (s = v))), grid, h("div", { class: "center" }, more));
  }

  MF.home = async () => {
    const t = MF.nav; MF.backFn = null;
    MF.render(MF.wide(h("div", { class: "hero skel-hero", "aria-busy": "true" }), MF.skelRow(), MF.skelRow()));
    let cat; try { cat = await MF.loadCatalog(); } catch (e) { if (t === MF.nav) MF.errorView(e, MF.route); return; }
    if (t !== MF.nav) return;
    if (!cat.length) return MF.render(MF.wide(MF.notice("Catalog khaali hai. Backend ka instance/movies_omdb_10000.csv check karo.")));
    const vis = cat.filter((m) => !MF.isHidden(m));
    const voted = vis.filter((m) => m.votes >= 5000), ranked = (voted.length >= 12 ? voted : vis).filter((m) => m.rating).sort(rank);
    const heroes = ranked.filter((m) => m.poster).slice(0, 4);
    const rows = [["Top rated", ranked.slice(0, 20), `${cat.length} movies catalog`]];
    const hindi = vis.filter((m) => m.languages.includes("Hindi") && m.rating).sort(rank); if (hindi.length >= 4) rows.push(["🇮🇳 Hindi picks", hindi.slice(0, 20)]);
    countBy(vis, (m) => m.genres).slice(0, 5).forEach(([gname]) => rows.push([gname, vis.filter((m) => m.genres.includes(gname) && m.rating).sort(rank).slice(0, 20)]));
    MF.render(MF.wide(heroes.length ? hero(heroes) : null, discoverBand(), rows.map((r) => row(...r)), browseAll(vis)));
  };

  /* ---------- search (whole catalog) ---------- */
  MF.search = async (q) => {
    const tok = (MF.sq = (MF.sq || 0) + 1); MF.nav++; MF.backFn = () => MF.search(q);
    document.querySelectorAll(".subnav a").forEach((a) => a.classList.remove("on"));
    MF.render(MF.wide(h("h2", { class: "bar-title" }, `Searching “${q}”…`), MF.skelRow()));
    let cat; try { cat = await MF.loadCatalog(); } catch (e) { if (tok === MF.sq) MF.errorView(e, () => MF.search(q)); return; }
    if (tok !== MF.sq) return;
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean), ql = q.toLowerCase();
    const hits = cat.filter((m) => terms.every((w) => m._h.includes(w))).map((m) => [m, (m.title.toLowerCase() === ql ? 10 : m.title.toLowerCase().startsWith(ql) ? 6 : m.title.toLowerCase().includes(ql) ? 4 : 0) + (m.genres.some((x) => x.toLowerCase() === ql) ? 2 : 0)])
      .sort((a, b) => b[1] - a[1] || rank(a[0], b[0])).map((x) => x[0]);
    let shown = PAGE;
    const grid = h("div", { class: "grid" }), more = h("button", { class: "btn", type: "button", onclick: () => { shown += PAGE; paint(); } }, "Load more");
    const paint = () => { grid.replaceChildren(...hits.slice(0, shown).map((m) => MF.card(m))); more.hidden = shown >= hits.length; }; paint();
    MF.render(MF.wide(h("h2", { class: "bar-title" }, `Results for “${q}”`, h("small", null, `${hits.length} found`)),
      hits.length ? [grid, h("div", { class: "center" }, more)] : [MF.notice("Koi movie nahi mili. Title, genre, actor, director ya language try karo (jaise “thriller”, “Hindi”, “Nolan”)."),
        h("div", { class: "center" }, h("a", { class: "btn primary", href: "#home", style: "text-decoration:none" }, "Back to home"))]));
  };

  /* ---------- library ---------- */
  const TABS = [["watchlist", "Watchlist", "🔖"], ["watched", "Watched", "👁"], ["liked", "Liked", "👍"], ["disliked", "Disliked", "👎"], ["hidden", "Hidden", "🚫"]];
  MF.library = async (tab) => {
    if (!MF.requireLogin("My Library dekhne ke liye login karo")) return;
    const t = MF.nav; tab = TABS.some((x) => x[0] === tab) ? tab : "watchlist";
    MF.backFn = () => MF.library(tab);
    MF.render(MF.wide(h("h2", { class: "bar-title" }, "My Library"), MF.skelRow()));
    await Promise.all([MF.loadLib(), MF.loadCatalog().catch(() => {})]);
    if (t !== MF.nav) return;
    if (!MF.user) return;
    const run = async (fn) => { try { await fn(); await MF.loadLib(); MF.library(tab); } catch (e) { MF.fail(e); } };
    const items = MF.lib.filter((r) => r.status === tab);
    const cardFor = (r) => {
      const m = MF.byKey.get(r.movie_key) || MF.norm({ title: r.title, year: r.release_year }), extra = [h("small", { class: "cgen" }, `Added ${String(r.created_at || "").slice(0, 10)}${r.watched_at ? ` · watched ${r.watched_at}` : ""}`)];
      if (tab === "watchlist") extra.push(h("button", { class: "wbtn", type: "button", onclick: () => run(() => MF.api("POST", "/api/library", { movie: MF.payload(m), status: "watched", watched_at: today() })) }, "👁 Mark watched"));
      extra.push(h("button", { class: "wbtn rm", type: "button", onclick: () => run(() => MF.api("DELETE", `/api/library/${r.id}`)) }, tab === "hidden" || tab === "disliked" ? "Undo / remove" : "Remove"));
      return MF.card(m, { extra });
    };
    MF.render(MF.wide(h("h2", { class: "bar-title" }, "My Library"),
      h("nav", { class: "tabs", "aria-label": "Library sections" }, TABS.map(([k, label, em]) => h("a", { href: `#library-${k}`, class: k === tab ? "on" : "" }, `${em} ${label} `, h("b", null, MF.lib.filter((r) => r.status === k).length)))),
      items.length ? h("div", { class: "grid" }, items.map(cardFor)) : [MF.notice(`${TABS.find((x) => x[0] === tab)[1]} abhi khaali hai. Kisi movie pe action dabao, yahan dikhegi.`),
        h("div", { class: "center" }, h("a", { class: "btn primary", href: "#home", style: "text-decoration:none" }, "Browse movies"))]));
  };

  /* ---------- auth ---------- */
  const field = (label, props) => h("label", { class: "fld" }, label, h("input", props));
  function authView(kind) {
    const signup = kind === "signup";
    if (MF.user) { location.hash = "#profile"; return; }
    const msg = h("p", { class: "err", role: "alert" }), btn = h("button", { class: "btn primary wide", type: "submit" }, signup ? "Create account" : "Log in");
    const f = h("form", { class: "authform", novalidate: true, onsubmit: async (e) => {
      e.preventDefault(); msg.textContent = "";
      const d = Object.fromEntries(new FormData(f));
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.email || "")) return (msg.textContent = "Sahi email address daalo.");
      if (!d.password || (signup && d.password.length < 8)) return (msg.textContent = signup ? "Password kam se kam 8 characters ka hona chahiye." : "Password daalo.");
      btn.disabled = true; btn.textContent = "Please wait…";
      try {
        const r = await MF.api("POST", `/api/auth/${signup ? "signup" : "login"}`, signup ? { email: d.email, password: d.password, display_name: d.display_name } : { email: d.email, password: d.password });
        MF.user = r.user; await MF.loadLib(); MF.toast(signup ? `Welcome, ${r.user.display_name}! 🎬` : `Welcome back, ${r.user.display_name} 👋`);
        const n = MF.next && !/^#(login|signup)$/.test(MF.next) ? MF.next : "#home"; MF.next = "#home";
        if (location.hash === n) MF.route(); else location.hash = n;
      } catch (err) { msg.textContent = err.message; btn.disabled = false; btn.textContent = signup ? "Create account" : "Log in"; }
    } },
      signup ? field("Name (optional)", { name: "display_name", type: "text", autocomplete: "name", maxlength: 80 }) : null,
      field("Email", { name: "email", type: "email", required: true, autocomplete: "email" }),
      field("Password", { name: "password", type: "password", required: true, autocomplete: signup ? "new-password" : "current-password", minlength: signup ? 8 : null }),
      signup ? h("small", { class: "hint" }, "Kam se kam 8 characters.") : null, msg, btn);
    MF.render(MF.narrow(MF.genie("", signup ? "Account banao, taste save karenge 🎬" : "Wapas aaye! 🧞"), h("h2", { class: "q" }, signup ? "Create your account" : "Log in"),
      h("div", { class: "authcard" }, f, h("p", { class: "meta", style: "text-align:center" }, signup ? "Already have an account? " : "New here? ", h("a", { href: signup ? "#login" : "#signup" }, signup ? "Log in" : "Sign up")))));
  }
  MF.login = () => authView("login");
  MF.signup = () => authView("signup");

  /* ---------- profile ---------- */
  function tagInput(values, suggestions, listId, placeholder) {
    let vals = [...values];
    const box = h("div", { class: "tags" }), input = h("input", { type: "text", list: listId, placeholder, autocomplete: "off" });
    const dl = h("datalist", { id: listId }, suggestions.map((s) => h("option", { value: s })));
    const paint = () => box.replaceChildren(...vals.map((v) => h("span", { class: "tag" }, v, h("button", { type: "button", "aria-label": `Remove ${v}`, onclick: () => { vals = vals.filter((x) => x !== v); paint(); } }, "×"))), input);
    const add = () => { const v = input.value.replace(/,$/, "").trim(); if (v && !vals.some((x) => x.toLowerCase() === v.toLowerCase())) vals.push(v); input.value = ""; paint(); input.focus(); };
    input.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); } else if (e.key === "Backspace" && !input.value && vals.length) { vals.pop(); paint(); input.focus(); } });
    input.addEventListener("change", add);
    paint();
    return { el: h("div", { class: "tagbox" }, box, dl), get: () => { if (input.value.trim()) add(); return vals; } };
  }
  MF.profile = async () => {
    if (!MF.requireLogin("Profile dekhne ke liye login karo")) return;
    const t = MF.nav; MF.backFn = null;
    MF.render(MF.narrow(h("h2", { class: "bar-title" }, "Your profile"), MF.notice("Loading…")));
    let d, cat = []; try { [d, cat] = await Promise.all([MF.api("GET", "/api/profile"), MF.loadCatalog().catch(() => [])]); } catch (e) { if (e.status === 401) { MF.user = null; MF.paintHeader(); MF.requireLogin(); return; } return MF.errorView(e, MF.profile); }
    if (t !== MF.nav) return;
    const p = d.profile, pr = d.preferences;
    const langSug = [...new Set(["Hindi", "English", "Malayalam", "Tamil", "Telugu", "Kannada", ...countBy(cat, (m) => m.languages).slice(0, 12).map((x) => x[0])])];
    const genSug = countBy(cat, (m) => m.genres).map((x) => x[0]);
    const T = { languages: tagInput(pr.languages, langSug, "dl-lang", "Add language, Enter"), genres: tagInput(pr.genres, genSug, "dl-gen", "Add genre, Enter"),
      favourite_movies: tagInput(pr.favourite_movies, cat.slice().sort(rank).slice(0, 300).map((m) => m.title), "dl-mov", "Add movie, Enter"), favourite_actors: tagInput(pr.favourite_actors, [...new Set(cat.flatMap((m) => m.actors))].slice(0, 400), "dl-act", "Add actor, Enter") };
    const name = h("input", { type: "text", value: p.display_name, maxlength: 80, required: true }), photo = h("input", { type: "url", value: p.photo_url || "", placeholder: "https://… (optional)" });
    const msg = h("p", { class: "err", role: "status" }), save = h("button", { class: "btn primary", type: "submit" }, "Save changes");
    const f = h("form", { class: "authform pf", onsubmit: async (e) => {
      e.preventDefault(); msg.textContent = ""; save.disabled = true; save.textContent = "Saving…";
      try {
        const body = { display_name: name.value.trim(), languages: T.languages.get(), genres: T.genres.get(), favourite_movies: T.favourite_movies.get(), favourite_actors: T.favourite_actors.get() };
        if (photo.value.trim()) body.photo_url = photo.value.trim();
        const r = await MF.api("PUT", "/api/profile", body); MF.user = { ...MF.user, ...r.profile }; MF.paintHeader(); MF.toast("Profile update ho gaya ✓"); msg.className = "ok"; msg.textContent = "Saved ✓ Ye preferences aage ki recommendations ko personalize karengi.";
      } catch (err) { msg.className = "err"; msg.textContent = err.message; if (err.status === 401) MF.fail(err); }
      save.disabled = false; save.textContent = "Save changes";
    } }, h("label", { class: "fld" }, "Display name", name), h("label", { class: "fld" }, "Photo URL", photo),
      h("div", { class: "fld" }, "Preferred languages", T.languages.el), h("div", { class: "fld" }, "Preferred genres", T.genres.el),
      h("div", { class: "fld" }, "Favourite movies", T.favourite_movies.el), h("div", { class: "fld" }, "Favourite actors", T.favourite_actors.el), msg, save);
    const danger = (label, fn) => h("button", { class: "btn bad", type: "button", onclick: async () => { if (!confirm(label + "?")) return; try { await fn(); } catch (e) { MF.fail(e); } } }, label);
    MF.render(MF.narrow(h("div", { class: "pfhead" }, p.photo_url && MF.safeUrl(p.photo_url) ? h("img", { class: "av big", src: p.photo_url, alt: "", referrerpolicy: "no-referrer" }) : h("span", { class: "av big" }, (p.display_name || "?")[0].toUpperCase()),
        h("div", null, h("h2", { class: "mt" }, p.display_name), h("p", { class: "meta" }, `${p.email} · member since ${String(p.created_at || "").slice(0, 10)}`))),
      h("div", { class: "authcard" }, h("h3", { class: "sech" }, "Taste & preferences"), f),
      h("div", { class: "authcard" }, h("h3", { class: "sech" }, "Data & account"), h("div", { class: "center", style: "justify-content:flex-start;margin:0" },
        danger("Reset taste preferences", async () => { await MF.api("POST", "/api/profile/preferences/reset"); MF.toast("Preferences reset ho gayi"); MF.profile(); }),
        danger("Clear recommendation history", async () => { await MF.api("DELETE", "/api/history/recommendations"); MF.toast("History clear ho gayi"); }),
        h("button", { class: "btn", type: "button", onclick: MF.logout }, "Logout")))));
  };
})();
