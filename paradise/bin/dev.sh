#!/usr/bin/env bash
# Dev environment Paradise Task Tracker (build dari source).
# Wrapper tipis di atas docker-compose-local.yml. Jalankan dari root repo.
#   ./paradise/bin/dev.sh up|down|logs|rebuild|ps
set -euo pipefail

COMPOSE="docker compose -f docker-compose-local.yml"
cd "$(dirname "$0")/../.."   # -> root repo

[ -f .env ] || { echo "ERROR: .env tidak ada. Jalankan: cp paradise/.env.example .env"; exit 1; }

case "${1:-up}" in
  up)      $COMPOSE up -d --build ;;
  down)    $COMPOSE down ;;
  logs)    $COMPOSE logs -f --tail=100 "${2:-}" ;;
  rebuild) $COMPOSE up -d --build --force-recreate "${2:-}" ;;
  ps)      $COMPOSE ps ;;
  *)       echo "usage: dev.sh up|down|logs|rebuild|ps"; exit 2 ;;
esac
