#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

mkdir -p uploads CONTENT media temp_audios

if command -v docker >/dev/null 2>&1; then
  echo "Starting with Docker Compose..."
  docker compose up --build -d
  echo "API: http://localhost:8000"
  echo "Docs: http://localhost:8000/docs"
  exit 0
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

redis-cli ping >/dev/null 2>&1 || {
  echo "Redis is not running. Start Redis first or install Docker."
  exit 1
}

celery -A gen_topic.celery_app worker --loglevel=info --concurrency=1 &
uvicorn main:app --host 0.0.0.0 --port 8000
