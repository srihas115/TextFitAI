const textInput = document.querySelector("#textInput");
const wordCountEl = document.querySelector("#wordCount");
const charCountEl = document.querySelector("#charCount");
const fitButton = document.querySelector("#fitButton");
const statusLine = document.querySelector("#statusLine");
const directionPill = document.querySelector("#directionPill");
const wordTargetSummary = document.querySelector("#wordTargetSummary");
const charTargetSummary = document.querySelector("#charTargetSummary");

const fields = {
  min_words: document.querySelector("#minWords"),
  max_words: document.querySelector("#maxWords"),
  min_chars: document.querySelector("#minChars"),
  max_chars: document.querySelector("#maxChars"),
};

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
    min_words: readOptionalInt(fields.min_words),
    max_words: readOptionalInt(fields.max_words),
    min_chars: readOptionalInt(fields.min_chars),
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

function updateCounts() {
  const constraints = getConstraints();
  wordCountEl.textContent = countWords(textInput.value);
  charCountEl.textContent = countChars(textInput.value);
  const direction = detectDirection();
  directionPill.textContent = `Auto: ${direction}`;
  wordTargetSummary.textContent = formatRange(constraints.min_words, constraints.max_words);
  charTargetSummary.textContent = formatRange(constraints.min_chars, constraints.max_chars);
  statusLine.className = "status";
}

function formatRange(min, max) {
  if (min === null && max === null) {
    return "No limit";
  }
  if (min !== null && max !== null) {
    return `${min} to ${max}`;
  }
  if (min !== null) {
    return `At least ${min}`;
  }
  return `At most ${max}`;
}

function validateConstraints(constraints) {
  if (constraints.min_words !== null && constraints.max_words !== null && constraints.min_words > constraints.max_words) {
    return "Min words cannot be greater than max words.";
  }
  if (constraints.min_chars !== null && constraints.max_chars !== null && constraints.min_chars > constraints.max_chars) {
    return "Min chars cannot be greater than max chars.";
  }
  return "";
}

textInput.addEventListener("input", updateCounts);
Object.values(fields).forEach((field) => field.addEventListener("input", updateCounts));

fitButton.addEventListener("click", async () => {
  const text = textInput.value;
  const constraints = getConstraints();
  const validationMessage = validateConstraints(constraints);

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

  fitButton.disabled = true;
  fitButton.textContent = "Fitting...";
  statusLine.className = "status";
  statusLine.textContent = "TextFitAI is revising against your exact target.";

  try {
    const response = await fetch("/fit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, ...constraints }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Fit request failed.");
    }

    textInput.value = data.result;
    updateCounts();
    statusLine.className = data.met_target ? "status" : "status error";
    statusLine.textContent = `${data.met_target ? "Target met" : "Closest result returned"} after ${data.attempts} attempt${data.attempts === 1 ? "" : "s"}: ${data.word_count} words, ${data.char_count} chars.`;
  } catch (error) {
    statusLine.className = "status error";
    statusLine.textContent = error.message;
  } finally {
    fitButton.disabled = false;
    fitButton.textContent = "Fit Text";
  }
});

updateCounts();
