---
name: github-login
description: Log into github.com in the running Chrome browser using Playwright over CDP, including TOTP two-factor. Use when browser-based GitHub access is needed (UI pages that the API cannot cover).
---

# GitHub browser login

Logs into github.com inside the already-running Chrome instance, so the session
persists in the browser profile for later manual or scripted browsing.

## Prerequisites

```bash
pip install playwright pyotp
```

Environment variables (use existing secrets, never hardcode):

| Variable | Required | Purpose |
| --- | --- | --- |
| `GITHUB_USERNAME` | yes | username or email |
| `GITHUB_PASSWORD` | yes | password |
| `_2FA_GITHUB` | only if 2FA is enabled | base32 TOTP secret |
| `CDP_URL` | no | defaults to `http://localhost:29229` |

## Run

```bash
python3 .agents/skills/github-login/github_login.py
```

The script is idempotent: if the profile is already authenticated it prints the
logged-in user and exits without touching the login form.

## Notes

- Attaches to the existing Chrome via CDP; it never launches a new browser, so
  the Devin browser profile and its cookies are preserved.
- Prefer `gh` CLI / the REST API with a token for anything scriptable; use this
  only for flows that require the web UI.
- If GitHub asks for a device-verification code sent by email, the script stops
  with an error — that step needs a human.
