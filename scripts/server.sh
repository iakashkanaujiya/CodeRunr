#!/bin/bash
set -e

# ── Start the server ─────────────────────────────────────────
echo "Running database migrations..."
uv run alembic upgrade head

echo "Seeding languages..."
uv run python -m db.seeds.languages

echo "Starting API server..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
