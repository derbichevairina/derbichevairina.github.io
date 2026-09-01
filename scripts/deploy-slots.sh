#!/usr/bin/env bash
# Installs the Calendly slot publisher and its timer on the web server.
set -euo pipefail

HOST="${1:-root@194.87.101.175}"
SSH="${SSH:-ssh}"
SCP="${SCP:-scp}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

$SCP "$repo_root/scripts/calendly_slots.py" "$HOST:/usr/local/bin/calendly-slots.py"
$SCP "$repo_root/deploy/systemd/calendly-slots.service" "$HOST:/etc/systemd/system/calendly-slots.service"
$SCP "$repo_root/deploy/systemd/calendly-slots.timer" "$HOST:/etc/systemd/system/calendly-slots.timer"

$SSH "$HOST" 'bash -euo pipefail -s' <<'REMOTE'
chmod 755 /usr/local/bin/calendly-slots.py
mkdir -p /var/www/psyholog-slots
systemctl daemon-reload
systemctl enable --now calendly-slots.timer
# publish once now, so nginx has something to serve before the first timer tick
systemctl start calendly-slots.service
systemctl status calendly-slots.service --no-pager --lines 3
REMOTE

echo "slot publisher installed on $HOST"
