def guild(guild_id: int) -> str:
    return f"guild:{guild_id}:config"

def cooldown(scope: str, guild_id: int, user_id: int, command: str) -> str:
    return f"cooldown:{scope}:{guild_id}:{user_id}:{command}"
