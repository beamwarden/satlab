#!/usr/bin/env bash
# deploy/install-service.sh — first-time systemd service install on beamrider-0003
#
# Run from your development machine after cloning the repo on the Pi:
#
#   ./deploy/install-service.sh [--host <hostname>] [--user <user>]
#
# What this script does:
#   1. Copies deploy/satlab-agent.service to /etc/systemd/system/ on the Pi
#   2. Reloads the systemd daemon
#   3. Enables the service so it starts automatically on boot
#   4. Prints a checklist of manual steps required before the first start
#
# Run deploy.sh (not this script) for all subsequent deployments.

set -euo pipefail

HOST="beamrider-0003.local"
REMOTE_USER="jeb"
SERVICE_FILE="$(dirname "$0")/satlab-agent.service"

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

log()  { echo "[install] $*"; }

log "target: ${REMOTE_USER}@${HOST}"

log "checking SSH connectivity..."
if ! ssh -T -o ConnectTimeout=5 "${REMOTE_USER}@${HOST}" true 2>/dev/null; then
    echo "[install] ERROR: cannot reach ${HOST}" >&2
    exit 1
fi

log "copying service file..."
scp "$SERVICE_FILE" "${REMOTE_USER}@${HOST}:/tmp/satlab-agent.service"
ssh -T "${REMOTE_USER}@${HOST}" \
    "sudo mv /tmp/satlab-agent.service /etc/systemd/system/satlab-agent.service && \
     sudo systemctl daemon-reload && \
     sudo systemctl enable satlab-agent"

log "service installed and enabled"
echo ""
echo "Before starting the service, complete these steps on the Pi:"
echo ""
echo "  1. Populate /home/jeb/satlab/.env with all required variables:"
echo "       SATLAB_SERIAL_PORT=/dev/ttyACM0"
echo "       BEAMWARDEN_URL=http://<beamwarden-host>:8000"
echo "       BEAMWARDEN_TOKEN=<token-from-beamwarden>"
echo "       SATLAB_NORAD_ID=25544"
echo "       SPACETRACK_USER=<email>"
echo "       SPACETRACK_PASS=<password>"
echo ""
echo "  2. Add jeb to the dialout group (if not already done) and re-login:"
echo "       sudo usermod -aG dialout jeb"
echo ""
echo "  3. Plug in the Arduino and verify the serial device:"
echo "       ls /dev/ttyACM* /dev/ttyUSB*"
echo ""
echo "  4. Register beamrider-0003 in Beamwarden to obtain the bearer token."
echo ""
echo "Then run: ./deploy/deploy.sh"
