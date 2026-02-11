#!/bin/sh
set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "Waiting for API at $BASE_URL"
until curl -sf "$BASE_URL/"; do
  sleep 1
done

echo "API is up — starting Discord bot"
exec python -m discord_bot.main PROD
