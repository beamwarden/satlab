# Engineering Log — satlab

Narrative record of daily progress, decisions, and open threads.
Most recent entry first.

---

## 2026-07-29

### CI/CD deploy pipeline debugged end-to-end on both Pis (first real exercise since PR #2/#3)

`develop` promoted to `main` (fast-forward to `902f01b`), carrying the self-hosted-runner workflows, the ne-body TLE-cache orbit switch, and deploy scripts that had sat on `develop` unpromoted since merge. The push fired `deploy-agent.yml` for real for the first time, which showed the pipeline had never actually been exercised against live hardware — it failed immediately.

**beamrider-0003 — four fixes, each a real `satlab-ci` least-privilege gap:**

1. `cd /home/jeb/satlab: Permission denied` — `/home/jeb` is `drwx------` (jeb:jeb). `satlab-ci` is correctly in the `satlab-deploy` group that owns `/home/jeb/satlab` itself (`drwxrwsr-x ... satlab-deploy`), but couldn't traverse the parent to get there. Fixed with an ACL scoped to exactly that user rather than opening traversal to the whole box:
   ```
   sudo setfacl -m u:satlab-ci:x /home/jeb
   ```
2. `fatal: detected dubious ownership in repository at '/home/jeb/satlab'` — git's ownership check rejects a non-owner operating on the repo by default.
   ```
   sudo -u satlab-ci git config --global --add safe.directory /home/jeb/satlab
   ```
3. `Host key verification failed` on `git fetch` — origin was `git@github.com:beamwarden/satlab.git` (SSH) and `satlab-ci` has no `~/.ssh` at all (no keys, no known_hosts). Since the repo is public, switched to the anonymous HTTPS remote instead of provisioning `satlab-ci` its own deploy key:
   ```
   sudo -u satlab-ci git remote set-url origin https://github.com/beamwarden/satlab.git
   ```
   Note: this changes `jeb`'s own manual `git pull`/`push` from this checkout too, since there's one `origin` per repo, not per-user. Fine for pulls; would need a credential if ever pushing from the Pi directly.
4. `unable to append to '.git/logs/refs/remotes/origin/main': Permission denied` — that one ref-log file was `-rw-r--r--` while its siblings (`develop`, `HEAD`) were `-rw-rw-r--`. Inconsistent history, not a systemic issue — just needed:
   ```
   chmod g+w /home/jeb/satlab/.git/logs/refs/remotes/origin/main
   ```

Run `30504239868` went green after all four: pull → deps → restart → verify.

**beamrider-0004 — stale/orphaned runner, plus fixes 1 and 2 above:**

The push-triggered run (`30501320354`) had been queued for ~1hr with nothing to pick it up. `gh api repos/beamwarden/satlab/actions/runners` showed `total_count: 1` — only `beamrider-0003` registered. On the Pi, `/home/satlab-ci/actions-runner/.runner` showed a real prior registration (`agentName: beamrider-0004`, `agentId: 22`, dated 2026-07-04), but `svc.sh install` had never been run and GitHub's side of that registration no longer existed — a half-finished bootstrap, not a live-but-crashed runner. Fix: wipe the stale local credentials, mint a fresh token, re-register, install as a service:
```
gh api -X POST repos/beamwarden/satlab/actions/runners/registration-token --jq .token
# on the Pi, as jeb:
sudo -u satlab-ci bash -c '
  cd ~/actions-runner
  rm -f .runner .credentials .credentials_rsaparams .path .env
  ./config.sh --unattended --url https://github.com/beamwarden/satlab \
      --token <TOKEN> --name beamrider-0004 --labels self-hosted,beamrider-0004 --work _work
'
sudo bash -c 'cd /home/satlab-ci/actions-runner && ./svc.sh install satlab-ci && ./svc.sh start'
```
Runner came online and immediately picked up the hour-old queued job, which then hit the same `/home/jeb` traversal and `safe.directory` gaps as beamrider-0003 (this Pi's `origin` was already HTTPS, so no SSH-key layer here). Run `30504710945` went green on the next attempt: pull → deps → restart → verify.

**Takeaway for next time a workflow file changes:** `install-runner.sh`'s step 2 (`chgrp -R satlab-deploy` + `chmod -R g+w` + `find -type d -exec chmod g+s`) assumes the checkout state at the moment it's run — it doesn't retroactively fix permission drift from files written before or between runs (e.g. that one ref-log file, or `/home/jeb` itself, which the script never touches since it's outside the repo tree). Worth a `find /home/jeb/satlab -exec chgrp satlab-deploy {} \; -exec chmod g+w {} \;` sanity sweep if a deploy ever regresses on a permission error again, rather than re-diagnosing from scratch.

### PR review: #5 and #6 closed as stale, #4 confirmed still blocked

Reviewed all three open PRs against current `main`. #5 (`docs/crosslink-reference`, adds `docs/crosslink-setup.pdf`) turned out to be a byte-identical duplicate of content already on `main` via a separately-merged commit (`d38f807`, same message, same md5sum). #6 (`docs/todo-spacetrack-status`, updates the repo's own `TODO.md`) was a stale draft — `main`'s current `TODO.md` already contains a later revision of the same status update, and the actual work it describes (rebase + merge `feat/orbit-nebody-api`, re-enable `satlab-agent` against ne-body) has long since shipped and is live. Closed both with comments explaining the supersession; branches left intact in case anything needs double-checking.

#4 (`feat(commissioning): add ISM330DHCX hardware-signature pipeline + HMAC health-vector signing`) is the one substantive open PR — `commissioning/` capture/Allan-deviation/fingerprint tooling plus `SATLAB_HW_KEY` wired into `HealthVector.to_payload()`. GitHub still reports it `MERGEABLE` but it's 13 commits behind `develop` (stale check, will need a rebase regardless), and the underlying commissioning run it depends on remains blocked: two ISM330DHCX units can't share one Pi's I2C bus without an ADDR change, cutting/soldering the jumper on the good unit was ruled out, and the second unit is suspected bad. Not merging until that's resolved one way or another.

---

## 2026-05-26

### beamrider-0004 provisioned — Raspberry Pi 5 + Sense HAT → production Beamwarden

Provisioned a new node (beamrider-0004) from bare hardware to live production telemetry in under 30 minutes, including flashing Raspberry Pi OS Trixie (Debian 13) to microSD.

**Hardware:** Raspberry Pi 5, Raspberry Pi Sense HAT stacked on GPIO header.

**Sensors now ingesting to production (app.beamwarden.com):**
- `lsm9ds1` — accel (g), gyro (dps), mag (µT) → subsystem: adcs
- `hts221` — temperature (°C), humidity (%) → subsystem: tcs
- `lps25h` — temperature (°C), pressure (mbar) → subsystem: tcs

All three sensors are onboard the Sense HAT — no external wiring. 10-second ingest cadence. LED matrix shows green on healthy cycle, amber on partial failure, red on full failure.

**New in repo:**
- `sense-agent/` — dedicated agent for beamrider-0004 (main, sense_reader, led_display, beamwarden client)
- `deploy/sense-agent.service` — systemd unit
- `deploy/install-sense-service.sh` — first-time service install
- `deploy/deploy-sense.sh` — subsequent deploys

**Provisioning time benchmark:** bare Pi 5 → green LED + production telemetry in ~30 minutes. Relevant for SBIR demo: single deploy script, no manual steps after `.env` is populated.

**Pi 5 note:** RTIMULib I2C bus may need manual config if IMU fails (`/etc/RTIMULib.ini` → `I2CBus=1`). No issue encountered on this provision.

---

## 2026-05-27

### NUCLEO-144 STM32H753ZI received

Cortex-M7 at 480MHz, 2MB flash (dual-bank), 1MB RAM. Candidate for reaction wheel inner loop controller or dedicated ADCS processor. Role in satlab TBD.

---

## 2026-05-25

### ADCS build document — reaction wheel architecture

Synthesized `docs/adcs-build.md` from the reaction wheel research and original project notes. Documents the full single-axis reaction wheel HIL demonstrator build:

- **Motor:** iPower GM4108H-120T (24N/22P, ~27KV, 10mm hollow shaft) — ~325 RPM at 12V
- **Driver:** SimpleFOC Shield v2 stacked on Arduino Uno Q
- **Encoder:** AS5600 (I2C, 12-bit) + 10×2mm diametrically magnetized magnet on shaft
- **Wire routing decision:** 4 wires (5V, GND, TX, RX) through bore of hollow pivot axle — zero torsion at any platform angle, no slipring needed
- **Control architecture:** inner velocity loop on Uno Q at 100Hz (SimpleFOC), outer attitude loop on RPi agent at ~20Hz (BNO055 quaternion), tumbling FSM on Uno Q (LSM6DSOX gyro)
- **Fallback:** full software stack runs without the pivot frame as a momentum wheel demonstrator

Mermaid architecture diagram rendering resolved: VS Code built-in renderer (`vscode.mermaid-markdown-features`) + yzane markdown-pdf pinned to mermaid v9 via `markdown-pdf.mermaidServer` setting. Removed three conflicting third-party renderers.

Hardware not yet ordered. Parts list and 10-step build sequence documented.

### NUCLEO-144 STM32H753ZI

Read STM32CubeIDE release notes (RN0114, v2.1.1). STM32H7 support mature since v1.3.0; linker script fix in v1.6.0. Board is Cortex-M7 at 480MHz, 2MB flash (dual-bank), 1MB RAM. Relevance to satlab TBD — candidate for reaction wheel inner loop controller or dedicated ADCS processor.

### Adafruit shipment received

Marked operational/on-hand: LSM6DSOX, LSM9DS1, BNO055, Sense HAT, TMAG5273, JST PH cable, short male headers.
