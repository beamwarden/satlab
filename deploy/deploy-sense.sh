#!/usr/bin/env bash
# deploy/deploy-sense.sh — deploy the Sense HAT agent to beamrider-0004
#
# Run from your development machine:
#
#   ./deploy/deploy-sense.sh [--host <hostname>] [--user <user>] [--dry-run]
#
# Defaults:
#   --host  beamrider-0004.local
#   --user  jeb

set -euo pipefail

HOST="beamrider-0004.local"
REMOTE_USER="jeb"
REPO_DIR="/home/jeb/satlab"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)    HOST="$2";        shift 2 ;;
        --user)    REMOTE_USER="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true;     shift   ;;
        *)
            echo "unknown option: $1" >&2
            echo "usage: $0 [--host HOST] [--user USER] [--dry-run]" >&2
            exit 1
            ;;
    esac
done

log()  { echo "[deploy-sense] $*"; }

ssh_run() {
    local cmd="$*"
    if $DRY_RUN; then
        log "DRY-RUN ssh ${REMOTE_USER}@${HOST} -- $cmd"
        return 0
    fi
    ssh -T "${REMOTE_USER}@${HOST}" "$cmd"
}

log "target: ${REMOTE_USER}@${HOST}  repo: ${REPO_DIR}"
$DRY_RUN && log "DRY-RUN mode: no changes will be made"

log "checking SSH connectivity..."
if ! ssh -T -o ConnectTimeout=5 "${REMOTE_USER}@${HOST}" true 2>/dev/null; then
    echo "[deploy-sense] ERROR: cannot reach ${HOST}" >&2
    exit 1
fi
log "SSH OK"

log "step 1/3: pulling latest commits..."
ssh_run "cd ${REPO_DIR} && git pull --ff-only origin \$(git rev-parse --abbrev-ref HEAD)"

log "step 2/3: installing Python dependencies..."
ssh_run "pip install -q --break-system-packages -r ${REPO_DIR}/sense-agent/requirements.txt"

log "step 3/3: restarting sense-agent service..."
ssh_run "sudo systemctl restart sense-agent"

sleep 2

log "verifying service is active..."
ssh_run "systemctl is-active --quiet sense-agent"
log "service is active"

log "tailing service log for 15 seconds (Ctrl-C to stop early)..."
if ! $DRY_RUN; then
    ssh -T "${REMOTE_USER}@${HOST}" \
        "journalctl -u sense-agent -n 30 --no-pager -f" &
    TAIL_PID=$!
    sleep 15
    kill "$TAIL_PID" 2>/dev/null || true
    wait "$TAIL_PID" 2>/dev/null || true
fi

log "deployment complete"
