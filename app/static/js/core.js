/* MoodFlix core: helpers, API client, session + library state, shared UI. Exposed as window.MF.
 * Backend routes used here: /api/movies/catalog, /api/auth/*, /api/library, /api/feedback,
 * /api/movies/<key>/audio-languages. Nothing is duplicated from backend recommendation logic. */
(() => {
  "use strict";
  const MF = (window.MF = { user: null, lib: [], catalog: null, nav: 0, next: "#home", byKey: new Map(), byImdb: new Map(), byTitle: new Map() });
  const $ = (id) => document.getElementById(id);

  /* ---------- helpers ---------- */
  function h(tag, props, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v == null || v === false) continue;
      if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v === true ? "" : v);
    }
    kids.flat(Infinity).forEach((c) => { if (c != null && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c))); });
    return n;
  }
  const NA = (v) => (v == null || v === "" || v === "N/A" || v === "Information currently unavailable" || v === "No synopsis available." ? "" : v);
  const splitList = (s) => (Array.isArray(s) ? s : String(s || "").split(/[,|]/)).map((x) => String(x).trim()).filter((x) => x && x !== "N/A");
  const title = (s) => String(s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const hue = (s) => [...String(s)].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 7);
  const safeUrl = (u) => { try { const p = new URL(u); return /^https?:$/.test(p.protocol) ? p.href : ""; } catch { return ""; } };
  const fmtRuntime = (m) => (m > 0 ? `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}m` : "");
  Object.assign(MF, { h, $, NA, splitList, title, hue, safeUrl, fmtRuntime });

  /* ---------- API ---------- */
  MF.api = async (method, url, body) => {
    let res;
    try { res = await fetch(url, { method, credentials: "same-origin", headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined }); }
    catch { throw Object.assign(new Error("Server se connect nahi ho paaya. Check karo ki backend chal raha hai."), { status: 0 }); }
    let data = null;
    try { data = await res.json(); } catch { /* non-JSON */ }
    if (!res.ok) throw Object.assign(new Error((data && data.error) || `Kuch gadbad ho gayi (${res.status}).`), { status: res.status, data });
    return data;
  };

  /* ---------- movie keys + normalisation ---------- */
  MF.key = (m) => {
    const id = String(m.imdb_id || "").trim().toLowerCase();
    return id.startsWith("tt") ? `imdb:${id}` : `title:${String(m.title || "").trim().toLowerCase()}:${m.year || m.release_year || ""}`;
  };
  MF.payload = (m) => ({ title: m.title, year: m.year, release_year: m.year, imdb_id: m.imdb_id || undefined, genres: m.genres || [], languages: m.languages || [] });

  function fromRow(r) {
    const year = parseInt(r.year) || null, rt = parseFloat(r.imdb_rating), langs = splitList(r.language);
    const m = { _n: 1, _src: "catalog", title: r.title, year, release_year: year, runtime: parseInt(r.runtime) || 0, genres: splitList(r.genre), languages: langs, language: langs[0] || "",
      country: r.country || "", director: NA(r.director), actors: splitList(r.actors), plot: NA(r.plot), poster: safeUrl(NA(r.poster)), imdb_id: r.imdb_id, rating: isFinite(rt) ? rt : null,
      votes: parseInt(String(r.imdb_votes || "").replace(/,/g, "")) || 0, rated: NA(r.rated), awards: NA(r.awards), moods: [], why: [], ott: [], dub: "unknown" };
    m._h = [m.title, m.genres.join(" "), m.languages.join(" "), m.actors.join(" "), m.director, m.country, m.plot, m.year].join(" ").toLowerCase();
    return m;
  }
  MF.loadCatalog = () => (MF._cp ||= MF.api("GET", "/api/movies/catalog").then((d) => {
    MF.catalog = (d.movies || []).map(fromRow).filter((m) => m.title);
    MF.catalog.forEach((m) => { MF.byKey.set(MF.key(m), m); if (m.imdb_id) MF.byImdb.set(String(m.imdb_id).toLowerCase(), m); MF.byTitle.set(`${m.title.toLowerCase()}|${m.year}`, m); });
    return MF.catalog;
  }).catch((e) => { MF._cp = null; throw e; }));
  MF.lookup = (m) => (m.imdb_id && MF.byImdb.get(String(m.imdb_id).toLowerCase())) || MF.byTitle.get(`${String(m.title || "").toLowerCase()}|${m.year}`) || null;

  /* Unify catalog rows, adaptive recs, quiz recs, mode recs into one shape. */
  MF.norm = (m) => {
    if (m._n) return m;
    const pos = (...v) => { for (const x of v) { const n = Number(x); if (x != null && x !== "" && isFinite(n) && n > 0) return n; } return null; };
    const cast = (m.cast && m.cast.actors) || m.actors;
    const langs = splitList(m.languages && m.languages.length ? m.languages : m.language);
    const n = { _n: 1, _src: "rec", title: m.title, year: parseInt(m.year || m.release_year) || null, runtime: pos(m.runtime) || 0, genres: splitList(m.genres), languages: langs, language: langs[0] || "",
      country: m.country || m.industry || "", industry: m.industry || "", director: NA(m.director), actors: splitList(cast), plot: NA(m.plot), poster: safeUrl(NA(m.poster)), imdb_id: m.imdb_id || "",
      rating: pos(m.imdb_rating, m.ratings && m.ratings.imdb, m.rating), rt: m.ratings && m.ratings.rotten_tomatoes && m.ratings.rotten_tomatoes.tomatometer, moods: splitList(m.moods),
      why: Array.isArray(m.reasons) ? m.reasons : m.why ? [m.why] : m.reasons ? [m.reasons] : [], ott: Array.isArray(m.ott_availability) ? m.ott_availability : [], dub: m.dub_status || "unknown", score: m.score, rated: "", awards: "" };
    n.release_year = n.year;
    const c = MF.lookup(n); // fill gaps from the 870-movie catalogue (same backend data, no extra API)
    if (c) { for (const k of ["poster", "plot", "director", "country", "rated", "awards"]) if (!n[k]) n[k] = c[k]; if (!n.runtime) n.runtime = c.runtime; if (!n.actors.length) n.actors = c.actors; if (!n.genres.length) n.genres = c.genres; if (!n.imdb_id) n.imdb_id = c.imdb_id; if (n.rating == null) n.rating = c.rating; }
    return n;
  };

  /* ---------- toast ---------- */
  MF.toast = (msg) => {
    let t = $("toast");
    if (!t) { t = h("div", { id: "toast", role: "status", "aria-live": "polite" }); document.body.append(t); }
    t.textContent = msg; t.classList.add("show"); clearTimeout(MF._tt); MF._tt = setTimeout(() => t.classList.remove("show"), 2600);
  };

  /* ---------- session + library state ---------- */
  const painters = new Set();
  MF.bind = (el, paint) => { paint(); painters.add({ el, paint }); return el; };
  MF.repaint = () => painters.forEach((p) => { if (p.el.isConnected) p.paint(); else painters.delete(p); });

  MF.paintHeader = () => {
    const box = $("authBox"), u = MF.user;
    box.replaceChildren(...(u
      ? [h("a", { class: "me", href: "#profile", title: "Your profile" }, h("span", { class: "av" }, (u.display_name || u.email || "?")[0].toUpperCase()), h("span", { class: "nm" }, u.display_name || u.email)),
         h("button", { class: "btn sm", type: "button", id: "logoutBtn", onclick: MF.logout }, "Logout")]
      : [h("a", { class: "btn sm", href: "#login" }, "Sign in"), h("a", { class: "btn sm primary", href: "#signup" }, "Sign up")]));
    const c = MF.lib.filter((r) => r.status === "watchlist").length, b = $("wlCount");
    b.textContent = c; b.hidden = !c;
  };
  MF.loadLib = async () => {
    if (!MF.user) MF.lib = [];
    else { try { MF.lib = (await MF.api("GET", "/api/library")).movies || []; } catch (e) { if (e.status === 401) MF.user = null; MF.lib = []; } }
    MF.paintHeader(); MF.repaint();
  };
  MF.refreshUser = async () => {
    try { MF.user = (await MF.api("GET", "/api/auth/me")).user; } catch { MF.user = null; }
    await MF.loadLib();
  };
  MF.logout = async () => {
    try { await MF.api("POST", "/api/auth/logout"); } catch { /* cookie may already be gone */ }
    MF.user = null; MF.lib = []; MF.paintHeader(); MF.repaint(); MF.toast("Logout ho gaye 👋");
    if (location.hash === "#home" || !location.hash) MF.route(); else location.hash = "#home";
  };
  MF.requireLogin = (msg) => {
    if (MF.user) return true;
    MF.toast(msg || "Pehle login karo 🔐"); MF.next = location.hash || "#home"; location.hash = "#login"; return false;
  };
  MF.rec = (m, status) => MF.lib.find((r) => r.movie_key === MF.key(m) && r.status === status);
  MF.isHidden = (m) => !!(MF.user && (MF.rec(m, "hidden") || MF.rec(m, "disliked")));
  const fail = (e) => { if (e.status === 401) { MF.user = null; MF.paintHeader(); MF.requireLogin("Session expire ho gaya, dobara login karo."); } else MF.toast(e.message); };
  MF.fail = fail;

  const STATUS_LABEL = { watchlist: "Watchlist", watched: "Watched", liked: "Liked", disliked: "Disliked", hidden: "Hidden" };
  MF.setStatus = async (m, status) => { // toggle a library state via /api/library
    if (!MF.requireLogin()) return;
    try {
      const ex = MF.rec(m, status);
      if (ex) { await MF.api("DELETE", `/api/library/${ex.id}`); MF.toast(`${m.title}: ${STATUS_LABEL[status]} se hata diya`); }
      else { const body = { movie: MF.payload(m), status }; if (status === "watched") body.watched_at = new Date().toISOString().slice(0, 10); await MF.api("POST", "/api/library", body); MF.toast(`${m.title} → ${STATUS_LABEL[status]} ✓`); }
      await MF.loadLib();
    } catch (e) { fail(e); }
  };
  const FB = { like: "liked", dislike: "disliked", not_interested: "hidden" };
  MF.feedback = async (m, fb) => { // like / dislike / not_interested via /api/feedback
    if (!MF.requireLogin()) return;
    try {
      const ex = MF.rec(m, FB[fb]);
      if (ex) { await MF.api("DELETE", `/api/library/${ex.id}`); MF.toast("Feedback hata diya"); }
      else {
        await MF.api("POST", "/api/feedback", { movie: MF.payload(m), feedback: fb });
        MF.toast(fb === "like" ? "👍 Like saved. Aage aisi movies zyada milengi." : fb === "dislike" ? "👎 Noted. Ye movie ab suggest nahi hogi." : "🚫 Hidden. Ye movie ab suggest nahi hogi.");
      }
      await MF.loadLib();
    } catch (e) { fail(e); }
  };

  /* ---------- rendering basics ---------- */
  MF.render = (...nodes) => {
    const app = $("app");
    app.replaceChildren(...nodes.flat(Infinity).filter(Boolean));
    const f = app.querySelector("h1,h2"); if (f) { f.tabIndex = -1; f.focus({ preventScroll: true }); }
    window.scrollTo({ top: 0 });
  };
  MF.narrow = (...n) => h("div", { class: "narrow" }, n);
  MF.wide = (...n) => h("div", { class: "container" }, n);
  MF.genie = (mood, text) => h("div", { class: `genie ${mood}` }, h("div", { class: "orb", "aria-hidden": "true" }, h("i")), text ? h("div", { class: "bubble" }, text) : null);
  MF.notice = (t) => h("div", { class: "notice" }, t);
  MF.errorView = (err, retry) => MF.render(MF.narrow(MF.genie("sad", "Oops!"), h("h2", { class: "q" }, "Kuch gadbad ho gayi"), h("p", { class: "sub" }, err.message || "Dobara try karo."),
    h("div", { class: "center" }, h("button", { class: "btn primary", onclick: retry || MF.route }, "Dobara try karo"))));
  MF.skelRow = (n = 6) => h("div", { class: "scroll", "aria-busy": "true" }, Array.from({ length: n }, () => h("div", { class: "card skel" }, h("div", { class: "poster" }), h("div", { class: "cbody" }, h("i"), h("i"), h("i")))));

  /* ---------- shared UI ---------- */
  MF.poster = (m) => {
    const ph = () => h("div", { class: "poster poster-ph", role: "img", "aria-label": `${m.title} (poster not available)`, style: `background:linear-gradient(145deg,hsl(${hue(m.title)} 60% 42%),hsl(${(hue(m.title) + 50) % 360} 65% 28%))` },
      h("span", null, String(m.title || "?").split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase()), h("small", null, "No poster"));
    if (!m.poster) return ph();
    const img = h("img", { class: "poster", src: m.poster, alt: `${m.title} poster`, loading: "lazy", referrerpolicy: "no-referrer" });
    img.addEventListener("error", () => img.replaceWith(ph()));
    return img;
  };
  MF.star = (m) => (m.rating != null ? h("span", { class: "star" }, `★ ${Number(m.rating).toFixed(1)}`) : h("span", { class: "star na" }, "★ N/A"));
  MF.metaLine = (m) => [m.year, fmtRuntime(m.runtime), m.languages.join(", "), m.country, m.rated].filter(Boolean).join(" · ");

  MF.card = (m, o = {}) => {
    const open = () => MF.openTitle(m);
    const body = h("div", { class: "cbody" }, h("div", { class: "crow" }, MF.star(m), h("small", null, m.year || "")),
      h("button", { class: "ctitle", type: "button", onclick: open }, m.title),
      m.genres.length ? h("small", { class: "cgen" }, m.genres.slice(0, 3).join(" · ")) : null,
      m.plot ? h("p", { class: "cplot" }, m.plot) : null);
    if (o.extra) body.append(...o.extra);
    else body.append(MF.stateBtn(m, "watchlist", "wbtn", { off: "+ Watchlist", on: "✓ In Watchlist" }));
    const ribbon = h("span", { class: "ribbon", "aria-hidden": "true" });
    MF.bind(ribbon, () => { const on = !!MF.rec(m, "watchlist"); ribbon.textContent = on ? "✓" : "+"; ribbon.classList.toggle("on", on); });
    return h("article", { class: "card" }, h("button", { class: "pbtn", type: "button", onclick: open, "aria-label": `${m.title} details` }, MF.poster(m), ribbon), body);
  };
  // Button that reflects a library state (toggle on click).
  MF.stateBtn = (m, status, cls, labels) => {
    const b = h("button", { class: cls, type: "button", onclick: () => labels.fb ? MF.feedback(m, labels.fb) : MF.setStatus(m, status) });
    return MF.bind(b, () => { const on = !!MF.rec(m, status); b.textContent = on ? labels.on : labels.off; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on); });
  };
  MF.actionBar = (m) => h("div", { class: "actions", role: "group", "aria-label": `Actions for ${m.title}` },
    MF.stateBtn(m, "watchlist", "act", { off: "+ Watchlist", on: "✓ Watchlist" }),
    MF.stateBtn(m, "watched", "act", { off: "👁 Watched", on: "✓ Watched" }),
    MF.stateBtn(m, "liked", "act", { off: "👍 Like", on: "👍 Liked", fb: "like" }),
    MF.stateBtn(m, "disliked", "act", { off: "👎 Dislike", on: "👎 Disliked", fb: "dislike" }),
    MF.stateBtn(m, "hidden", "act", { off: "🚫 Not interested", on: "🚫 Hidden", fb: "not_interested" }));

  /* OTT: India providers grouped by access type; Watch Now only when the provider gave a link. */
  const ACCESS = [["sub", "Subscription"], ["free", "Free"], ["rent", "Rent"], ["buy", "Buy"], ["tve", "TV Everywhere"]];
  MF.ottBlock = (m) => {
    const wrap = h("section", { class: "ott-block" }, h("div", { class: "label" }, "Where to watch · India 🇮🇳"));
    if (!m.ott.length) { wrap.append(h("p", { class: "meta" }, m._src === "rec" ? "Is movie ke liye India OTT info nahi mili (provider match ya Watchmode key ke bina nahi aati)." : "India OTT info sirf recommendation results ke saath aati hai. Mood quiz se ye movie aaye to yahan providers dikhenge.")); return wrap; }
    const groups = new Map();
    m.ott.forEach((o) => { const k = String(o.availability || o.type || "other").toLowerCase(); (groups.get(k) || groups.set(k, []).get(k)).push(o); });
    const order = [...ACCESS.map((a) => a[0]), ...[...groups.keys()].filter((k) => !ACCESS.some((a) => a[0] === k))];
    order.filter((k) => groups.has(k)).forEach((k) => {
      const label = (ACCESS.find((a) => a[0] === k) || [0, groups.get(k)[0].availability_label || "Other"])[1];
      wrap.append(h("div", { class: "ott-group" }, h("span", { class: "ott-type t-" + k }, label),
        h("div", { class: "ott" }, groups.get(k).map((o) => { const u = safeUrl(o.url), name = o.platform || o.provider || o.name || "Provider";
          return u ? h("a", { href: u, target: "_blank", rel: "noopener noreferrer", "aria-label": `Watch ${m.title} on ${name} (${label})` }, name, h("b", null, " Watch now ↗")) : h("span", null, name); }))));
    });
    return wrap;
  };

  /* Audio / dubbing: only sourced evidence is shown; everything else stays "unknown". */
  MF.dubBlock = (m) => {
    const out = h("p", { class: "meta dub" }, "🎧 Audio / dubbing: ", h("span", null, "unknown (koi verified source nahi)"));
    const span = out.querySelector("span");
    MF.api("GET", `/api/movies/${encodeURIComponent(MF.key(m))}/audio-languages`).then((d) => {
      const rows = (d.audio_languages || []).filter((r) => r.status !== "unknown" && r.source);
      if (rows.length) span.textContent = rows.map((r) => `${String(r.language_code).toUpperCase()} ${r.status === "available" ? "available" : "not available"} (source: ${r.source})`).join("; ");
    }).catch(() => {});
    return out;
  };

  MF.detail = (m, o = {}) => h("article", { class: "movie" }, MF.poster(m),
    h("div", null, h(o.big ? "h1" : "h3", { class: "mt" }, m.title), h("p", { class: "meta" }, MF.metaLine(m)),
      h("div", { class: "badges" }, h("span", { class: "badge imdb" }, m.rating != null ? `★ ${Number(m.rating).toFixed(1)}` : "★ N/A"), m.rt ? h("span", { class: "badge" }, `🍅 ${m.rt}`) : null, o.tag ? h("span", { class: "badge tag" }, o.tag) : null),
      h("div", { class: "chips" }, m.genres.map((g) => h("span", { class: "chip" }, g)), m.moods.map((x) => h("span", { class: "chip mood" }, title(x)))),
      m.plot ? h("p", { class: "plot" }, m.plot) : h("p", { class: "plot muted" }, "Plot abhi available nahi hai."),
      m.why.length ? h("ul", { class: "why" }, m.why.map((r) => h("li", null, r))) : null,
      m.director ? h("p", { class: "meta" }, h("b", null, "Director: "), m.director) : null,
      m.actors.length ? h("p", { class: "meta" }, h("b", null, "Cast: "), m.actors.join(", ")) : null,
      m.awards ? h("p", { class: "meta" }, "🏆 ", m.awards) : null,
      MF.ottBlock(m), MF.dubBlock(m),
      /^tt\d+$/.test(m.imdb_id || "") ? h("p", { class: "meta" }, h("a", { href: `https://www.imdb.com/title/${m.imdb_id}/`, target: "_blank", rel: "noopener noreferrer" }, "IMDb par dekho ↗")) : null,
      MF.actionBar(m)));
})();
