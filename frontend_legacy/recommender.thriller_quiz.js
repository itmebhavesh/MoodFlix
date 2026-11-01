// MoodFlix's quiz-first interface. No filter form is used on this page.
const questions = [
  { id: "thriller_type", title: "Which type of thriller do you enjoy most?", options: ["Mind-blowing twists", "Murder mystery", "Psychological thriller", "Crime investigation", "Sci-fi mystery"] },
  { id: "story_priority", title: "What matters most in a movie?", options: ["Unpredictable story", "Fast-paced entertainment", "Intelligent screenplay", "Suspense until the end", "A satisfying climax"] },
  { id: "pacing", title: "How do you feel about slow-paced movies?", options: ["Love slow-burn stories", "Okay if the payoff is great", "Prefer medium pace", "Only fast-paced movies"] },
  { id: "ending", title: "What kind of ending do you prefer?", options: ["Completely unexpected", "Clever and logical", "Emotional and satisfying", "Dark and disturbing", "Ambiguous, open to interpretation"] },
  { id: "complexity", title: "How challenging should the mystery be?", options: ["Easy and entertaining", "Some clues to solve", "Complex puzzle", "Extremely complicated; I want to think hard"] },
  { id: "atmosphere", title: "Which atmosphere do you prefer?", options: ["Realistic crime", "Dark and gritty", "Stylish and fun", "Tense and claustrophobic", "Unusual and surreal"] },
  { id: "comedy", title: "How much comedy do you want?", options: ["A lot of humor", "Some humor", "Almost none", "Depends on the story"] },
  { id: "languages", title: "Which languages should we include?", subtitle: "Choose one or more. We'll use this to personalize the movie examples in the next question.", multiple: true, options: ["Hindi", "English", "Malayalam", "Tamil", "Telugu", "Kannada", "All South Indian languages", "All languages"] },
  { id: "example_movie", title: "Which movies have impressed you most?", subtitle: "These examples change based on your language choices. Pick the closest match, or choose the last option.", options: [] },
  { id: "recommendation_style", title: "What kind of recommendations do you want?", options: ["Hidden gems nobody talks about", "Highly rated masterpieces", "Underrated thrillers", "Movies with insane twists", "A mix of everything"] }
];

const examplesByLanguage = {
  Hindi: ["Andhadhun", "Kahaani", "Talaash", "None of these / haven't watched them"],
  English: ["Gone Girl", "Shutter Island", "Prisoners", "None of these / haven't watched them"],
  Malayalam: ["Drishyam", "Memories", "Anjaam Pathiraa", "None of these / haven't watched them"],
  Tamil: ["Ratsasan", "Vikram Vedha", "Maharaja", "None of these / haven't watched them"],
  Telugu: ["Agent Sai Srinivasa Athreya", "HIT: The First Case", "Evaru", "None of these / haven't watched them"],
  Kannada: ["U Turn", "Kavaludaari", "Rangitaranga", "None of these / haven't watched them"]
};
const answers = {};
let current = 0;
let busy = false;
const $ = (id) => document.getElementById(id);

function questionOptions(question) {
  if (question.id !== "example_movie") return question.options;
  const selected = answers.languages || [];
  if (selected.includes("All languages") || selected.length === 0) {
    return [...new Set(Object.values(examplesByLanguage).flat())];
  }
  let list = [];
  selected.forEach((language) => {
    if (language === "All South Indian languages") {
      ["Malayalam", "Tamil", "Telugu", "Kannada"].forEach((lang) => list.push(...examplesByLanguage[lang]));
    } else if (examplesByLanguage[language]) list.push(...examplesByLanguage[language]);
  });
  return [...new Set(list)];
}

function selectedValues(question) {
  return question.multiple ? (answers[question.id] || []) : (answers[question.id] ? [answers[question.id]] : []);
}

function renderQuestion() {
  const q = questions[current];
  const options = questionOptions(q);
  $("stepLabel").textContent = `QUESTION ${current + 1} OF ${questions.length}`;
  $("percentLabel").textContent = `${Math.round(((current + 1) / questions.length) * 100)}%`;
  $("progressBar").style.width = `${((current + 1) / questions.length) * 100}%`;
  $("questionTitle").textContent = q.title;
  $("questionSub").textContent = q.subtitle || "Choose the answer that best matches your taste.";
  $("questionHint").textContent = q.multiple ? "Select all languages you are happy to watch." : "Choose one answer to continue.";
  $("options").replaceChildren();
  const selected = selectedValues(q);
  options.forEach((label) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `option${selected.includes(label) ? " selected" : ""}`;
    button.textContent = label;
    button.setAttribute("aria-pressed", String(selected.includes(label)));
    button.addEventListener("click", () => chooseAnswer(q, label));
    $("options").appendChild(button);
  });
  $("backBtn").disabled = current === 0 || busy;
  $("nextBtn").disabled = selected.length === 0 || busy;
  $("nextBtn").textContent = current === questions.length - 1 ? "Find my movies →" : "Continue →";
}

function chooseAnswer(question, value) {
  if (busy) return;
  if (question.multiple) {
    const currentValues = answers[question.id] || [];
    const isAll = value === "All languages";
    const isSouthAll = value === "All South Indian languages";
    if (currentValues.includes(value)) answers[question.id] = currentValues.filter((item) => item !== value);
    else if (isAll) answers[question.id] = ["All languages"];
    else if (isSouthAll) answers[question.id] = [...new Set([...currentValues.filter(x => x !== "All languages"), value])];
    else answers[question.id] = [...new Set([...currentValues.filter(x => x !== "All languages"), value])];
    if (answers[question.id].includes("All languages")) answers[question.id] = ["All languages"];
  } else {
    answers[question.id] = value;
    // If language choices change, reset the old example so an incompatible example is not submitted.
    if (question.id === "example_movie") answers.example_movie = value;
  }
  renderQuestion();
}

$("backBtn").addEventListener("click", () => { if (current > 0 && !busy) { current--; renderQuestion(); } });
$("nextBtn").addEventListener("click", async () => {
  if (busy || selectedValues(questions[current]).length === 0) return;
  if (current < questions.length - 1) {
    current++;
    // If the selected example is no longer valid after language changes, clear it.
    if (questions[current].id === "example_movie" && !questionOptions(questions[current]).includes(answers.example_movie)) delete answers.example_movie;
    renderQuestion();
  } else await submitQuiz();
});

function safeLink(url) {
  try { const parsed = new URL(url); return ["https:", "http:"].includes(parsed.protocol) ? parsed.href : ""; }
  catch { return ""; }
}

function renderResults(data) {
  $("quiz").classList.add("hidden");
  const section = $("results");
  section.classList.remove("hidden");
  section.replaceChildren();
  const heading = document.createElement("h2"); heading.textContent = "Your thriller matches"; section.appendChild(heading);
  const intro = document.createElement("p"); intro.className = "sub"; intro.textContent = `We ranked ${data.count || 0} movies using your answers.`; section.appendChild(intro);
  if (data.notice) { const notice = document.createElement("div"); notice.className = "notice"; notice.textContent = data.notice; section.appendChild(notice); }
  if (!data.recommendations || !data.recommendations.length) { const empty = document.createElement("p"); empty.className = "empty"; empty.textContent = "No matches in the current catalog. The global movie catalog needs to be connected to expand your choices."; section.appendChild(empty); }
  (data.recommendations || []).forEach((movie, index) => {
    const card = document.createElement("article"); card.className = "movie";
    const img = document.createElement("img"); img.className = "poster"; img.alt = `${movie.title} poster`; img.loading = "lazy";
    img.src = safeLink(movie.poster || "") || ""; img.onerror = () => { img.removeAttribute("src"); img.alt = "Poster unavailable"; };
    const body = document.createElement("div"); const title = document.createElement("h3"); title.textContent = `${index === 0 ? "★ Top match · " : ""}${movie.title}`;
    const meta = document.createElement("p"); meta.className = "meta"; meta.textContent = `${movie.year || movie.release_year || "Year unknown"} · ${(movie.languages || [movie.language || "Language unknown"]).join(", ")} · ${movie.country || movie.industry || ""}${movie.imdb_rating ? ` · IMDb ${movie.imdb_rating}/10` : ""}`;
    const why = document.createElement("p"); why.textContent = movie.why || "Matched your preferences.";
    body.append(title, meta, why);
    if (movie.plot) { const plot = document.createElement("p"); plot.textContent = movie.plot; body.appendChild(plot); }
    const imdbId = movie.imdb_id;
    if (imdbId && /^tt\d+$/.test(imdbId)) { const a = document.createElement("a"); a.href = `https://www.imdb.com/title/${imdbId}/`; a.target = "_blank"; a.rel = "noopener noreferrer"; a.textContent = "View on IMDb"; body.appendChild(a); }
    card.append(img, body); section.appendChild(card);
  });
  const restart = document.createElement("button"); restart.type = "button"; restart.className = "btn primary"; restart.textContent = "Take the quiz again"; restart.style.marginTop = "20px";
  restart.addEventListener("click", () => { Object.keys(answers).forEach(k => delete answers[k]); current = 0; section.classList.add("hidden"); $("quiz").classList.remove("hidden"); renderQuestion(); });
  section.appendChild(restart);
}

async function submitQuiz() {
  busy = true; $("nextBtn").disabled = true; $("nextBtn").textContent = "Finding matches…";
  $("questionHint").textContent = "Matching your preferences to the available catalog…";
  try {
    const response = await fetch("/api/thriller-quiz/recommend", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answers }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not generate recommendations.");
    renderResults(data);
  } catch (error) {
    $("questionHint").textContent = `Something went wrong: ${error.message}. Please try again.`;
    $("nextBtn").textContent = "Try again";
  } finally { busy = false; if (!$ ("quiz").classList.contains("hidden")) renderQuestion(); }
}

renderQuestion();
