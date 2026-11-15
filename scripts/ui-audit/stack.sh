#!/usr/bin/env bash
# Start/stop the local Paradise stack for UI audits.
#   scripts/ui-audit/stack.sh up      # docker backend + web dev server (port 4000)
#   scripts/ui-audit/stack.sh seed    # one-time: bootstrap admin+workspace, then repo demo seed (needs UI_AUDIT_EMAIL/PASSWORD)
#   scripts/ui-audit/stack.sh down    # stop web dev server and containers (data volumes are kept)
#   scripts/ui-audit/stack.sh status
set -euo pipefail
cd "$(dirname "$0")/../.."
DC="sudo --preserve-env=UI_AUDIT_EMAIL,UI_AUDIT_PASSWORD docker compose -f docker-compose-local.yml"
LOG="${UI_AUDIT_WEB_LOG:-/tmp/claude-1001/web-dev.log}"

case "${1:-status}" in
  up)
    $DC up -d plane-db plane-redis plane-mq plane-minio
    $DC up migrator
    $DC up -d api worker
    until curl -fs -o /dev/null http://localhost:8000/api/instances/; do sleep 3; done
    if ! curl -fs -o /dev/null http://localhost:4000/; then
      mkdir -p "$(dirname "$LOG")"
      nohup setsid pnpm turbo run dev --filter=web > "$LOG" 2>&1 < /dev/null &
      until curl -fs -o /dev/null http://localhost:4000/; do sleep 3; done
    fi
    echo "api :8000 and web :4000 are up (web log: $LOG)"
    ;;
  seed)
    : "${UI_AUDIT_EMAIL:?}" "${UI_AUDIT_PASSWORD:?}"
    $DC exec -T -e UI_AUDIT_EMAIL -e UI_AUDIT_PASSWORD api python manage.py shell --settings=plane.settings.local < scripts/ui-audit/seed.py
    $DC exec -T api python manage.py seed_demo_data --settings=plane.settings.local
    ;;
  down)
    pkill -f "react-router dev --port 4000" || true
    pkill -f "turbo run dev --filter=web" || true
    $DC stop
    ;;
  status)
    $DC ps --format '{{.Name}} {{.Status}}'
    curl -s -o /dev/null -w 'web :4000 -> %{http_code}\n' http://localhost:4000/ || true
    ;;
  *) echo "usage: $0 up|seed|down|status"; exit 2 ;;
esac
