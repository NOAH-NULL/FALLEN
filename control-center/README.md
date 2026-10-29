# FALLEN Control Center

A responsive React + Vite dashboard scaffold for the FALLEN Discord bot. The current interface is deliberately in **preview mode**: sample activity is illustrative, status metrics are not live, and security switches do not save settings.

## Run locally

Requirements: Node.js 20 or newer.

```bash
cd control-center
npm install
npm run dev
```

Vite prints a local development URL. To build the static site:

```bash
npm run build
npm run preview
```

## Current state

- Responsive dark charcoal / crimson interface
- Overview, navigation, sample activity search, quick actions, and preview toggles
- Explicit preview-mode messaging; no fake live metrics or successful mutations
- Discord connection setup guidance
- The UI is not yet wired to FALLEN's PostgreSQL/Redis state or Discord OAuth

## Next integration steps

1. Create a Discord application and register an exact HTTPS OAuth callback URL.
2. Implement OAuth authorization-code flow on a server-side API. Keep the client secret and session signing key out of Vite/client environment variables.
3. Use secure, HttpOnly, SameSite cookies, CSRF state validation, and HTTPS in production.
4. Validate that the signed-in Discord user has administrator/manage-server permission for the selected guild, and independently verify the bot is installed there.
5. Expose narrowly scoped API endpoints for configuration, activity and diagnostics. Validate every guild ID and every requested action on the server.
6. Connect the API to the existing bot services/database using least-privilege credentials. Never expose PostgreSQL, Redis, bot tokens or arbitrary internal URLs to the browser.
7. Replace sample data only after live endpoints are implemented and tested.

## Deployment

This directory can be deployed as a static Vite site (for example, a Vercel project with root directory `control-center` and build command `npm run build`). Static hosting alone does **not** enable OAuth or live bot data. Those require a separately deployed backend and environment variables.

## API contract (future)

- `GET /api/health` — API health only
- `GET /api/auth/me` — current signed-in identity
- `GET /api/guilds` — guilds the signed-in user may manage and where FALLEN is installed
- `GET /api/guilds/{guild_id}/overview` — verified guild overview
- `PATCH /api/guilds/{guild_id}/settings` — validated, authorized configuration update

Do not treat a successful API health response as proof the Discord bot, database, Redis or gateway is healthy.