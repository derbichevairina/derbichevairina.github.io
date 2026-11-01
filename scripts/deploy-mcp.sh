#!/usr/bin/env bash
# Builds and starts the booking MCP server container on the web server, then checks it reads the schedule.
set -euo pipefail

HOST="${1:-root@194.87.101.175}"
SSH="${SSH:-ssh}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

tar --exclude __pycache__ -C "$repo_root/mcp" -czf - pyproject.toml uv.lock Dockerfile compose.yml booking_mcp \
    | $SSH "$HOST" 'rm -rf /opt/psyholog-mcp/booking_mcp && mkdir -p /opt/psyholog-mcp && tar -xzf - -C /opt/psyholog-mcp'

$SSH "$HOST" 'bash -euo pipefail -s' <<'REMOTE'
cd /opt/psyholog-mcp
docker compose -p psyholog-mcp up -d --build --remove-orphans
docker image prune -f >/dev/null
for attempt in $(seq 1 30); do
    if curl -sf -X POST http://127.0.0.1:3200/mcp \
        -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
        -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_free_slots","arguments":{}}}' \
        | grep -q '"session_minutes"'; then
        echo "booking MCP reads the schedule"
        exit 0
    fi
    sleep 2
done
docker compose -p psyholog-mcp logs --tail 50
exit 1
REMOTE
