# Contributing to TextFitAI

Thanks for helping improve TextFitAI. This project is a bring-your-own-key AI text fitting app, so the most important contribution rule is simple: never include private text, API keys, passwords, billing details, or other secrets in issues, pull requests, screenshots, logs, or commits.

The issue and pull request workflow in this repository was inspired by the issue templates from [TheBoredTeam/boring.notch](https://github.com/TheBoredTeam/boring.notch/tree/main/.github/ISSUE_TEMPLATE). Credit and thanks to the Boring Notch developers for that structure.

## Reporting Bugs

Use the [bug report form](https://github.com/srihas115/TextFitAI/issues/new?template=bug_report.yml) when something does not work the way it should.

Good bug reports are written for humans first. You do not need to be technical. The form asks for:

- What went wrong.
- What you were trying to do.
- What you expected to happen.
- What happened instead.
- Where you noticed the problem.
- What word or character limits you entered.

Optional details are still helpful if you know them:

- A short example text that causes the problem. Use made-up text if your real text is private.
- A screenshot or copied error message.
- The browser you used, such as Chrome, Safari, Firefox, or Edge.
- Whether you used TextFitAI on your own computer or on a website.
- The AI provider, if you set it up yourself. This is the value of `AI_PROVIDER` in `backend/.env`, such as `nvidia` or `anthropic`.

Before submitting, remove API keys, private writing, names, passwords, and billing details.

## Requesting Features

Use the [feature request form](https://github.com/srihas115/TextFitAI/issues/new?template=1-feature-request-form.yml) when you have an idea for a new feature or improvement.

A useful feature request explains:

- The problem or frustration.
- The behavior you would like TextFitAI to have.
- Who would benefit from the feature.
- Any mockups, screenshots, examples, or related apps that make the idea clearer.

Please search [existing issues](https://github.com/srihas115/TextFitAI/issues) before opening a new request so duplicate ideas can stay in one discussion.

## Working on Code

Do day-to-day work on the `development` branch. The `main` branch is the production branch watched by Vercel, so changes should only reach `main` intentionally.

TextFitAI has a small structure:

- `backend/` contains the FastAPI app, provider calls, fitting logic, and tests.
- `frontend/` contains the plain HTML, CSS, and JavaScript UI.
- `api/` contains the Vercel entrypoint.

Keep these project rules in mind:

- Do not commit `backend/.env` or real API keys.
- Update `backend/.env.example` if you add a required environment variable.
- Keep the app stateless unless an issue or PR explicitly discusses persistence.
- Preserve the shared counting contract: words use `len(text.split())`, characters use `len(text)`.
- Keep frontend and backend counts in agreement.
- Avoid logging user text or provider secrets.

## Testing Changes

Run the checks that match the files you changed.

For backend fitting/counting changes:

```bash
cd backend
python -m pytest
```

For a manual app check:

```bash
cd backend
uvicorn main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

For provider behavior, you need a local `backend/.env` with your own `NVIDIA_API_KEY` or `ANTHROPIC_API_KEY`. Do not share that file.

## Opening Pull Requests

Before opening a pull request:

- Make sure your PR is not a duplicate of an existing PR or issue.
- Target the `development` branch unless the maintainer asks for something else.
- Give the PR a clear title.
- Explain what changed and why.
- Link related issues with `closes #123` when appropriate.
- Include screenshots or a short screen recording for visible UI changes.
- Describe how you tested the change.
- Mention any follow-up work or known limitations.

Small, focused pull requests are easier to review than large mixed changes.
