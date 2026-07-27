const textInput = document.querySelector("#textInput");
const wordCountEl = document.querySelector("#wordCount");
const charCountEl = document.querySelector("#charCount");
const fitButton = document.querySelector("#fitButton");
const statusLine = document.querySelector("#statusLine");
const directionPill = document.querySelector("#directionPill");
const manualDirectionToggle = document.querySelector("#manualDirectionToggle");
const directionOptions = document.querySelectorAll(".direction-option");
const lengthenNotesPanel = document.querySelector("#lengthenNotesPanel");
const lengthenNotes = document.querySelector("#lengthenNotes");
const activityPanel = document.querySelector("#activityPanel");
const activityLabel = document.querySelector("#activityLabel");
const revisionCounter = document.querySelector("#revisionCounter");
const activityStream = document.querySelector("#activityStream");
const revisionSummaryList = document.querySelector("#revisionSummaryList");
const toast = document.querySelector("#toast");

const fields = {
  min_words: document.querySelector("#minWords"),
  max_words: document.querySelector("#maxWords"),
  min_chars: document.querySelector("#minChars"),
  max_chars: document.querySelector("#maxChars"),
};

const activityMessages = [
  "Reading the target range.",
  "Drafting a fitted revision.",
  "Checking counts with Python.",
  "Sending checker feedback to the writer.",
  "Preparing the revision summary.",
];

let loadingDotsTimer = null;
let activityTimer = null;
let activityMessageIndex = 0;
let activityLetterIndex = 0;
let currentActivityLine = null;
let toastTimer = null;
let manualDirection = "shorten";

function countWords(text) {
  const trimmed = text.trim();
  return trimmed === "" ? 0 : trimmed.split(/\s+/).length;
}

function countChars(text) {
  return text.length;
}

function readOptionalInt(input) {
  return input.value === "" ? null : Number.parseInt(input.value, 10);
}

function getConstraints() {
  return {
    min_words: fields.min_words.value === "" ? 1 : readOptionalInt(fields.min_words),
    max_words: readOptionalInt(fields.max_words),
    min_chars: fields.min_chars.value === "" ? 1 : readOptionalInt(fields.min_chars),
    max_chars: readOptionalInt(fields.max_chars),
  };
}

function detectDirection() {
  const constraints = getConstraints();
  const words = countWords(textInput.value);
  const chars = countChars(textInput.value);

  if ((constraints.max_words !== null && words > constraints.max_words) || (constraints.max_chars !== null && chars > constraints.max_chars)) {
    return "shorten";
  }

  if ((constraints.min_words !== null && words < constraints.min_words) || (constraints.min_chars !== null && chars < constraints.min_chars)) {
    return "lengthen";
  }

  return "fit";
}

function getEffectiveDirection() {
  const direction = detectDirection();
  return direction === "fit" ? manualDirection : direction;
}

function updateCounts() {
  wordCountEl.textContent = countWords(textInput.value);
  charCountEl.textContent = countChars(textInput.value);
  const direction = detectDirection();
  directionPill.textContent = `Auto: ${direction}`;
  manualDirectionToggle.hidden = direction !== "fit";
  lengthenNotesPanel.hidden = getEffectiveDirection() !== "lengthen";
  statusLine.className = "status";
}

function updateManualDirectionButtons() {
  directionOptions.forEach((button) => {
    const isActive = button.dataset.direction === manualDirection;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function validateConstraints(constraints) {
  if (constraints.min_words !== null && constraints.max_words !== null && constraints.min_words > constraints.max_words) {
    return "Min words cannot be greater than max words.";
  }
  if (constraints.min_chars !== null && constraints.max_chars !== null && constraints.min_chars > constraints.max_chars) {
    return "Min characters cannot be greater than max characters.";
  }
  return "";
}

function renderRevisionSummary(items) {
  activityPanel.hidden = false;
  activityLabel.textContent = "Revision summary";
  activityStream.textContent = "";
  activityStream.hidden = true;
  revisionSummaryList.innerHTML = "";

  if (!Array.isArray(items) || items.length === 0) {
    activityPanel.hidden = true;
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    revisionSummaryList.append(li);
  });
}

function startLoadingState() {
  textInput.disabled = true;
  textInput.closest(".editor-panel").classList.add("is-fitting");
  fitButton.disabled = true;
  statusLine.className = "status";
  statusLine.textContent = "TextFitAI is revising against your exact target.";

  let dotCount = 1;
  fitButton.textContent = "Fitting text.";
  loadingDotsTimer = window.setInterval(() => {
    dotCount = dotCount === 3 ? 1 : dotCount + 1;
    fitButton.textContent = `Fitting text${".".repeat(dotCount)}`;
  }, 420);

  activityPanel.hidden = false;
  activityLabel.textContent = "AI activity";
  activityStream.hidden = false;
  revisionSummaryList.innerHTML = "";
  activityMessageIndex = 0;
  activityLetterIndex = 0;
  currentActivityLine = createActivityLine();
  revisionCounter.textContent = "Revision 1/4";
  activityStream.textContent = "";
  activityStream.append(currentActivityLine);

  activityTimer = window.setInterval(streamActivityLetter, 42);
}

function stopLoadingState() {
  window.clearInterval(loadingDotsTimer);
  window.clearInterval(activityTimer);
  loadingDotsTimer = null;
  activityTimer = null;
  currentActivityLine = null;

  textInput.disabled = false;
  textInput.closest(".editor-panel").classList.remove("is-fitting");
  fitButton.disabled = false;
  fitButton.textContent = "Fit Text";
}

function streamActivityLetter() {
  const message = activityMessages[activityMessageIndex];
  const revisionNumber = Math.min(activityMessageIndex + 1, 4);
  revisionCounter.textContent = `Revision ${revisionNumber}/4`;

  if (activityLetterIndex <= message.length) {
    currentActivityLine.textContent = message.slice(0, activityLetterIndex);
    activityStream.scrollTop = activityStream.scrollHeight;
    activityLetterIndex += 1;
    return;
  }

  activityLetterIndex = 0;
  activityMessageIndex = (activityMessageIndex + 1) % activityMessages.length;
  currentActivityLine.classList.remove("is-streaming");
  currentActivityLine = createActivityLine();
  activityStream.append(currentActivityLine);
  activityStream.scrollTop = activityStream.scrollHeight;
}

function createActivityLine() {
  const line = document.createElement("p");
  line.className = "activity-line is-streaming";
  return line;
}

function showCompletionToast(direction, metTarget) {
  const action = {
    shorten: "Shortening complete",
    lengthen: "Expansion complete",
    fit: "Fit complete",
  }[direction] || "Fit complete";

  toast.textContent = metTarget ? action : "Closest fit returned";
  toast.hidden = false;
  toast.classList.add("is-visible");

  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
    window.setTimeout(() => {
      toast.hidden = true;
    }, 220);
  }, 3200);
}

textInput.addEventListener("input", updateCounts);
Object.values(fields).forEach((field) => field.addEventListener("input", updateCounts));
directionOptions.forEach((button) => {
  button.addEventListener("click", () => {
    manualDirection = button.dataset.direction;
    updateManualDirectionButtons();
    updateCounts();
  });
});

fitButton.addEventListener("click", async () => {
  const text = textInput.value;
  const constraints = getConstraints();
  const validationMessage = validateConstraints(constraints);
  const autoDirection = detectDirection();
  const startingDirection = getEffectiveDirection();
  const directionOverride = autoDirection === "fit" ? startingDirection : null;
  const expansionNotes = parseExpansionNotes();

  if (text.trim() === "") {
    statusLine.className = "status error";
    statusLine.textContent = "Add text before fitting.";
    return;
  }

  if (validationMessage) {
    statusLine.className = "status error";
    statusLine.textContent = validationMessage;
    return;
  }

  startLoadingState();

  try {
    const response = await fetch("/fit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        ...constraints,
        direction_override: directionOverride,
        expansion_notes: expansionNotes,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Fit request failed.");
    }

    textInput.value = data.result;
    updateCounts();
    revisionCounter.textContent = `${data.attempts} revision${data.attempts === 1 ? "" : "s"}`;
    renderRevisionSummary(data.revision_summary);
    showCompletionToast(startingDirection, data.met_target);
    statusLine.className = data.met_target ? "status" : "status error";
    statusLine.textContent = `${data.met_target ? "Target met" : "Closest result returned"} after ${data.attempts} attempt${data.attempts === 1 ? "" : "s"}: ${data.word_count} words, ${data.char_count} chars.`;
  } catch (error) {
    statusLine.className = "status error";
    statusLine.textContent = error.message;
    activityPanel.hidden = true;
  } finally {
    stopLoadingState();
  }
});

function parseExpansionNotes() {
  if (getEffectiveDirection() !== "lengthen") {
    return [];
  }

  return lengthenNotes.value
    .split("\n")
    .map((note) => note.replace(/^\s*[-*•]\s*/, "").trim())
    .filter(Boolean);
}

updateManualDirectionButtons();
updateCounts();
