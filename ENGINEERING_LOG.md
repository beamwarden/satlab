# Engineering Log — satlab

Narrative record of daily progress, decisions, and open threads.
Most recent entry first.

---

## 2026-06-05

### Ender 3 online; reaction-wheel flywheel CAD started; print pipeline shaken out

3D printer (Creality Ender 3) brought up and confirmed printing. This unblocks
the two 3D-printed parts in the reaction-wheel build (flywheel, pivot frame) —
previously the only items in that build with no fabrication path.

**CAD heritage — charleslabs reaction wheel (`gaspode-wonder/reaction_wheel`, MIT).**
Cloned to `~/git/reaction_wheel` for reference. This is the exact project
`docs/reaction-wheel.md` already cites. Findings on what transfers to satlab:

- **Electronics/firmware do NOT transfer.** Their design is a NEMA 17 **stepper**
  + DRV8825 + MPU6050. satlab is GM4108H **BLDC gimbal** + SimpleFOC + AS5600 +
  BNO055/LSM6DSOX. Different motor class entirely.
- **Flywheel concept transfers.** Their wheel (130 mm OD × 16 mm) tunes inertia
  with 3× M8 bolts/nuts slid in the rim — the "adjustable hardware placement"
  approach our Open questions cite.
- **Motor holder does NOT transfer** — bored for a NEMA 17 square face; needs a
  from-scratch holder for the round GM4108H.
- **Control heritage (informative).** Their `PID.h`/`.ino` confirm the cascaded
  PID + tumbling-FSM structure: attitude gains P=2.5, I=0, D=400; angle error
  wrapped to ±180°; **FSM hysteresis** — drop to detumble above 360 °/s,
  re-engage attitude hold below 45 °/s. Adopt the hysteresis band (not a single
  threshold) for our `NOMINAL`/`TUMBLING` FSM to avoid chatter.

**New files (working tree, not yet committed):**

- `cad/flywheel_gm4108h.scad` — parametric rim-loaded flywheel for the GM4108H
  (default 120 mm OD, 16 mm rim). Bolts to the rotor bell; shaft end reserved for
  the AS5600 magnet. Ring of M8 pockets for adjustable tuning masses. Rotor
  bolt pattern is a **placeholder** — the GM4108H is still on the to-acquire list,
  so `mount_*`/`boss_*` cannot be verified yet.
- `cad/print_test_coupon.scad` — 40×20×6 mm fit/calibration coupon carrying the
  flywheel's M8 (8.5 mm) and M3 (3.4 mm + counterbore) hole specs, so hole fit can
  be validated before committing to the ~2 h flywheel print.

Both render clean (manifold, `Simple: yes`) via OpenSCAD 2021.01.

**`docs/reaction-wheel.md` updated:** added "3D printed parts" section (CAD
heritage table, control-gain reference, flywheel/motor-holder/pivot-frame notes,
`openscad` render command), expanded acronyms on first use, updated the flywheel
Open question to point at the new model.

**Print pipeline shake-out (first-time bring-up, all resolved):**

- **"SD init fail"** → card was 64 GB **exFAT**. Stock Ender 3 board reads only
  **FAT32**, and SDXC (>32 GB) can fail at init regardless of FS. Reformatted the
  card FAT32 (MBR) and it read fine. *Standing recommendation: keep a ≤32 GB
  FAT32 card for this printer.*
- **First layer** walked through both failure modes: nozzle too high (stringy,
  non-bonded web) → over-corrected too low (heavy paper drag, nothing extruding,
  bed blocking the nozzle) → backed off to **light paper drag**, which printed
  cleanly. Hotend confirmed healthy by extruding in mid-air.
- **Bed surface is rigid (not the flexible magnetic mat).** A bonded coupon was
  destroyed on removal, and the stock surface was damaged in the process.

**Decision: replace the bed surface with a 235×235 magnetic textured-PEI flex
plate** (IdeaFormer textured, two-part: adhesive magnetic base + spring-steel PEI
sheet). Flex-and-pop removal eliminates the destroy-on-removal failure. To be
ordered; install requires cleaning the bare aluminum bed (IPA) and re-leveling.

### Open threads

- **Commit held:** `cad/` files + `docs/reaction-wheel.md` edits are uncommitted,
  pending a verified test-coupon print on the new plate.
- **Coupon Z height suspect:** destroyed coupon eyeballed ~4 mm vs the modeled
  6 mm — but the part was mangled on removal, so the reading is unreliable.
  Re-measure a clean coupon (calipers, all 3 axes). If X/Y are right but Z is
  short, suspect over-squished first layers, unclosed top layers (the print
  showed a hairy/open top), or Z steps/mm — investigate then.
- **Flywheel bolt pattern unverified** until the GM4108H is acquired and the
  rotor bolt-circle/boss measured.
- **Log duplication:** this session's entry landed in the root
  `ENGINEERING_LOG.md` (narrative log); `docs/engineering-log.md` (detailed,
  file-level log) does not yet have a matching entry. Both logs are maintained —
  a merge into a single log is planned.

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
