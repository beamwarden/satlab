#!/usr/bin/env bash
# deploy/install-sense-service.sh — first-time systemd install on beamrider-0004
#
# Run from your development machine after the Pi is provisioned (see CLAUDE.md):
#
#   ./deploy/install-sense-service.sh [--host <hostname>] [--user <user>]
#
# Defaults:
#   --host  beamrider-0004.local
#   --user  jeb

set -euo pipefail

HOST="beamrider-0004.local"
REMOTE_USER="jeb"
SERVICE_FILE="$(dirname "$0")/sense-agent.service"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host) HOST="$2";        shift 2 ;;
        --user) REMOTE_USER="$2"; shift 2 ;;
        *)
            echo "unknown option: $1" >&2
            exit 1
            ;;
    esac
done

log() { echo "[install-sense] $*"; }

log "target: ${REMOTE_USER}@${HOST}"

log "checking SSH connectivity..."
if ! ssh -T -o ConnectTimeout=5 "${REMOTE_USER}@${HOST}" true 2>/dev/null; then
    echo "[install-sense] ERROR: cannot reach ${HOST}" >&2
    exit 1
fi

log "copying service file..."
scp "$SERVICE_FILE" "${REMOTE_USER}@${HOST}:/tmp/sense-agent.service"
ssh -T "${REMOTE_USER}@${HOST}" \
    "sudo mv /tmp/sense-agent.service /etc/systemd/system/sense-agent.service && \
     sudo systemctl daemon-reload && \
     sudo systemctl enable sense-agent"

log "service installed and enabled"
echo ""
echo "Before starting the service, complete these steps on the Pi:"
echo ""
echo "  1. Populate /home/jeb/satlab/.env:"
echo "       BEAMWARDEN_URL=https://<beamwarden-host>"
echo "       BEAMWARDEN_TOKEN=<token-from-beamwarden-for-beamrider-0004>"
echo ""
echo "  2. Register beamrider-0004 in Beamwarden and add sensors:"
echo "       lsm9ds1  (subsystem: adcs)"
echo "       hts221   (subsystem: tcs)"
echo "       lps25h   (subsystem: tcs)"
echo ""
echo "Then run: ./deploy/deploy-sense.sh"
