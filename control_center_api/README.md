# FALLEN Control Center API

This FastAPI application is the HTTP/OAuth API for the separate Control Center frontend. The Discord gateway bot remains a separate long-running process.

## Run locally

From the repository root:

```bash
python -m pip install -r control_center_api/requirements.txt
```

Copy `control_center_api/.env.example` to the environment file used by your local API process, then configure the Discord OAuth application values. Start the API with:

```bash
uvicorn control_center_api.app.main:app --reload --port 8000
```

Register the matching callback URL in the Discord Developer Portal:

```
http://localhost:8000/api/auth/callback
```

Set `FRONTEND_ORIGIN=http://localhost:5173` locally. In production, use HTTPS and `COOKIE_SECURE=true`.

## Current limitations

- Session and token state is stored in process memory. Replace it with a shared, expiring server-side store before using multiple workers or production deployments.
- `/api/guilds` lists servers where the signed-in user has Manage Server or Administrator permission. It does not verify that FALLEN is installed in each server.
- The guild overview intentionally returns HTTP 501 until a trusted adapter verifies bot installation and loads real data.
- Server settings are not currently writable through this API.
- Add rate limiting, audit logs, session expiry/revocation, OAuth token refresh/revocation, and deployment-specific origin/proxy validation before production use.
- Never expose bot tokens, database credentials, Redis credentials, OAuth client secrets, or session secrets to the browser.

## Vercel

The repository's `pyproject.toml` points Vercel at `control_center_api.app.main:app`. Vercel hosts this HTTP API only; it does not host the Discord gateway process. Keep the bot running separately on a long-lived service. The current process-local session store is not restart-resilient or horizontally scalable.
