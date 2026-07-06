# satlab self-hosted runner — bootstrap TODO

**Status as of 2026-07-06:** `satlab-agent` on beamrider-0003 is stopped and
disabled (`systemctl stop` + `disable`) — it was still querying Space-Track
directly (a second IP on the account) even after its poll interval was fixed,
which is exactly the "multiple servers/IPs" pattern Space-Track flagged
separately from per-source frequency. Do not re-enable it until the migration
below is done. See memory `project-spacetrack-suspension-2026-07`.

`feat/orbit-nebody-api` has been rebased onto current `develop` and pushed
(`38b8a3d`, force-pushed 2026-07-06) — conflicts in `agent/orbit.py`/`CLAUDE.md`
resolved by taking the ne-body-cache version, keeping `SATLAB_HW_KEY` from
develop; 17/17 tests pass. Still needs to actually merge to `develop` and
promote to `main` (see Priority 0).

SSH access to beamrider-0003.local now works directly from the main dev
machine (confirmed 2026-07-05) — the "requires physical/LAN access, blocked
while traveling" framing below is stale as of that date; re-verify current
network access before assuming this is still blocked.

## Priority 0: migrate off direct Space-Track access

ne-body now exposes `GET /tle/{norad_id}/latest` and `GET /tle/latest`
(commit `e3ed793`, deployed to `keep-0001`) specifically so satlab doesn't
need its own Space-Track poller.

- [x] Rebase `feat/orbit-nebody-api` onto current `develop` — done 2026-07-06
- [ ] Merge `feat/orbit-nebody-api` to `develop`, then promote to `main`
- [ ] Re-enable `satlab-agent` on beamrider-0003, confirm via journalctl that
      it's hitting ne-body's endpoint and never `www.space-track.org`

## Prerequisites (self-hosted runner bootstrap — secondary to the above)

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
- [x] PR #2 (rate-limit fix: 30min → 1hr) and PR #3 (this deploy pipeline) merged to `develop` — still need an actual `develop` → `main` promotion, since both workflows trigger only on push to `main` (see Priority 0 above, which now also needs to land before this promotion)
- [ ] Watch the Actions tab for `Deploy — beamrider-0003 (satlab-agent)` and `Deploy — beamrider-0004 (sense-agent)` to fire; approve the environment-reviewer prompt on each
- [ ] Check the workflow's own journalctl diagnostics step (or `ssh ... "systemctl status satlab-agent"`) for a clean restart: serial port opened, TLE loaded, first Beamwarden ingest accepted
- [ ] Confirm `satlab-agent` is actually running the fixed 3600s interval — journalctl "refreshing TLE" log lines should now be ~1hr apart, not ~30min

## Reference

- Bootstrap script: `deploy/install-runner.sh`
- Sudoers template: `deploy/satlab-ci.sudoers.tmpl`
- Workflows: `.github/workflows/deploy-agent.yml`, `.github/workflows/deploy-sense-agent.yml`
- Full design writeup: `CLAUDE.md` → "CI/CD (GitHub Actions self-hosted runner)"
- PRs: [beamwarden/satlab#2](https://github.com/beamwarden/satlab/pull/2), [beamwarden/satlab#3](https://github.com/beamwarden/satlab/pull/3)
