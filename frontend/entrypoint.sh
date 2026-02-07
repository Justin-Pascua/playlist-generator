#!/bin/sh
set -e

echo "Waiting for API..."
until curl -sf http://api:8000/; do
  sleep 1
done

echo "API is up — starting Discord bot"
exec python -m discord_bot.main PROD
