// MoodFlix adaptive discovery UI for Surprise Me and Today's Mood.
(() => {
  const $ = (id) => document.getElementById(id);
  let sessionId = null;
  let activeMode = null;
  let busy = false;

  function showMyTaste() {
    $("adaptiveQuiz").classList.add("hidden");
    $("quiz").classList.remove("hidden");
    $("results").classList.add("hidden");
  }

  async function startMode(mode) {
    if (busy) return;
    busy = true;
    activeMode = mode;
    $("quiz").classList.add("hidden");
    $("results").classList.add("hidden");
    $("adaptiveQuiz").classList.remove("hidden");
    $("adaptiveQuiz").querySelectorAll(".movie, .mode-restart").forEach((node) => node.remove());
    $("adaptiveMessage").textContent = "Starting your personalized discovery…";
    try {
      const response = await fetch("/api/modes/start", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode })
      });
      const data = await response.json();
      if (response.status === 401) { location.href = "/login"; return; }
      if (!response.ok) throw new Error(data.error || "Could not start discovery.");
      sessionId = data.session_id;
      renderQuestion(data.question, mode);
    } catch (error) {
      $("adaptiveMessage").textContent = error.message;
    } finally { busy = false; }
  }

  function renderQuestion(question, mode) {
    if (!question) return;
    $("adaptiveModeLabel").textContent = mode === "today_mood" ? "TODAY'S MOOD" : "SURPRISE ME";
    $("adaptiveQuestion").textContent = question.text;
    $("adaptiveSubtitle").textContent = "Choose one answer. The next question may change based on this choice.";
    $("adaptiveStepLabel").textContent = "Adaptive question";
    $("adaptiveMessage").textContent = "";
    const options = $("adaptiveOptions");
    options.replaceChildren();
    question.options.forEach((value) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "option";
      button.textContent = value === "not_sure" ? "I don't know / no preference" : value.replaceAll("_", " ");
      button.addEventListener("click", () => submitAnswer(question.id, value));
      options.appendChild(button);
    });
  }

  async function submitAnswer(questionId, answer) {
    if (busy) return;
    busy = true;
    $("adaptiveMessage").textContent = "Finding the next best question…";
    [...$("adaptiveOptions").children].forEach((button) => { button.disabled = true; });
    try {
      const response = await fetch("/api/modes/answer", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, question_id: questionId, answer })
      });
      const data = await response.json();
      if (response.status === 401) { location.href = "/login"; return; }
      if (!response.ok) throw new Error(data.error || "Could not save answer.");
      if (data.complete) renderRecommendations(data);
      else renderQuestion(data.question, activeMode);
    } catch (error) {
      $("adaptiveMessage").textContent = error.message;
      [...$("adaptiveOptions").children].forEach((button) => { button.disabled = false; });
    } finally { busy = false; }
  }

  function renderRecommendations(data) {
    const section = $("adaptiveQuiz");
    $("adaptiveModeLabel").textContent = "YOUR DISCOVERY PICKS";
    $("adaptiveStepLabel").textContent = `${data.count || 0} matches`;
    $("adaptiveQuestion").textContent = "Three different ways to discover your next movie";
    $("adaptiveSubtitle").textContent = data.notice || "Recommendations are ranked from your answers.";
    $("adaptiveOptions").replaceChildren();
    $("adaptiveMessage").textContent = data.count < 3 ? "We found fewer than three strong matches. We haven't filled the list with weak suggestions." : "Save a movie or tell MoodFlix what you think.";
    (data.recommendations || []).forEach((movie) => {
      const card = document.createElement("article");
      card.className = "movie";
      const img = document.createElement("img"); img.className = "poster"; img.alt = `${movie.title} poster`; img.loading = "lazy";
      if (movie.poster && /^https:\/\//.test(movie.poster)) img.src = movie.poster;
      img.onerror = () => img.removeAttribute("src");
      const body = document.createElement("div");
      const title = document.createElement("h3"); title.textContent = `${movie.recommendation_role || "Recommended"} · ${movie.title}`;
      const meta = document.createElement("p"); meta.className = "meta"; meta.textContent = `${movie.year || "Year unknown"} · ${(movie.languages || []).join(", ") || "Language unknown"}`;
      const plot = document.createElement("p"); plot.textContent = movie.plot || "No synopsis available.";
      body.append(title, meta, plot);
      const dub = document.createElement("p"); dub.className = "meta";
      dub.textContent = "Hindi audio/dubbing: Information currently unavailable (not verified)";
      body.appendChild(dub);
      const ottHeading = document.createElement("p"); ottHeading.className = "meta"; ottHeading.textContent = "Where to Watch (India)";
      body.appendChild(ottHeading);
      const ott = Array.isArray(movie.ott_availability) ? movie.ott_availability : [];
      if (ott.length) {
        ott.forEach((provider) => {
          const line = document.createElement("p"); line.className = "meta";
          const name = provider.platform || provider.provider || provider.name || "Streaming provider";
          const type = provider.availability_label || provider.availability || provider.type || "Availability";
          const url = provider.url || provider.web_url;
          if (url && /^https?:\/\//i.test(url)) { const link = document.createElement("a"); link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = `${name} · ${type}`; line.appendChild(link); }
          else line.textContent = `${name} · ${type}`;
          body.appendChild(line);
        });
      } else { const none = document.createElement("p"); none.className = "meta"; none.textContent = "Information currently unavailable"; body.appendChild(none); }
      const actions = document.createElement("div"); actions.className = "mode-actions";
      [["Watchlist", () => saveMovie(movie, "watchlist")], ["Watched", () => saveMovie(movie, "watched")], ["Like", () => sendFeedback(movie, "like")], ["Dislike", () => sendFeedback(movie, "dislike")], ["Not interested", () => sendFeedback(movie, "not_interested")]].forEach(([label, action]) => {
        const button = document.createElement("button"); button.type = "button"; button.textContent = label; button.addEventListener("click", action); actions.appendChild(button);
      });
      body.appendChild(actions); card.append(img, body); section.appendChild(card);
    });
    const restart = document.createElement("button"); restart.type = "button"; restart.className = "btn primary mode-restart"; restart.textContent = "Try another mode"; restart.style.marginTop = "18px"; restart.addEventListener("click", showMyTaste);
    section.appendChild(restart);
  }

  async function saveMovie(movie, status) {
    const response = await fetch("/api/library", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ movie, status }) });
    const data = await response.json();
    if (response.status === 401) location.href = "/login";
    else $("adaptiveMessage").textContent = response.ok ? `${movie.title} saved as ${status}.` : (data.error || "Could not save movie.");
  }

  async function sendFeedback(movie, feedback) {
    const response = await fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ movie, feedback }) });
    const data = await response.json();
    if (response.status === 401) location.href = "/login";
    else $("adaptiveMessage").textContent = response.ok ? `Feedback saved: ${feedback}.` : (data.error || "Could not save feedback.");
  }

  $("myTasteMode").addEventListener("click", showMyTaste);
  $("surpriseMode").addEventListener("click", () => startMode("surprise_me"));
  $("todayMoodMode").addEventListener("click", () => startMode("today_mood"));
  $("backToModes").addEventListener("click", showMyTaste);
})();
