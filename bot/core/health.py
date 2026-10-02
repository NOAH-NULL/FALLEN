from aiohttp import web


async def start_health_server(bot, host, port):
    app = web.Application()

    async def healthz(_):
        # Liveness must describe process health, not dependency health. A Redis
        # or PostgreSQL outage should not cause Kubernetes to restart every pod.
        return web.json_response({"status": "ok"}, status=200)

    async def readyz(_):
        db = redis = False
        try:
            db = await bot.db.health()
        except Exception:
            pass
        try:
            redis = await bot.cache.health()
        except Exception:
            pass
        leases = getattr(bot, "shard_leases", None)
        lease_ok = bool(getattr(leases, "healthy", True))
        discord_ready = bool(bot.is_ready())
        ok = db and redis and lease_ok and discord_ready
        return web.json_response(
            {
                "status": "ok" if ok else "degraded",
                "db": db,
                "redis": redis,
                "shard_leases": lease_ok,
                "discord_ready": discord_ready,
            },
            status=200 if ok else 503,
        )

    app.router.add_get("/healthz", healthz)
    app.router.add_get("/readyz", readyz)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    return runner
