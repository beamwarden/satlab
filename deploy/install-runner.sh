#!/usr/bin/env bash
# deploy/install-runner.sh — one-time GitHub Actions self-hosted runner bootstrap
#
# Run from your development machine once the target Pi is reachable:
#
#   ./deploy/install-runner.sh --host beamrider-0003.local --label beamrider-0003 --token <REG_TOKEN>
#   ./deploy/install-runner.sh --host beamrider-0004.local --label beamrider-0004 --token <REG_TOKEN>
#
# The registration token is SHORT-LIVED (~1 hour) and cannot be hardcoded.
# Generate a fresh one immediately before running this script:
#
#   gh api -X POST repos/beamwarden/satlab/actions/runners/registration-token --jq .token
#
# (requires admin rights on the repo — gh auth with repo-admin scope, or use
# the GitHub UI: Settings -> Actions -> Runners -> New self-hosted runner,
# which shows the same token). Because the token expires, this script cannot
# be run unattended / scheduled -- it must be run interactively with a token
# generated moments before.
#
# What this does on the target Pi:
#   1. Create the satlab-ci system user + satlab-deploy group (no sudo, no dialout)
#   2. chgrp/chmod /home/jeb/satlab so satlab-ci can git pull without elevation
#      (never touches .env's own permissions)
#   3. Install a NARROWLY scoped sudoers drop-in (systemctl restart/is-active only)
#   4. Add satlab-ci to systemd-journal (log reads without sudo)
#   5. Download the linux-arm64 Actions runner tarball
#   6. Register it against beamwarden/satlab with the given label
#   7. Install + start it as a systemd service (survives reboot)
#
# Safe to re-run: each step is idempotent (checks before creating/installing).

set -euo pipefail

HOST=""
REMOTE_USER="jeb"
LABEL=""
TOKEN=""
RUNNER_VERSION="2.319.1"   # bump as needed; verify against
                           # https://github.com/actions/runner/releases before bumping
RUNNER_TARBALL="actions-runner-linux-arm64-${RUNNER_VERSION}.tar.gz"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)  HOST="$2";  shift 2 ;;
        --user)  REMOTE_USER="$2"; shift 2 ;;
        --label) LABEL="$2"; shift 2 ;;   # beamrider-0003 | beamrider-0004
        --token) TOKEN="$2"; shift 2 ;;
        *)
            echo "unknown option: $1" >&2
            echo "usage: $0 --host <host> --label <beamrider-0003|beamrider-0004> --token <REG_TOKEN>" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$HOST" || -z "$LABEL" || -z "$TOKEN" ]]; then
    echo "usage: $0 --host <host> --label <beamrider-0003|beamrider-0004> --token <REG_TOKEN>" >&2
    exit 1
fi

if [[ "$LABEL" != "beamrider-0003" && "$LABEL" != "beamrider-0004" ]]; then
    echo "ERROR: --label must be beamrider-0003 or beamrider-0004, got: $LABEL" >&2
    exit 1
fi

SERVICE_NAME=$([[ "$LABEL" == "beamrider-0003" ]] && echo satlab-agent || echo sense-agent)

log()  { echo "[install-runner] $*"; }

log "target: ${REMOTE_USER}@${HOST}  label: ${LABEL}  service: ${SERVICE_NAME}"

log "checking SSH connectivity..."
if ! ssh -T -o ConnectTimeout=5 "${REMOTE_USER}@${HOST}" true 2>/dev/null; then
    echo "[install-runner] ERROR: cannot reach ${HOST} — check network, hostname, and SSH keys" >&2
    exit 1
fi
log "SSH OK"

# ── step 1: satlab-ci user + satlab-deploy group ────────────────────────────

log "step 1/7: creating satlab-ci user + satlab-deploy group..."
ssh -T "${REMOTE_USER}@${HOST}" '
    sudo id -u satlab-ci &>/dev/null || sudo useradd --system --create-home --shell /bin/bash satlab-ci
    sudo getent group satlab-deploy &>/dev/null || sudo groupadd satlab-deploy
    sudo usermod -aG satlab-deploy jeb
    sudo usermod -aG satlab-deploy satlab-ci
    sudo usermod -aG systemd-journal satlab-ci
'

# ── step 2: shared write access to the deploy checkout (never touches .env) ──

log "step 2/7: granting satlab-deploy group write access to /home/jeb/satlab..."
ssh -T "${REMOTE_USER}@${HOST}" '
    sudo chgrp -R satlab-deploy /home/jeb/satlab
    sudo chmod -R g+w /home/jeb/satlab
    sudo find /home/jeb/satlab -type d -exec chmod g+s {} \;
'
log "NOTE: .env permissions are untouched by design — verify after this run:"
log "      ssh ${REMOTE_USER}@${HOST} 'ls -l /home/jeb/satlab/.env' (expect 600, owner jeb)"

# ── step 3: scoped sudoers drop-in ───────────────────────────────────────────

log "step 3/7: installing scoped sudoers drop-in for ${SERVICE_NAME}..."
TMPL="$(dirname "$0")/satlab-ci.sudoers.tmpl"
sed "s/SERVICE_NAME/${SERVICE_NAME}/g" "$TMPL" | ssh -T "${REMOTE_USER}@${HOST}" '
    cat > /tmp/satlab-ci.sudoers
    sudo visudo -cf /tmp/satlab-ci.sudoers
    sudo mv /tmp/satlab-ci.sudoers /etc/sudoers.d/satlab-ci-deploy
    sudo chmod 440 /etc/sudoers.d/satlab-ci-deploy
'
log "sudoers drop-in installed and syntax-validated"

# ── step 4: download runner ──────────────────────────────────────────────────

log "step 4/7: downloading GitHub Actions runner ${RUNNER_VERSION} (arm64)..."
ssh -T "${REMOTE_USER}@${HOST}" "
    sudo -u satlab-ci -H bash -c '
        mkdir -p ~/actions-runner && cd ~/actions-runner
        curl -o ${RUNNER_TARBALL} -L \
            https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_TARBALL}
        tar xzf ${RUNNER_TARBALL}
    '
"

# ── step 5: register ─────────────────────────────────────────────────────────

log "step 5/7: registering runner (label: ${LABEL})..."
ssh -T "${REMOTE_USER}@${HOST}" "
    sudo -u satlab-ci -H bash -c '
        cd ~/actions-runner
        ./config.sh --unattended \
            --url https://github.com/beamwarden/satlab \
            --token ${TOKEN} \
            --name ${LABEL} \
            --labels self-hosted,${LABEL} \
            --work _work
    '
"

# ── step 6: install as systemd service ───────────────────────────────────────

log "step 6/7: installing + starting as a systemd service (runs as satlab-ci)..."
ssh -T "${REMOTE_USER}@${HOST}" "
    cd /home/satlab-ci/actions-runner
    sudo ./svc.sh install satlab-ci
    sudo ./svc.sh start
    sudo ./svc.sh status
"

# ── step 7: verify ───────────────────────────────────────────────────────────

log "step 7/7: done."
log "verify online status: gh api repos/beamwarden/satlab/actions/runners --jq '.runners[].name'"
log "verify .env untouched: ssh ${REMOTE_USER}@${HOST} 'ls -l /home/jeb/satlab/.env'"
