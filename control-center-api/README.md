# FALLEN Control Center API

A FastAPI starter for the Control Center. It includes a health endpoint, a Discord OAuth authorization-code flow, a signed HttpOnly session cookie containing only an opaque session ID, and a guild list filtered by Discord permissions.

## Run locally

```bash
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Export the variables from `.env` into your shell or use your deployment provider's environment settings. The example values are not production credentials.

Register this exact local callback in the Discord Developer Portal:
`http://localhost:8000/api/auth/callback`

Set `FRONTEND_ORIGIN=http://localhost:5173` locally and configure `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, and a cryptographically random `SESSION_SECRET`. In production, use HTTPS and `COOKIE_SECURE=true`.

## Important limitations before production

- The session/token store is process-local memory. It is for a single-process starter only; replace it with a shared, expiring server-side store before using multiple workers or production deployments.
- `/api/guilds` lists servers where the signed-in user has Manage Server or Administrator permission. It does **not** verify that FALLEN is installed in each server.
- The guild overview intentionally returns HTTP 501 until a trusted adapter verifies bot installation and loads real data.
- No server settings are currently writable through this API.
- Add rate limiting, structured audit logs, session expiry/revocation, OAuth token refresh/revocation, and deployment-specific origin/proxy validation before production use.
- Never expose bot tokens, database credentials, Redis credentials, OAuth client secrets, or session secrets to the browser.
