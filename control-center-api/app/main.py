"""FALLEN Control Center API starter.

This service provides a health endpoint and a server-side Discord OAuth flow.
It intentionally does not expose bot/database data until authorization and
least-privilege data adapters are implemented.
"""
from __future__ import annotations

import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

APP_ENV = os.getenv("APP_ENV", "development")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv(
    "DISCORD_REDIRECT_URI",
    "http://localhost:8000/api/auth/callback",
)
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

app = FastAPI(title="FALLEN Control Center API", version="0.1.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET or "development-only-change-me",
    same_site="lax",
    https_only=COOKIE_SECURE,
    session_cookie="fallen_session",
    max_age=60 * 60 * 8,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


def oauth_configured() -> bool:
    return bool(CLIENT_ID and CLIENT_SECRET and SESSION_SECRET)


def require_oauth_config() -> None:
    if not oauth_configured():
        raise HTTPException(
            status_code=503,
            detail="Discord OAuth is not configured on this server.",
        )


def require_session(request: Request) -> dict:
    user = request.session.get("discord_user")
    if not isinstance(user, dict) or not user.get("id"):
        raise HTTPException(status_code=401, detail="Sign-in required.")
    return user


@app.middleware("http")
async def enforce_browser_origin(request: Request, call_next):
    # Mutating routes must be same-origin. OAuth callback is a top-level GET.
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        origin = request.headers.get("origin")
        if origin != FRONTEND_ORIGIN:
            return JSONResponse({"detail": "Invalid request origin."}, status_code=403)
    return await call_next(request)


@app.get("/api/health")
async def health():
    # This is API-process health only, not bot/DB/Redis health.
    return {"status": "ok", "service": "fallen-control-center-api", "version": "0.1.0"}


@app.get("/api/auth/login")
async def login(request: Request):
    require_oauth_config()
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds",
        "state": state,
        "prompt": "consent",
    }
    return RedirectResponse(
        "https://discord.com/oauth2/authorize?" + urlencode(params),
        status_code=302,
    )


@app.get("/api/auth/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    require_oauth_config()
    expected = request.session.pop("oauth_state", None)
    if error or not code or not state or not expected or not secrets.compare_digest(state, expected):
        request.session.clear()
        raise HTTPException(status_code=400, detail="Discord authorization could not be verified. Please try again.")
    async with httpx.AsyncClient(timeout=12.0) as client:
        token_response = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Discord token exchange failed.")
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="Discord did not return an access token.")
        user_response = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Discord identity lookup failed.")
        user = user_response.json()
    # Keep the OAuth access token server-side in the signed session. Never return it to JS.
    request.session.clear()
    request.session["discord_user"] = {
        "id": str(user["id"]),
        "username": user.get("username", "Discord user"),
        "global_name": user.get("global_name"),
        "avatar": user.get("avatar"),
    }
    request.session["oauth_access_token"] = access_token
    return RedirectResponse(FRONTEND_ORIGIN, status_code=303)


@app.get("/api/auth/me")
async def me(request: Request):
    user = request.session.get("discord_user")
    return {"authenticated": bool(isinstance(user, dict) and user.get("id")), "user": user}


@app.post("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    response = JSONResponse({"ok": True})
    response.delete_cookie("fallen_session", path="/", secure=COOKIE_SECURE, httponly=True, samesite="lax")
    return response


@app.get("/api/guilds")
async def guilds(request: Request):
    require_oauth_config()
    require_session(request)
    access_token = request.session.get("oauth_access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Please sign in again.")
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(
            "https://discord.com/api/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not load Discord servers.")
    user_guilds = response.json()
    manageable = []
    for guild in user_guilds:
        try:
            permissions = int(guild.get("permissions", "0"))
        except (ValueError, TypeError):
            continue
        # Discord ADMINISTRATOR = 0x8; MANAGE_GUILD = 0x20.
        if permissions & 0x8 or permissions & 0x20:
            manageable.append({
                "id": str(guild["id"]),
                "name": guild.get("name", "Unnamed server"),
                "icon": guild.get("icon"),
                "owner": bool(guild.get("owner")),
            })
    # Bot installation and per-guild API authorization still need to be verified
    # before this list can be used to access/change any FALLEN configuration.
    return {"guilds": manageable, "live_bot_data": False}


@app.get("/api/guilds/{guild_id}/overview")
async def guild_overview(guild_id: str, request: Request):
    require_session(request)
    if not guild_id.isdecimal() or len(guild_id) > 22:
        raise HTTPException(status_code=400, detail="Invalid server ID.")
    # Fail closed until the bot-installed check and trusted data adapter exist.
    raise HTTPException(
        status_code=501,
        detail="Live server overview is not wired to FALLEN services yet.",
    )
