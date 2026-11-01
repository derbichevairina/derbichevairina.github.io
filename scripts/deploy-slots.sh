#!/usr/bin/env bash
# Installs the free-slots publisher and its timer on the web server.
set -euo pipefail

HOST="${1:-root@194.87.101.175}"
SSH="${SSH:-ssh}"
SCP="${SCP:-scp}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

$SCP "$repo_root/scripts/free_slots.py" "$HOST:/usr/local/bin/free-slots.py"
$SCP "$repo_root/deploy/systemd/free-slots.service" "$HOST:/etc/systemd/system/free-slots.service"
$SCP "$repo_root/deploy/systemd/free-slots.timer" "$HOST:/etc/systemd/system/free-slots.timer"

$SSH "$HOST" 'bash -euo pipefail -s' <<'REMOTE'
# the Calendly-based publisher it replaces; a no-op once removed
systemctl disable --now calendly-slots.timer 2>/dev/null || true
rm -f /etc/systemd/system/calendly-slots.service /etc/systemd/system/calendly-slots.timer /usr/local/bin/calendly-slots.py
chmod 755 /usr/local/bin/free-slots.py
mkdir -p /var/www/psyholog-slots
systemctl daemon-reload
systemctl enable --now free-slots.timer
# publish once now, so nginx has something to serve before the first timer tick;
# a oneshot unit propagates the script's exit code, so a broken fetch fails the deploy
systemctl start free-slots.service
REMOTE

echo "free-slots publisher installed on $HOST"
