#!/usr/bin/env bash
# Installs deploy/nginx/ on the web server, validating the config and rolling back if it breaks.
set -euo pipefail

HOST="${1:-root@194.87.101.175}"
SSH="${SSH:-ssh}"
SCP="${SCP:-scp}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

$SSH "$HOST" 'mkdir -p /etc/nginx/snippets /etc/nginx/conf.d /root/nginx-backup'
$SCP "$repo_root/deploy/nginx/conf.d/markdown-negotiation.conf" "$HOST:/etc/nginx/conf.d/markdown-negotiation.conf"
$SCP "$repo_root/deploy/nginx/snippets/markdown-location.conf" "$HOST:/etc/nginx/snippets/markdown-location.conf"
$SCP "$repo_root/deploy/nginx/snippets/slots-locations.conf" "$HOST:/etc/nginx/snippets/slots-locations.conf"
$SCP "$repo_root/deploy/nginx/sites-available/psyholog" "$HOST:/etc/nginx/sites-available/psyholog.new"

$SSH "$HOST" 'bash -euo pipefail -s' <<'REMOTE'
cp /etc/nginx/sites-available/psyholog /root/nginx-backup/psyholog.bak
mv /etc/nginx/sites-available/psyholog.new /etc/nginx/sites-available/psyholog

if ! nginx -t; then
    echo "config rejected, rolling back" >&2
    cp /root/nginx-backup/psyholog.bak /etc/nginx/sites-available/psyholog
    nginx -t
    exit 1
fi

systemctl reload nginx
REMOTE

echo "nginx config installed on $HOST"
