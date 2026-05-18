#!/usr/bin/env bash
# deploy/deploy.sh — deploy the satlab agent to beamrider-0003
#
# Run from your development machine:
#
#   ./deploy/deploy.sh [--host <hostname>] [--user <user>] [--dry-run]
#
# Defaults:
#   --host  beamrider-0003.local   (mDNS; use IP if mDNS is unavailable)
#   --user  jeb
#
# What this script does (in order):
#   1. Pull the latest commits on the current branch from origin
#   2. Install or upgrade Python dependencies from agent/requirements.txt
#   3. Restart the satlab-agent systemd service
#   4. Tail the service log for 15 seconds so you can verify a clean startup
#
# Prerequisites on the Pi (first-time only — see CLAUDE.md "RPi setup"):
#   - repo cloned at ~/satlab
#   - /home/jeb/satlab/.env populated with all required environment variables
#   - satlab-agent.service installed and enabled (see deploy/install-service.sh)
#   - jeb in the dialout group (sudo usermod -aG dialout jeb; then re-login)
#
# Exit codes:
#   0  — deployment succeeded and service started cleanly
#   1  — SSH unreachable, git pull failed, pip failed, or service failed to start

set -euo pipefail

# ── defaults ──────────────────────────────────────────────────────────────────

HOST="beamrider-0003.local"
REMOTE_USER="jeb"
REPO_DIR="/home/jeb/satlab"
DRY_RUN=false

# ── argument parsing ──────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)   HOST="$2";        shift 2 ;;
        --user)   REMOTE_USER="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true;    shift   ;;
        *)
            echo "unknown option: $1" >&2
            echo "usage: $0 [--host HOST] [--user USER] [--dry-run]" >&2
            exit 1
            ;;
    esac
done

# ── helpers ───────────────────────────────────────────────────────────────────

log()  { echo "[deploy] $*"; }
warn() { echo "[deploy] WARNING: $*" >&2; }

ssh_run() {
    # Run a command on the Pi over SSH. Passes -T to suppress pseudo-tty
    # allocation (no interactive prompts expected). Exits this script if the
    # remote command fails.
    local cmd="$*"
    if $DRY_RUN; then
        log "DRY-RUN ssh ${REMOTE_USER}@${HOST} -- $cmd"
        return 0
    fi
    ssh -T "${REMOTE_USER}@${HOST}" "$cmd"
}

# ── preflight ─────────────────────────────────────────────────────────────────

log "target: ${REMOTE_USER}@${HOST}  repo: ${REPO_DIR}"
$DRY_RUN && log "DRY-RUN mode: no changes will be made"

log "checking SSH connectivity..."
if ! ssh -T -o ConnectTimeout=5 "${REMOTE_USER}@${HOST}" true 2>/dev/null; then
    echo "[deploy] ERROR: cannot reach ${HOST} — check network, hostname, and SSH keys" >&2
    exit 1
fi
log "SSH OK"

# ── step 1: git pull ──────────────────────────────────────────────────────────

log "step 1/3: pulling latest commits..."
ssh_run "cd ${REPO_DIR} && git pull --ff-only origin \$(git rev-parse --abbrev-ref HEAD)"

# ── step 2: install dependencies ─────────────────────────────────────────────
#
# --break-system-packages is required on Bookworm (PEP 668) because the Pi
# uses the system Python rather than a venv. The flag is safe here: all
# packages are pinned in requirements.txt and the Pi is a single-purpose node.

log "step 2/3: installing Python dependencies..."
ssh_run "pip install -q --break-system-packages -r ${REPO_DIR}/agent/requirements.txt"

# ── step 3: restart service ───────────────────────────────────────────────────

log "step 3/3: restarting satlab-agent service..."
ssh_run "sudo systemctl restart satlab-agent"

# Give systemd a moment to attempt the start before we check status.
sleep 2

# Verify the service is active. 'is-active' exits non-zero if the unit is not
# in the 'active' state, which causes the script to exit via set -e.
log "verifying service is active..."
ssh_run "systemctl is-active --quiet satlab-agent"
log "service is active"

# ── tail logs ─────────────────────────────────────────────────────────────────
#
# Stream 15 seconds of journal output so the operator can confirm a clean
# startup (serial port open, TLE loaded, first Beamwarden ingest accepted).
# The tail runs in the foreground; Ctrl-C here does not affect the service.

log "tailing service log for 15 seconds (Ctrl-C to stop early)..."
if ! $DRY_RUN; then
    ssh -T "${REMOTE_USER}@${HOST}" \
        "journalctl -u satlab-agent -n 30 --no-pager -f" &
    TAIL_PID=$!
    sleep 15
    kill "$TAIL_PID" 2>/dev/null || true
    wait "$TAIL_PID" 2>/dev/null || true
fi

log "deployment complete"
