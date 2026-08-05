const textInput = document.querySelector("#textInput");
const wordCountEl = document.querySelector("#wordCount");
const charCountEl = document.querySelector("#charCount");
const fitButton = document.querySelector("#fitButton");
const statusLine = document.querySelector("#statusLine");
const directionPill = document.querySelector("#directionPill");
const directionWord = document.querySelector("#directionWord");
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
const welcomeOverlay = document.querySelector("#welcomeOverlay");
const welcomeDismissButton = document.querySelector("#welcomeDismissButton");
const themeToggle = document.querySelector("#themeToggle");
const themeColorMeta = document.querySelector('meta[name="theme-color"]');
const accentPicker = document.querySelector(".accent-picker");
const accentMenuButton = document.querySelector("#accentMenuButton");
const accentMenu = document.querySelector("#accentMenu");
const accentOptions = document.querySelectorAll(".accent-option");
const customAccentOption = document.querySelector(".custom-accent-option");
const customAccentInput = document.querySelector("#customAccentInput");

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
let directionAnimationTimer = null;
let manualDirection = "shorten";
let currentDirectionLabel = "";
let activeActivityMessages = activityMessages;
const visibilityTimers = new WeakMap();
const welcomeStorageKey = "textfitai-welcome-seen";
const themeStorageKey = "textfitai-theme";
const accentStorageKey = "textfitai-accent";
const customAccentStorageKey = "textfitai-custom-accent";
const defaultAccent = "silver";
const defaultCustomAccent = "#a1a1aa";
const darkThemeColor = "#101010";
const lightThemeColor = "#fafaf9";
const minDarkThemeAccentLuminance = 0.28;
const maxLightThemeAccentLuminance = 0.62;

function countWords(text) {
  const trimmed = text.trim();
  return trimmed === "" ? 0 : trimmed.split(/\s+/).length;
}

function hasSeenWelcome() {
  try {
    return window.localStorage.getItem(welcomeStorageKey) === "true";
  } catch {
    return false;
  }
}

function markWelcomeSeen() {
  try {
    window.localStorage.setItem(welcomeStorageKey, "true");
  } catch {
    // The popup can still be dismissed if localStorage is unavailable.
  }
}

function getStoredTheme() {
  try {
    return window.localStorage.getItem(themeStorageKey);
  } catch {
    return null;
  }
}

function getPreferredTheme() {
  const storedTheme = getStoredTheme();
  if (storedTheme === "dark" || storedTheme === "light") {
    return storedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.documentElement.dataset.theme = theme;
  themeToggle.setAttribute("aria-pressed", String(isDark));
  themeToggle.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} mode`);

  if (themeColorMeta) {
    themeColorMeta.setAttribute("content", isDark ? darkThemeColor : lightThemeColor);
  }

  applyCustomAccent(customAccentInput.value || defaultCustomAccent);
}

function saveTheme(theme) {
  try {
    window.localStorage.setItem(themeStorageKey, theme);
  } catch {
    // Theme switching still works for the current page if localStorage is unavailable.
  }
}

function toggleTheme() {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(nextTheme);
  saveTheme(nextTheme);
}

function getStoredAccent() {
  try {
    return window.localStorage.getItem(accentStorageKey);
  } catch {
    return null;
  }
}

function getPreferredAccent() {
  const storedAccent = getStoredAccent();
  const accentNames = [...Array.from(accentOptions).map((option) => option.dataset.accent), "custom"];

  return accentNames.includes(storedAccent) ? storedAccent : defaultAccent;
}

function applyAccent(accent) {
  document.documentElement.dataset.accent = accent;
  accentMenuButton.setAttribute("aria-label", `Choose accent color, current ${accent}`);
  customAccentOption.classList.toggle("is-active", accent === "custom");

  accentOptions.forEach((option) => {
    const isActive = option.dataset.accent === accent;
    option.classList.toggle("is-active", isActive);
    option.setAttribute("aria-checked", String(isActive));
  });
}

function saveAccent(accent) {
  try {
    window.localStorage.setItem(accentStorageKey, accent);
  } catch {
    // Accent switching still works for the current page if localStorage is unavailable.
  }
}

function selectAccent(accent) {
  applyAccent(accent);
  saveAccent(accent);
  closeAccentMenu();
}

function getStoredCustomAccent() {
  try {
    return window.localStorage.getItem(customAccentStorageKey);
  } catch {
    return null;
  }
}

function saveCustomAccent(color) {
  try {
    window.localStorage.setItem(customAccentStorageKey, color);
  } catch {
    // Custom accent still works for the current page if localStorage is unavailable.
  }
}

function applyCustomAccent(color) {
  const safeColor = /^#[0-9a-f]{6}$/i.test(color) ? color : defaultCustomAccent;
  const cappedColor = capCustomAccentForTheme(safeColor, document.documentElement.dataset.theme);
  const contrastColor = getReadableTextColor(cappedColor);
  document.documentElement.style.setProperty("--custom-accent", safeColor);
  document.documentElement.style.setProperty("--custom-accent-safe", cappedColor);
  document.documentElement.style.setProperty("--custom-accent-contrast", contrastColor);
  customAccentInput.value = safeColor;
}

function capCustomAccentForTheme(color, theme) {
  const rgb = hexToRgb(color);
  const luminance = getRelativeLuminance(rgb);

  if (theme === "dark" && luminance < minDarkThemeAccentLuminance) {
    return mixUntilLuminance(rgb, [255, 255, 255], minDarkThemeAccentLuminance, "min");
  }

  if (theme !== "dark" && luminance > maxLightThemeAccentLuminance) {
    return mixUntilLuminance(rgb, [0, 0, 0], maxLightThemeAccentLuminance, "max");
  }

  return color;
}

function getReadableTextColor(backgroundColor) {
  const luminance = getRelativeLuminance(hexToRgb(backgroundColor));
  const whiteContrast = (1.05) / (luminance + 0.05);
  const blackContrast = (luminance + 0.05) / 0.05;

  return blackContrast >= whiteContrast ? "#111111" : "#ffffff";
}

function mixUntilLuminance(startRgb, targetRgb, limit, mode) {
  let bestRgb = startRgb;

  for (let amount = 0; amount <= 1; amount += 0.02) {
    const mixedRgb = startRgb.map((channel, index) => Math.round(channel + (targetRgb[index] - channel) * amount));
    const luminance = getRelativeLuminance(mixedRgb);
    bestRgb = mixedRgb;

    if ((mode === "min" && luminance >= limit) || (mode === "max" && luminance <= limit)) {
      break;
    }
  }

  return rgbToHex(bestRgb);
}

function hexToRgb(color) {
  const normalized = color.replace("#", "");
  return [0, 2, 4].map((start) => Number.parseInt(normalized.slice(start, start + 2), 16));
}

function rgbToHex(rgb) {
  return `#${rgb.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
}

function getRelativeLuminance(rgb) {
  const [red, green, blue] = rgb.map((channel) => {
    const value = channel / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });

  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function openAccentMenu() {
  accentMenu.hidden = false;
  accentMenuButton.setAttribute("aria-expanded", "true");
}

function closeAccentMenu() {
  accentMenu.hidden = true;
  accentMenuButton.setAttribute("aria-expanded", "false");
}

function toggleAccentMenu() {
  if (accentMenu.hidden) {
    openAccentMenu();
    return;
  }

  closeAccentMenu();
}

function showWelcomeIfNeeded() {
  if (hasSeenWelcome()) {
    return;
  }

  welcomeOverlay.hidden = false;
  welcomeDismissButton.focus();
}

function dismissWelcome() {
  markWelcomeSeen();
  welcomeOverlay.hidden = true;
  textInput.focus();
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

function hasAnyConstraint(constraints) {
  return Object.values(constraints).some((value) => value !== null);
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
  updateDirectionDisplay(direction);
  setAnimatedVisibility(directionPill, direction !== "fit");
  setAnimatedVisibility(manualDirectionToggle, direction === "fit");
  setAnimatedVisibility(lengthenNotesPanel, getEffectiveDirection() === "lengthen");
  statusLine.className = "status";
}

function updateDirectionDisplay(direction) {
  const nextLabel = formatDirectionStatus(direction);
  directionPill.setAttribute("aria-label", nextLabel || "Manual direction");

  if (nextLabel === "") {
    currentDirectionLabel = "";
    directionWord.textContent = "";
    directionWord.classList.remove("is-changing");
    window.clearTimeout(directionAnimationTimer);
    return;
  }

  if (nextLabel === currentDirectionLabel) {
    return;
  }

  window.clearTimeout(directionAnimationTimer);

  if (currentDirectionLabel === "") {
    directionWord.textContent = nextLabel;
    currentDirectionLabel = nextLabel;
    return;
  }

  directionWord.classList.add("is-changing");
  directionAnimationTimer = window.setTimeout(() => {
    directionWord.textContent = nextLabel;
    currentDirectionLabel = nextLabel;
    window.requestAnimationFrame(() => {
      directionWord.classList.remove("is-changing");
    });
  }, 120);
}

function formatDirectionStatus(direction) {
  const labels = {
    shorten: "Shortening to range",
    lengthen: "Lengthening to range",
    fit: "",
  };

  return labels[direction] || "";
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

function startLoadingState(expansionNotes, isOneWordSummary) {
  textInput.disabled = true;
  textInput.closest(".editor-panel").classList.add("is-fitting");
  fitButton.disabled = true;
  statusLine.className = "status";
  statusLine.textContent = isOneWordSummary
    ? "TextFitAI is distilling your text into one word."
    : "TextFitAI is revising against your exact target.";

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
  activeActivityMessages = getActivityMessages(expansionNotes, isOneWordSummary);
  activityMessageIndex = 0;
  activityLetterIndex = 0;
  currentActivityLine = createActivityLine();
  revisionCounter.textContent = isOneWordSummary ? "One-word mode" : "Revision 1/4";
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
  const message = activeActivityMessages[activityMessageIndex];
  if (activeActivityMessages === oneWordActivityMessages) {
    revisionCounter.textContent = "One-word mode";
  } else {
    const revisionNumber = Math.min(activityMessageIndex + 1, 4);
    revisionCounter.textContent = `Revision ${revisionNumber}/4`;
  }

  if (activityLetterIndex <= message.length) {
    currentActivityLine.textContent = message.slice(0, activityLetterIndex);
    activityStream.scrollTop = activityStream.scrollHeight;
    activityLetterIndex += 1;
    return;
  }

  activityLetterIndex = 0;
  activityMessageIndex = (activityMessageIndex + 1) % activeActivityMessages.length;
  currentActivityLine.classList.remove("is-streaming");
  currentActivityLine = createActivityLine();
  activityStream.append(currentActivityLine);
  activityStream.scrollTop = activityStream.scrollHeight;
}

const oneWordActivityMessages = [
  "Unlocking one-word mode.",
  "Finding the core idea.",
  "Returning a single word.",
];

function getActivityMessages(expansionNotes, isOneWordSummary) {
  if (isOneWordSummary) {
    return oneWordActivityMessages;
  }

  if (!Array.isArray(expansionNotes) || expansionNotes.length === 0) {
    return activityMessages;
  }

  return [
    "Reading the target range.",
    "Reading details to add.",
    "Interpreting details.",
    "Drafting a fitted revision.",
    "Checking counts with Python.",
    "Sending checker feedback to the writer.",
    "Preparing the revision summary.",
  ];
}

function createActivityLine() {
  const line = document.createElement("p");
  line.className = "activity-line is-streaming";
  return line;
}

function setAnimatedVisibility(element, shouldShow) {
  const existingTimer = visibilityTimers.get(element);
  if (existingTimer) {
    window.clearTimeout(existingTimer);
  }

  if (shouldShow) {
    element.hidden = false;
    window.requestAnimationFrame(() => {
      element.classList.add("is-visible");
    });
    return;
  }

  element.classList.remove("is-visible");
  const timer = window.setTimeout(() => {
    element.hidden = true;
    visibilityTimers.delete(element);
  }, 260);
  visibilityTimers.set(element, timer);
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
welcomeDismissButton.addEventListener("click", dismissWelcome);
themeToggle.addEventListener("click", toggleTheme);
accentMenuButton.addEventListener("click", toggleAccentMenu);
accentOptions.forEach((option) => {
  option.addEventListener("click", () => {
    selectAccent(option.dataset.accent);
  });
});
customAccentInput.addEventListener("input", () => {
  applyCustomAccent(customAccentInput.value);
  saveCustomAccent(customAccentInput.value);
  applyAccent("custom");
  saveAccent("custom");
});
document.addEventListener("click", (event) => {
  if (!accentPicker.contains(event.target)) {
    closeAccentMenu();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeAccentMenu();
    accentMenuButton.focus();
  }
});

fitButton.addEventListener("click", async () => {
  const text = textInput.value;
  const constraints = getConstraints();
  const validationMessage = validateConstraints(constraints);
  const autoDirection = detectDirection();
  const startingDirection = getEffectiveDirection();
  const directionOverride = autoDirection === "fit" && hasAnyConstraint(constraints) ? startingDirection : null;
  const expansionNotes = parseExpansionNotes();
  const isOneWordSummary = constraints.min_words === 1 && constraints.max_words === 1;

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

  startLoadingState(expansionNotes, isOneWordSummary);

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
applyTheme(getPreferredTheme());
applyCustomAccent(getStoredCustomAccent() || defaultCustomAccent);
applyAccent(getPreferredAccent());
updateCounts();
showWelcomeIfNeeded();
