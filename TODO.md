# satlab self-hosted runner — bootstrap TODO

Everything here requires physical/LAN access to the Pis, which isn't available
while traveling. Pick this up once you're back home (or once Tailscale/VPN
access to the Pis exists).

## Prerequisites

- [ ] LAN/SSH access to `beamrider-0003.local` and `beamrider-0004.local`
- [ ] `gh auth status` shows admin rights on `beamwarden/satlab` (needed to mint runner registration tokens)

## Per-Pi bootstrap

Registration tokens are short-lived (~1hr) — generate one immediately before
running the script, not in advance.

### beamrider-0003 (satlab-agent)

1. `gh api -X POST repos/beamwarden/satlab/actions/runners/registration-token --jq .token`
2. `./deploy/install-runner.sh --host beamrider-0003.local --label beamrider-0003 --token <REG_TOKEN>`
3. Verify `.env` untouched: `ssh jeb@beamrider-0003.local "ls -l /home/jeb/satlab/.env"` — expect `600`, owner `jeb`
4. If `pip install --break-system-packages` fails under the new `satlab-ci` user (group-write turns out insufficient for dist-packages), uncomment the pip fallback lines in `deploy/satlab-ci.sudoers.tmpl` and re-run step 2 (the script is idempotent)

### beamrider-0004 (sense-agent)

1. Fresh token again — same command as above
2. `./deploy/install-runner.sh --host beamrider-0004.local --label beamrider-0004 --token <REG_TOKEN>`
3. Same `.env` permission check as above

## After both runners are online

- [ ] `gh api repos/beamwarden/satlab/actions/runners --jq '.runners[].name'` — confirm both `beamrider-0003` and `beamrider-0004` show up
- [ ] Merge PR #2 (rate-limit fix: 30min → 1hr) and PR #3 (this deploy pipeline) — needs an actual `develop` → `main` promotion, since both workflows trigger only on push to `main`
- [ ] Watch the Actions tab for `Deploy — beamrider-0003 (satlab-agent)` and `Deploy — beamrider-0004 (sense-agent)` to fire; approve the environment-reviewer prompt on each
- [ ] Check the workflow's own journalctl diagnostics step (or `ssh ... "systemctl status satlab-agent"`) for a clean restart: serial port opened, TLE loaded, first Beamwarden ingest accepted
- [ ] Confirm `satlab-agent` is actually running the fixed 3600s interval — journalctl "refreshing TLE" log lines should now be ~1hr apart, not ~30min

## Reference

- Bootstrap script: `deploy/install-runner.sh`
- Sudoers template: `deploy/satlab-ci.sudoers.tmpl`
- Workflows: `.github/workflows/deploy-agent.yml`, `.github/workflows/deploy-sense-agent.yml`
- Full design writeup: `CLAUDE.md` → "CI/CD (GitHub Actions self-hosted runner)"
- PRs: [beamwarden/satlab#2](https://github.com/beamwarden/satlab/pull/2), [beamwarden/satlab#3](https://github.com/beamwarden/satlab/pull/3)
