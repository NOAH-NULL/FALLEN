from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    frontend_origin: str = "http://127.0.0.1:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
app = FastAPI(
    title="FALLEN Control Center API",
    version="0.1.0",
    description="Initial scaffold. Authentication and live bot integration are not implemented.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    """Liveness endpoint; does not claim the Discord bot is healthy."""
    return {"status": "ok", "service": "fallen-control-center-api", "mode": "scaffold"}
