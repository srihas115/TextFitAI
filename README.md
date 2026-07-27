# TextFitAI

TextFitAI is a full-stack AI text editor that trims or expands user text until it lands inside an exact word-count or character-count target. It uses a FastAPI backend, Anthropic Claude through the official `anthropic` Python SDK, and a plain HTML/CSS/JavaScript frontend served by FastAPI.

The app is stateless. It stores no documents, users, sessions, or history. Every `POST /fit` request sends text plus optional constraints, asks Claude for a revision, verifies the result locally, and returns the closest valid output it can produce within four attempts.

## What TextFitAI Does

- Accepts pasted or typed text in a large editor.
- Shows live word and character counts on every keystroke.
- Lets you set any combination of optional limits:
  - minimum words
  - maximum words
  - minimum characters
  - maximum characters
- Treats blank limit fields as no constraint.
- Auto-detects whether the text should be shortened or lengthened:
  - above a max limit means shorten
  - below a min limit means lengthen
  - already inside the range means fit/preserve
- Sends the text to `POST /fit`.
- Replaces the editor text with the fitted result.
- Shows the returned word count, character count, attempt count, and whether the target was met.

## Project Structure

```text
backend/
  main.py            FastAPI app, static frontend serving, /fit endpoint
  ai_fitter.py       Claude prompt construction plus retry/verification loop
  counters.py        Shared backend source of truth for word and character counts
  requirements.txt   Python dependencies
  .env.example       Example environment variables
  .env               Local API key file, gitignored
  test_fitter.py     Small script that hits the running /fit endpoint
frontend/
  index.html         Plain HTML app shell
  style.css          Responsive editor UI
  app.js             Live counters, validation, and /fit call
README.md
.gitignore
```

## Counting Rules

TextFitAI intentionally uses simple, explicit counting rules so the frontend and backend agree:

```python
word_count = len(text.split())
char_count = len(text)
```

The backend implementation lives in `backend/counters.py`. The frontend mirrors the same behavior in `frontend/app.js`: words are counted by splitting on whitespace, and characters are counted with `text.length`.

## Backend API

### `POST /fit`

Request body:

```json
{
  "text": "Your text here.",
  "min_words": null,
  "max_words": 50,
  "min_chars": null,
  "max_chars": null
}
```

All constraint fields are optional. Send `null` or omit a target by leaving the matching frontend input blank.

Response body:

```json
{
  "result": "Revised text here.",
  "word_count": 48,
  "char_count": 278,
  "attempts": 2,
  "met_target": true
}
```

### `GET /health`

Returns:

```json
{ "status": "ok" }
```

### `GET /counts?text=...`

Returns backend counts for a piece of text. This is mainly useful while debugging count agreement.

## AI Fitting Loop

`backend/ai_fitter.py` implements the required verification loop:

1. Count the current text with `backend/counters.py`.
2. Determine the direction:
   - shorten if current words or characters exceed a max constraint
   - lengthen if current words or characters are below a min constraint
   - fit if the text is already inside the requested range
3. Build a Claude prompt containing the current count, exact target, direction, and original text.
4. Ask Claude to list 3-5 candidate cuts or additions, then output a line containing exactly `---FINAL---`.
5. Parse only the text after `---FINAL---`.
6. Count the result locally.
7. If the result misses the target, send a concise retry prompt with the specific miss, such as being 22 words over the maximum.
8. Retry up to 4 total attempts.
9. If no attempt hits the target, return the closest attempt with `"met_target": false`.

Shortening prompts tell the model to remove filler, redundant modifiers, hedging language, and throat-clearing phrases without dropping distinct claims or facts.

Lengthening prompts tell the model to add supporting detail or examples to existing points and explicitly forbid repeated sentences.

## Setup

TextFitAI is designed as a bring-your-own-key open source app. The repository does not include, share, proxy, or manage an Anthropic API key for users. Each person who runs TextFitAI locally should create their own Anthropic API key and store it in their own local `backend/.env` file.

### 1. Create and activate a virtual environment

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your Anthropic API key

Create an Anthropic API key from your Anthropic account, then add it locally. Your key stays on your machine and is read only by the FastAPI backend when it calls Claude.

Copy the example file if needed:

```bash
cp .env.example .env
```

Then edit `backend/.env`:

```env
ANTHROPIC_API_KEY=your_real_anthropic_key_here
```

Do not commit `.env`. It is covered by `.gitignore`.

For forks, contributors, and self-hosted deployments:

- Keep `backend/.env.example` committed so users know which variables are required.
- Keep real `.env` files untracked.
- Do not paste API keys into source code, issues, pull requests, screenshots, logs, or README examples.
- If you deploy TextFitAI to a server, set `ANTHROPIC_API_KEY` as a private environment variable in that hosting provider instead of committing it.
- Every user or deployment owner is responsible for their own Anthropic account, key, usage limits, and billing.

### 4. Run the app

From `backend/`:

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Running The Test Script

Start the app first from `backend/`:

```bash
uvicorn main:app --reload
```

In another terminal, with the virtual environment active:

```bash
cd backend
python test_fitter.py
```

The script sends three sample cases to `/fit`:

- a shortening case
- a lengthening case
- a tight character-range case

For each case it prints the attempt count, whether the target was met, final word count, final character count, and the returned text.

## Local Development Notes

- The frontend is served by FastAPI from `frontend/`.
- Static assets are available under `/static`.
- CORS is enabled for common local development origins.
- The app has no database and no persistent storage.
- `ANTHROPIC_MODEL` can optionally be set in `.env`; otherwise the backend uses `claude-3-5-sonnet-latest`.
- The first real `/fit` call requires `ANTHROPIC_API_KEY` to be present in `backend/.env`.

## Contributing

Contributions are welcome. Because TextFitAI is meant to remain a safe open source bring-your-own-key project, please keep API-key handling local and private in every contribution.

Before opening a pull request:

- Run the relevant syntax checks or tests for the files you changed.
- Do not commit `backend/.env` or any real credentials.
- Update `backend/.env.example` when adding a new required environment variable.
- Keep the backend stateless unless a change explicitly discusses why persistence is needed.
- Preserve the shared counting contract: words use `len(text.split())`, characters use `len(text)`.

## Troubleshooting

### `ANTHROPIC_API_KEY is not set`

Add your key to `backend/.env`:

```env
ANTHROPIC_API_KEY=your_real_anthropic_key_here
```

Restart `uvicorn` after editing environment variables.

### Counts look different from another editor

TextFitAI uses `len(text.split())` for words and `len(text)` for characters. Other editors may handle punctuation, emojis, invisible characters, or whitespace differently.

### The result says `met_target: false`

Claude did not hit the requested range within 4 total attempts. TextFitAI returns the closest attempt it saw, along with the final verified counts, so you still get the best available revision.
