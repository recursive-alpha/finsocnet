# X (Twitter) Authentication & Exploration Guide

## Authentication Setup (Optional)
While unauthenticated queries work via search fallbacks, an authenticated session enables live search (`f=live`), access to private profiles, and direct tweet threads.

### Method 1: Using `X_AUTH_TOKEN` (Recommended)
1. In your browser where you are logged in to X (x.com), open DevTools (`F12`) -> Application -> Cookies -> `https://x.com`.
2. Copy the value of the `auth_token` cookie.
3. In `.env`:
   ```env
   X_AUTH_TOKEN=your_auth_token_here
   ```
4. Run:
   ```bash
   uv run .agents/skills/x-explorer/scripts/login_x.py
   ```
   *This automatically generates `data/sessions/x_session.json`.*

### Method 2: Interactive Browser Login
```bash
uv run .agents/skills/x-explorer/scripts/login_x.py --interactive
```
*Opens a visible Chromium window. Log in to X, and your session will be saved to `data/sessions/x_session.json`.*

### Method 3: Verify Session
```bash
uv run .agents/skills/x-explorer/scripts/login_x.py --verify
```
