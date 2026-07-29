## Pull Request Template

This pull request template was adapted for TextFitAI from [TheBoredTeam/boring.notch](https://github.com/TheBoredTeam/boring.notch/blob/main/.github/PULL_REQUEST.md). Credit and thanks to the Boring Notch developers.

Please go through these steps before you submit a PR.

1. Make sure that your PR is not a duplicate.
2. Make sure your PR targets the `development` branch unless the maintainer asked you to target another branch. The `main` branch is used for production deployments.
3. Make sure you have tested the code yourself and that the app still works as intended.
4. Make sure your PR does not include API keys, `.env` files, private user text, passwords, billing details, or provider secrets.
5. If you added or changed an environment variable, update `backend/.env.example`.
6. If you changed word or character counting, confirm the frontend and backend still agree.

After these steps, you are ready to open a pull request.

### Description

Describe what changed and why.

### Related Issue

Put `closes #XXXX` here if this PR fixes an issue.

### Testing

Describe how you tested this change. Examples:

- `cd backend && python -m pytest`
- `cd backend && uvicorn main:app --reload`
- Manual check in the browser at `http://127.0.0.1:8000`

### Screenshots or Screen Recording

For UI changes, include screenshots or a short screen recording.

### Checklist

- [ ] I have reviewed [CONTRIBUTING.md](../CONTRIBUTING.md).
- [ ] My PR targets `development`, unless the maintainer requested another branch.
- [ ] I tested the relevant behavior.
- [ ] I did not commit secrets, API keys, `.env` files, or private user text.
- [ ] I updated `backend/.env.example` if I added a required environment variable.
- [ ] I included screenshots or a screen recording for visible UI changes.

**PLEASE REMOVE THIS TEMPLATE BEFORE SUBMITTING**
