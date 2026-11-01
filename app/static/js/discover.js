/* MoodFlix discovery. Backend: /api/modes/start|answer, /api/thriller-quiz/recommend,
 * /api/recommend/questions|answer|finish (public Genie), /api/profile, /api/history/recommendations, /api/library */
(() => {
  "use strict";
  const { h, title } = MF;
  const ANY = "__any__";
  const ROLES = ["Best Match", "Different Experience", "Surprise Discovery"];

  const LABEL = { not_sure: "Not sure", any: "Koi bhi / Any", under_100: "Under 100 min", "100_to_140": "100–140 min", over_140: "Over 140 min", science_fiction: "Sci-Fi", hidden_gem: "Hidden gem", something_new: "Something new",
    mind_bending: "Mind-bending", feel_good: "Feel-good", very_complex: "Very complex", uplifting_any: "Uplifting, any", high: "Highly rated", popular: "Popular", exact: "Exact match", balanced: "Balanced", loose: "Loose match", scared: "Scared / spooky" };
  const EM = { happy: "😄", fun: "🎉", sad: "😢", thoughtful: "🤔", thrilled: "😰", scared: "👻", relaxed: "😌", romantic: "💕", inspired: "✨", adventurous: "🧭", action: "💥", comedy: "😂", drama: "🎭", thriller: "😰",
    science_fiction: "🚀", romance: "💕", animation: "🎨", horror: "👻", documentary: "🎥", under_100: "⚡", "100_to_140": "⏱️", over_140: "🎞️", high: "⭐", hidden_gem: "💎", popular: "🔥", something_new: "🆕",
    mind_bending: "🌀", feel_good: "☀️", easy: "🙂", clever: "🧠", very_complex: "🤯", light: "🪶", emotional: "🥹", uplifting_any: "✨", exact: "🎯", balanced: "⚖️", loose: "🌈", not_sure: "🤷", any: "🤷" };
  const LANGS = ["Hindi", "English", "Malayalam", "Tamil", "Telugu", "Kannada", "All South Indian Languages", "All Languages"];
  const decorate = (qid, v) => ({ em: qid === "languages" ? "🌐" : EM[v] || "🎬", label: LABEL[v] || (LANGS.includes(v) ? v : title(v)) });
  const isSoft = (v) => v === "not_sure" || v === "any" || v === ANY;

  const thinking = (t) => MF.render(MF.narrow(MF.genie("think", t)));
  const meter = (n, total, left) => h("div", { class: "meter" }, h("div", { class: "meter-row" }, h("span", null, `SAWAAL ${n}`), h("span", null, left || `~${total} sawaal`)),
    h("div", { class: "track", role: "progressbar", "aria-valuemin": 0, "aria-valuemax": 100, "aria-valuenow": Math.round((n / total) * 100) }, h("div", { class: "fill", style: `width:${Math.min(100, Math.round((n / total) * 100))}%` })));

  /* ---------- hub ---------- */
  const MODES = [
    ["#mood", "☀️", "Today’s Mood", "Apna mood batao, 5 quick sawaal, 3 perfect picks.", true],
    ["#surprise", "🎲", "Surprise Me", "Kuch naya aur unexpected, Genie choose karega.", true],
    ["#thriller", "🕵️", "My Taste · Thriller Quiz", "10 sawaal, tumhare thriller taste ke hisaab se matches.", false],
    ["#genie", "🧞", "Quick Genie Guess", "Bina login ke: Genie sawaal poochhke guess karta hai.", false],
  ];
  MF.discover = () => {
    MF.backFn = null;
    MF.render(MF.narrow(MF.genie("", "Kaise dhundhein tumhari movie?"), h("h2", { class: "q" }, "Discover your next movie"), h("p", { class: "sub" }, "Mood, surprise ya apna taste. Recommendations tumhare feedback se behtar hoti jaati hain."),
      h("div", { class: "modes" }, MODES.map(([href, em, t, d, login]) => h("a", { class: "mode", href }, h("span", { class: "em" }, em), h("b", null, t), h("small", null, d),
        login && !MF.user ? h("span", { class: "pill lock" }, "🔐 Login required") : null)))));
  };

  /* ---------- results ---------- */
  async function showRecs(data, again, heading) {
    await MF.loadCatalog().catch(() => {});
    const recs = (data.recommendations || []).map(MF.norm);
    MF.render(MF.narrow(MF.genie(recs.length ? "guess" : "sad", recs.length ? heading || "Ye rahe tumhare picks! 🍿" : "Hmm, koi match nahi mila…"),
      recs.length ? recs.map((m, i) => h("div", { class: "movie-wrap" }, MF.detail(m, { tag: ROLES[i] || null }))) : [h("h2", { class: "q" }, "Is combination ki koi movie nahi mili"),
        MF.notice(data.relaxation_prompt || "Thode kam constraints try karo: “Koi bhi / Not sure” chuno ya language/runtime relax karo.")],
      data.notice ? h("p", { class: "meta", style: "text-align:center;margin-top:14px" }, data.notice) : null,
      recs.length && recs.length < 3 && data.relaxation_prompt ? MF.notice(data.relaxation_prompt) : null,
      !MF.user ? MF.notice("Login karke Like / Dislike / Watchlist use karo, tumhari recommendations personalize hongi.") : null,
      h("div", { class: "center" }, h("button", { class: "btn primary", type: "button", onclick: again }, "Dobara try karo"), h("a", { class: "btn", href: "#library", style: "text-decoration:none" }, "My Library"))));
  }

  /* ---------- Today's Mood / Surprise Me (login required) ---------- */
  const MODE_TXT = { today_mood: "Aaj ka mood ☀️", surprise_me: "Surprise Me 🎲" };
  MF.mode = async (mode) => {
    if (!MF.requireLogin("Is mode ke liye login zaroori hai")) return;
    let sid = null, asked = 0;
    const fail = (e) => (e.status === 401 ? MF.fail(e) : MF.errorView(e, () => MF.mode(mode)));
    const ask = (q) => {
      const opts = q.options.map((v) => { const d = decorate(q.id === "languages" ? "languages" : q.id, v);
        return h("button", { class: "opt" + (isSoft(v) ? " ghost" : ""), type: "button", onclick: () => answer(q, v) }, isSoft(v) ? null : h("span", { class: "em", "aria-hidden": "true" }, d.em), d.label); });
      opts.sort((a, b) => a.classList.contains("ghost") - b.classList.contains("ghost"));
      MF.render(MF.narrow(MF.genie("", MODE_TXT[mode]), meter(asked + 1, asked >= 5 ? asked + 1 : 5), h("h2", { class: "q" }, q.text), h("div", { class: "opts" }, opts),
        h("div", { class: "center" }, h("a", { class: "link", href: "#discover" }, "← Modes"))));
    };
    const answer = async (q, v) => {
      document.querySelectorAll(".opt").forEach((b) => (b.disabled = true)); thinking("Hmm, samajh gaya… 🧐");
      try { const d = await MF.api("POST", "/api/modes/answer", { session_id: sid, question_id: q.id, answer: v }); asked++; d.complete ? showRecs(d, () => MF.mode(mode)) : ask(d.question); }
      catch (e) { if (e.status === 404 || e.status === 409) MF.errorView(new Error("Ye quiz session ab valid nahi hai. Dobara shuru karte hain."), () => MF.mode(mode)); else fail(e); }
    };
    thinking("Genie jaag raha hai… 🧞");
    try { const d = await MF.api("POST", "/api/modes/start", { mode }); sid = d.session_id; ask(d.question); } catch (e) { fail(e); }
  };

  /* ---------- Thriller quiz (existing 10 questions) ---------- */
  const TQ = [
    { id: "thriller_type", title: "Which type of thriller do you enjoy most?", options: ["Mind-blowing twists", "Murder mystery", "Psychological thriller", "Crime investigation", "Sci-fi mystery"] },
    { id: "story_priority", title: "What matters most in a movie?", options: ["Unpredictable story", "Fast-paced entertainment", "Intelligent screenplay", "Suspense until the end", "A satisfying climax"] },
    { id: "pacing", title: "How do you feel about slow-paced movies?", options: ["Love slow-burn stories", "Okay if the payoff is great", "Prefer medium pace", "Only fast-paced movies"] },
    { id: "ending", title: "What kind of ending do you prefer?", options: ["Completely unexpected", "Clever and logical", "Emotional and satisfying", "Dark and disturbing", "Ambiguous, open to interpretation"] },
    { id: "complexity", title: "How challenging should the mystery be?", options: ["Easy and entertaining", "Some clues to solve", "Complex puzzle", "Extremely complicated; I want to think hard"] },
    { id: "atmosphere", title: "Which atmosphere do you prefer?", options: ["Realistic crime", "Dark and gritty", "Stylish and fun", "Tense and claustrophobic", "Unusual and surreal"] },
    { id: "comedy", title: "How much comedy do you want?", options: ["A lot of humor", "Some humor", "Almost none", "Depends on the story"] },
    { id: "languages", title: "Which languages should we include?", sub: "Choose one or more. Next question ke examples isi pe depend karenge.", multiple: true, options: ["Hindi", "English", "Malayalam", "Tamil", "Telugu", "Kannada", "All South Indian languages", "All languages"] },
    { id: "example_movie", title: "Which movies have impressed you most?", sub: "Examples tumhari language choice ke hisaab se badalte hain.", options: [] },
    { id: "recommendation_style", title: "What kind of recommendations do you want?", options: ["Hidden gems nobody talks about", "Highly rated masterpieces", "Underrated thrillers", "Movies with insane twists", "A mix of everything"] },
  ];
  const NONE = "None of these / haven't watched them";
  const EXAMPLES = { Hindi: ["Andhadhun", "Kahaani", "Talaash"], English: ["Gone Girl", "Shutter Island", "Prisoners"], Malayalam: ["Drishyam", "Memories", "Anjaam Pathiraa"], Tamil: ["Ratsasan", "Vikram Vedha", "Maharaja"],
    Telugu: ["Agent Sai Srinivasa Athreya", "HIT: The First Case", "Evaru"], Kannada: ["U Turn", "Kavaludaari", "Rangitaranga"] };
  function exampleOptions(a) {
    const sel = a.languages || [];
    const langs = !sel.length || sel.includes("All languages") ? Object.keys(EXAMPLES) : sel.flatMap((l) => (l === "All South Indian languages" ? ["Malayalam", "Tamil", "Telugu", "Kannada"] : [l])).filter((l) => EXAMPLES[l]);
    return [...new Set([...langs.flatMap((l) => EXAMPLES[l]), NONE])];
  }
  MF.thriller = () => {
    const A = {}; let cur = 0, busy = false;
    const paint = () => {
      const q = TQ[cur], opts = q.id === "example_movie" ? exampleOptions(A) : q.options, picked = q.multiple ? A[q.id] || [] : A[q.id] ? [A[q.id]] : [];
      const choose = (v) => {
        if (q.multiple) { let c = A[q.id] || []; c = c.includes(v) ? c.filter((x) => x !== v) : [...c.filter((x) => x !== "All languages"), v]; if (v === "All languages" && c.includes(v)) c = ["All languages"]; A[q.id] = c; } else A[q.id] = v;
        paint();
      };
      const next = h("button", { class: "btn primary", type: "button", disabled: !picked.length || busy, onclick: () => { if (cur < TQ.length - 1) { cur++; const nq = TQ[cur]; if (nq.id === "example_movie" && !exampleOptions(A).includes(A.example_movie)) delete A.example_movie; paint(); } else submit(); } }, cur === TQ.length - 1 ? "Find my movies →" : "Continue →");
      MF.render(MF.narrow(h("div", { class: "meter" }, h("div", { class: "meter-row" }, h("span", null, `QUESTION ${cur + 1} OF ${TQ.length}`), h("span", null, `${Math.round(((cur + 1) / TQ.length) * 100)}%`)),
        h("div", { class: "track" }, h("div", { class: "fill", style: `width:${((cur + 1) / TQ.length) * 100}%` }))),
        h("h2", { class: "q" }, q.title), h("p", { class: "sub" }, q.sub || (q.multiple ? "Jitni chaho utni languages chuno." : "Ek answer chuno.")),
        h("div", { class: "opts" }, opts.map((v) => h("button", { class: "opt" + (picked.includes(v) ? " sel" : ""), type: "button", "aria-pressed": picked.includes(v), onclick: () => choose(v) }, picked.includes(v) ? "✓ " : "", v))),
        h("div", { class: "center" }, h("button", { class: "btn", type: "button", disabled: cur === 0, onclick: () => { cur--; paint(); } }, "← Back"), next),
        !MF.user ? h("p", { class: "meta", style: "text-align:center;margin-top:14px" }, "Tip: login karoge to results tumhare taste profile se personalize honge.") : null));
    };
    const submit = async () => {
      busy = true; thinking("Tumhare taste se match kar raha hoon… 🕵️");
      try { const d = await MF.api("POST", "/api/thriller-quiz/recommend", { answers: A }); showRecs(d, MF.thriller, "Tumhare thriller matches 🕵️"); }
      catch (e) { MF.errorView(e, () => { busy = false; paint(); }); }
    };
    paint();
  };

  /* ---------- Quick Genie guess (public adaptive API) ---------- */
  MF.genieGuess = () => {
    const S = { sid: null, total: 0, count: 0, asked: 0, recs: [], idx: 0, done: false };
    const err = (e) => MF.errorView(e.status === 404 ? new Error("Session expire ho gaya. Dobara shuru karte hain.") : e, MF.genieGuess);
    const step = (d) => { S.sid = d.session_id; S.count = d.candidate_count ?? S.count; if (d.complete || !d.question) result(d.recommendations || []); else ask(d.question); };
    const ask = (q) => {
      const LN = { en: "English", hi: "Hindi", ta: "Tamil", te: "Telugu", ml: "Malayalam", kn: "Kannada", ja: "Japanese", ko: "Korean", fr: "French", es: "Spanish" };
      const opts = q.options.map((o) => h("button", { class: "opt" + (o.value === ANY ? " ghost" : ""), type: "button", onclick: () => answer(q, o) }, o.value === ANY ? "Koi farak nahi" : q.field === "language" ? LN[String(o.value).toLowerCase()] || o.label : o.label));
      opts.sort((a, b) => a.classList.contains("ghost") - b.classList.contains("ghost"));
      MF.render(MF.narrow(MF.genie("", `Abhi ${S.count} movies mein se dhundh raha hoon`), meter(S.asked + 1, Math.max(S.asked + 2, 5), `${S.count} movies bachi`), h("h2", { class: "q" }, q.text), h("div", { class: "opts" }, opts),
        h("div", { class: "center" }, S.asked ? h("button", { class: "link", type: "button", onclick: finish }, "Bas, abhi result dikhao →") : null, h("button", { class: "link", type: "button", onclick: MF.genieGuess }, "Shuru se"))));
    };
    const answer = async (q, o) => { thinking("Hmm, samajh gaya… 🧐"); try { step(await MF.api("POST", "/api/recommend/answer", { session_id: S.sid, question_id: q.id, answer: o.value })); S.asked++; } catch (e) { err(e); } };
    const finish = async () => { thinking("Result nikaal raha hoon… 🔮"); try { result((await MF.api("POST", "/api/recommend/finish", { session_id: S.sid })).recommendations || []); } catch (e) { err(e); } };
    const result = async (raw) => {
      await MF.loadCatalog().catch(() => {}); S.recs = raw.map(MF.norm); S.idx = 0; S.done = false; guess();
    };
    const guess = () => {
      const { recs, idx } = S;
      if (!recs.length) return MF.render(MF.narrow(MF.genie("sad", "Hmm…"), h("h2", { class: "q" }, "Is combination ki koi movie nahi mili"), h("div", { class: "center" }, h("button", { class: "btn primary", onclick: MF.genieGuess }, "Dobara try karo"))));
      if (idx >= recs.length) return MF.render(MF.narrow(MF.genie("sad", "Meri saari guesses khatam 😅"), h("h2", { class: "q" }, "Koi bhi pasand nahi aayi?"), h("div", { class: "center" },
        h("button", { class: "btn", onclick: () => { S.idx = 0; guess(); } }, "Pehli guess dobara dekho"), h("button", { class: "btn primary", onclick: MF.genieGuess }, "Naya mood try karo"))));
      const m = recs[idx];
      MF.render(MF.narrow(MF.genie("guess", S.done ? "Maza aaye! 🍿" : idx === 0 ? "Mera guess hai… 🔮" : "Achha, toh phir ye? 🤔"), h("div", { class: "movie-wrap" }, MF.detail(m)),
        S.done ? h("div", { class: "center" }, h("button", { class: "btn primary", onclick: MF.genieGuess }, "Naya mood, nayi movie ✨"))
          : h("div", { class: "center" }, h("button", { class: "btn ok", onclick: () => { S.done = true; guess(); } }, "✅ Sahi pakda!"), h("button", { class: "btn bad", onclick: () => { S.idx++; guess(); } }, "❌ Ye nahi"))));
    };
    thinking("Soch raha hoon… 🤔");
    MF.api("GET", "/api/recommend/questions").then((d) => { S.total = d.candidate_count || 0; step(d); }).catch(err);
  };

  /* ---------- My Taste ---------- */
  const fromKey = (r) => { const k = String(r.movie_key || ""), y = parseInt(k.split(":").pop()); return { title: r.title, imdb_id: k.startsWith("imdb:") ? k.slice(5) : "", year: k.startsWith("title:") && y ? y : null }; };
  const chipRow = (label, vals) => h("div", { class: "fld" }, h("div", { class: "label" }, label), vals.length ? h("div", { class: "chips" }, vals.map((v) => h("span", { class: "chip mood" }, v))) : h("p", { class: "meta" }, "Abhi kuch set nahi hai."));
  MF.taste = async () => {
    if (!MF.requireLogin("My Taste dekhne ke liye login karo")) return;
    const t = MF.nav; MF.backFn = null;
    MF.render(MF.narrow(h("h2", { class: "bar-title" }, "My Taste"), MF.notice("Loading…")));
    let prof, hist; try { [prof, hist] = await Promise.all([MF.api("GET", "/api/profile"), MF.api("GET", "/api/history/recommendations?limit=30"), MF.loadLib(), MF.loadCatalog().catch(() => {})]); }
    catch (e) { return e.status === 401 ? MF.fail(e) : MF.errorView(e, MF.taste); }
    if (t !== MF.nav) return;
    const pr = prof.preferences, learned = { genres: new Map(), languages: new Map() };
    MF.lib.filter((r) => r.status === "liked" && r.note).forEach((r) => { try { const n = JSON.parse(r.note); ["genres", "languages"].forEach((k) => (n[k] || []).forEach((v) => learned[k].set(v, (learned[k].get(v) || 0) + 1))); } catch { /* note is free text */ } });
    const cnt = (s) => MF.lib.filter((r) => r.status === s).length, top = (m) => [...m.entries()].sort((a, b) => b[1] - a[1]).map(([k, n]) => `${k}${n > 1 ? ` ×${n}` : ""}`);
    const rows = (hist.history || []).map((r) => { const m = MF.byKey.get(r.movie_key) || MF.norm(fromKey(r));
      return h("li", { class: "hist" }, h("div", null, h("button", { class: "ctitle", type: "button", onclick: () => { MF.backFn = MF.taste; MF.openTitle(m); } }, r.title), h("small", { class: "cgen" }, `${title(r.mode)}${r.role ? ` · ${r.role}` : ""} · ${String(r.recommended_at || "").slice(0, 10)}`)),
        h("div", { class: "actions sm" }, MF.stateBtn(m, "liked", "act", { off: "👍", on: "👍 ✓", fb: "like" }), MF.stateBtn(m, "disliked", "act", { off: "👎", on: "👎 ✓", fb: "dislike" }), MF.stateBtn(m, "hidden", "act", { off: "🚫", on: "🚫 ✓", fb: "not_interested" }))); });
    MF.render(MF.narrow(h("h2", { class: "bar-title" }, "My Taste"),
      h("div", { class: "authcard" }, h("h3", { class: "sech" }, "Your taste profile"), chipRow("Preferred genres", pr.genres), chipRow("Preferred languages", pr.languages), chipRow("Favourite movies", pr.favourite_movies), chipRow("Favourite actors", pr.favourite_actors),
        h("a", { class: "btn", href: "#profile", style: "text-decoration:none" }, "Edit preferences")),
      h("div", { class: "authcard" }, h("h3", { class: "sech" }, "What MoodFlix learned from your feedback"),
        h("div", { class: "stats" }, [["👍 Liked", cnt("liked")], ["👎 Disliked", cnt("disliked")], ["🚫 Hidden", cnt("hidden")], ["👁 Watched", cnt("watched")]].map(([l, n]) => h("div", null, h("b", null, n), h("small", null, l)))),
        chipRow("Genres you like", top(learned.genres)), chipRow("Languages you like", top(learned.languages)),
        h("p", { class: "meta" }, "Likes tumhari preferences mein judte hain; watched, disliked aur hidden movies dobara recommend nahi hoti.")),
      h("div", { class: "authcard" }, h("h3", { class: "sech" }, "Get recommendations"), h("div", { class: "center", style: "justify-content:flex-start;margin:0" },
        h("a", { class: "btn primary", href: "#mood", style: "text-decoration:none" }, "☀️ Today’s Mood"), h("a", { class: "btn", href: "#surprise", style: "text-decoration:none" }, "🎲 Surprise Me"), h("a", { class: "btn", href: "#thriller", style: "text-decoration:none" }, "🕵️ Thriller Quiz"))),
      h("div", { class: "authcard" }, h("h3", { class: "sech" }, "Recent recommendations"), rows.length ? h("ul", { class: "histlist" }, rows) : h("p", { class: "meta" }, "Abhi koi recommendation history nahi hai. Upar se koi mode try karo.")))); 
  };
})();
