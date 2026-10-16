# FALLEN Control Center

A separate web control plane for the FALLEN Discord bot. This directory is an initial scaffold on the `feat/control-center-scaffold` branch; it is not deployed and does not modify the production bot.

## Current state

- Frontend: React + TypeScript + Vite starter with clearly labeled demo data.
- Backend: FastAPI health endpoint only.
- Live Discord authentication, server authorization, configuration writes, and bot integration are **not implemented yet**.
- No production credentials or database migrations are included.

## Structure

```
control-center/
  frontend/
    index.html
    package.json
    tsconfig.json
    vite.config.ts
    src/
      main.tsx
      App.tsx
      styles.css
  backend/
    requirements.txt
    app/
      __init__.py
      main.py
  .env.example
  .gitignore
```

## Run the frontend

Requires Node.js 20+.

```sh
cd control-center/frontend
npm install
npm run dev
```

## Run the API

Requires Python 3.12+.

```sh
cd control-center/backend
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8082
```

Health check: `GET http://127.0.0.1:8082/health`.

## Safety notes

- Demo metrics are illustrative and must not be interpreted as live bot telemetry.
- Do not paste tokens or credentials into source files.
- The existing bot already has an aiohttp dashboard API and a PostgreSQL-backed guild configuration service. Integration design must inspect their complete contracts before implementation.
- Do not point this scaffold at production data or deploy it until authentication, authorization, API contracts, and tests are implemented.
