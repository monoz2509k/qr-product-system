# QR Product System

Minimal FastAPI backend for the DEIP QR product traceability system.
Run in Bash:

```bash
cp .env.example .env
uv sync
docker compose up -d
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check .
```

Run tests and lint in another terminal while the server is running.
`GET /health` returns `{"status": "ok", "database": "up"}` or `"down"`.
Module folders are placeholders; no migrations have been created.
