# Discloud Deployment

Discloud runs the bot process; it does not run this repository's Docker Compose stack. PostgreSQL, Redis, and Lavalink must be hosted separately and reachable from Discloud.

## Prepare the App

The repository includes a root `main.py`, `discloud.config`, and `requirements.txt`. Upload the project with those files at the archive root. Do not upload `.env`; `.discloudignore` excludes it. Set secrets in the Discloud application's environment-variable settings instead.

Use a plan with enough memory for the bot and its dependencies. The manifest requests 512 MB; lower it only if the selected plan requires it and the app fits.

## Environment Variables

Set these in Discloud's app settings:

- `DISCORD_TOKEN`
- `DATABASE_URL` using the SQLAlchemy `postgresql+asyncpg://` scheme
- `REDIS_URL`
- `LAVALINK_URL`
- `LAVALINK_PASSWORD`

`GUILD_ID` is optional. Use managed or otherwise persistent PostgreSQL and Redis services; local `localhost` defaults will not work in Discloud. Use a Lavalink v4 node that the bot can reach and configure it with plugins for the media sources you need.

## Database Migration

Run `alembic upgrade head` once against the hosted database before starting the bot. The database provider must allow the migration client to connect. Repeat migrations when deploying future schema changes.

## Upload and Operate

Upload the project through Discloud's panel or supported CLI, then start the bot from its application page. Check the deployment logs for `Connected music node` and `bot ready`. Keep PostgreSQL, Redis, and Lavalink running independently; restarting the bot does not restore its in-memory music queue or voice session.