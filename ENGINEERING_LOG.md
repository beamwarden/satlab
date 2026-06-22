# Engineering Log — satlab

Narrative record of daily progress, decisions, and open threads.
Most recent entry first.

---

## 2026-06-22

### Print session (Jun 18) — Z offset failure + nozzle replacement

**Objective:** print `cad/print_test_coupon.scad` on new PEI flex plate, measure with calipers, validate hole fit.

**What happened:** PEI plate seated and bed re-leveled. Print started. Nozzle was not reaching the bed — extruding in mid-air. Root cause: the Z endstop position was not adjusted after plate installation. The leveling procedure sets the bed level relative to wherever Z=0 is, but Z=0 is defined by the physical endstop switch position. The PEI plate (magnetic base sheet + spring steel sheet) adds roughly 3mm of total height above the bare aluminum bed. The endstop switch was not lowered to compensate, so the printer homes with the nozzle ~3mm above the new print surface.

Mid-air extrusion produced a blob on the nozzle tip. Nozzle clogged. Cold-pull and manual push did not clear it. Nozzle removed and replaced.

**Nozzle replacement procedure (hot swap):**
- Raised temp to 260°C to soften any heat-creep bond between nozzle and heatbreak shoulder
- Removed old nozzle at 260°C with wrench; hot block held with cloth
- New MK8 nozzle threaded in finger-tight at temperature
- Cooled to 200°C; final torque snug (not overtorqued — sealing against heatbreak shoulder)
- Do not tighten cold: nozzle contracts on cooling and will unseat the seal

**Session outcome:** nozzle is fresh and printer is in a known state. No coupon print completed.

### Next print session — Z offset calibration required before printing

The Z endstop needs physical adjustment or a software offset. Preferred path (software, fastest):

1. Start a print (test coupon is fine)
2. As first layer begins, navigate to Tune → Z Offset on LCD
3. Baby-step the Z offset negative (down) in 0.05mm increments until filament squishes visibly onto PEI surface
4. Good first layer: thin, slightly flattened bead, no gaps, sticks immediately
5. Save offset with M500 from terminal or via LCD
6. Let print complete; flex plate cold to pop coupon; measure with calipers

Hardware option (permanent, avoids saved offset dependency): loosen Z endstop switch mounting screw, slide switch down ~3mm, re-home, verify nozzle just kisses bed at Z=0.

### Track 3 hardware arrivals (Jun 18–19)

| Item | Status |
|---|---|
| UMLIFE AS5600 3-pack with 10×2mm magnets | On hand |
| 608ZZ bearings 10-pack (8×22×7mm) | On hand |
| SimpleFOC Shield v2 (IR2104 gate drivers, INA240 current sensors) | On hand |

GM4108H-120T still in transit (est. Jun 30–Jul 9). All other Track 3 hardware is on hand. M8 bolts + nuts still needed from hardware store.

### DigiKey order arrived — Track 1 blocker cleared

DigiKey package arrived 2026-06-22 (two days early vs. est. Jun 23–25). Contents confirmed:

| Item | Status |
|---|---|
| SparkFun Qwiic pHAT v2.0 for Raspberry Pi (DEV-15945) | On hand |
| SAC0307 0.6mm lead-free solder wire (Olimex) | On hand |
| Chip Quik no-clean flux pen CQ4LF (0.34 oz) | On hand |

Track 1 hardware is now complete. No remaining blockers before commissioning can begin.

**Next commissioning steps:**
1. Solder bridge the ADDR pad on SEN-20176 Unit A → address 0x6A
2. Install Qwiic pHAT on beamrider-0003 GPIO header
3. Connect both SEN-20176 units via Qwiic cables to pHAT
4. Verify `sudo i2cdetect -y 1` shows both 0x6A and 0x6B
5. Run `python commissioning/commission.py --bus 1 --duration 120`

`what.md` and `hardware-inventory.md` updated to reflect arrival and clear the blocker.

### Open threads

- Track 1: No blocker. Ready to commission when bench time available.
- Track 3: Z offset calibration blocks coupon print; coupon print blocks flywheel print; GM4108H blocks motor mount CAD finalization.
- M8 hardware: hardware store errand, not ordered.

---

## 2026-06-17

### Hardware inventory audit — ISM330DHCX form factor corrected

Receipt cross-reference (SparkFun order #000294857, May 18 2026) confirmed both ISM330DHCX units are **SparkFun Micro 6DoF IMU SEN-20176 breakout boards**, not bare ST chips. The inventory entry "ST ISM330DHCX ×2" was a mislabel carried forward from the original procurement plan. Both units on hand.

Consequence for Track 1 wiring: the SEN-20176 does not expose SA0 as a through-hole pin. Address is set via a solder jumper (ADDR pad) on the back of the board:
- Unit A: bridge ADDR pad with solder → I2C address 0x6A
- Unit B: leave ADDR pad open (factory default) → I2C address 0x6B

Both units connect to RPi i2c-1 via Qwiic cable (to Qwiic pHAT); no bare wire to SA0 needed. `what.md` Track 1 remaining steps updated accordingly.

### Track 1 blocker identified and ordered

SparkFun Qwiic pHAT v2.0 (DEV-15945) was missing from inventory and is required to route Qwiic connectors to the RPi I2C header cleanly. Backordered at SparkFun; sourced from DigiKey. Same DigiKey order includes SAC0307 0.6mm solder and Chip Quik no-clean flux pen for the ADDR jumper bridge operation. Est. delivery Jun 23–25.

### Track 3 hardware procurement complete

All Track 3 hardware ordered via Amazon:

| Item | Source | Est. Delivery |
|---|---|---|
| iPower GM4108H-120T (hollow shaft, without slipring) | Amazon | Jun 30–Jul 9 |
| SimpleFOC shield (IR2104 gate drivers, INA240 current sensors) | Amazon | Jun 19 |
| UMLIFE AS5600 3-pack (12-bit I2C, with 10×2mm magnets) | Amazon | Jun 18 |
| 608ZZ bearings 10-pack (8×22×7mm) | Amazon | Jun 18 |

SimpleFOC shield verified compatible: IR2104 half-bridge drivers (3× for 3-phase), INA240 high-precision current sensors (A/B phase), Arduino Uno shield form factor, power input DC 12–35V, SimpleFOC v2.0.4 explicitly cited. IR2104 voltage jumper: leave at left position for VCC ≤ 20V operation with GM4108H.

AS5600 3-pack with magnets: 1 unit allocated to Track 3 reaction wheel; 2 spare for Track 5 ADCS sensor suite. Magnet confirmed included in listing (pictured).

GM4108H delivery Jun 30–Jul 9 is the long pole for Track 3. M8 bolts + nuts (flywheel tuning masses) still needed from hardware store before flywheel print.

### Tomorrow — test print session plan

**Objective:** validate print quality and hole fit on the new PEI flex plate before committing to the ~2 h flywheel print.

**Step 1 — Install PEI flex plate (prerequisite)**
- Clean bare aluminum bed with IPA; allow to dry fully
- Seat adhesive magnetic base sheet, smooth out bubbles from center outward
- Re-level bed: four-corner paper drag, then center check
- Do not skip leveling — first layer on new surface will differ from prior calibration

**Step 2 — Print test coupon**
- File: `cad/print_test_coupon.scad` (40×20×6mm, M8 + M3 holes)
- Slice at 0.20mm layer height, 20% infill, 3 perimeter walls, supports off
- Let cool completely on plate before removal; flex plate off printer, bend to pop part

**Step 3 — Measure with calipers**

| Dimension | Nominal | Pass if within |
|---|---|---|
| X length | 40.0mm | ±0.3mm |
| Y width | 20.0mm | ±0.3mm |
| Z height | 6.0mm | ±0.3mm |
| M8 hole diameter | 8.5mm | ±0.2mm |
| M3 hole diameter | 3.4mm | ±0.15mm |

Z height is the primary concern: prior coupon eyeballed ~4mm vs 6mm modeled (part was damaged on removal, so unreliable). A clean measurement resolves whether the gap is a slicer setting, Z steps/mm, or first-layer over-squish.

**Step 4 — Diagnose Z if short**
- Check slicer layer count × layer height = expected Z
- If layer count is correct but Z is short: Z steps/mm may need calibration (`M92 Z<value>`, measure, iterate)
- If top surface is open/hairy: increase top layer count in slicer (3 → 5 solid layers)
- If first layer is visibly over-squished (elephant foot): back off Z offset 0.05mm at a time

**Step 5 — Decision gate**
- X/Y/Z and holes all within tolerance: commit `cad/` files, proceed to flywheel print planning
- Any dimension out: iterate on slicer or calibration, reprint coupon before touching flywheel

### Open threads

- Track 1: Qwiic pHAT delivery (~Jun 23) unblocks commissioning
- Track 3: GM4108H delivery (~Jul 9) is critical path; flywheel CAD bolt pattern unverified until motor arrives
- M8 hardware still needed from hardware store
- PEI plate leveling required before tomorrow's prints

---

## 2026-06-16

### ISM330DHCX ×2 received — hardware signature commissioning stack built

Second ISM330DHCX arrived, completing the redundant pair. Both units now on hand and
can share the RPi I2C bus via SA0 pin strapping: unit 0 at 0x6A (SA0 low), unit 1 at
0x6B (SA0 high). The ISM330DHCX is a significant step up from the LIS3DH currently in
the Arduino sketch: 6-DoF industrial-grade, ±125 dps gyro range, 0.061 mg/LSB accel,
104 Hz ODR easily achievable over I2C.

**Context from prior sensor fingerprint experiment (2026-06-07 worklog entry):**
The beamwarden-side fingerprint experiment showed that static bias offset drifts enough
within three weeks to collapse same-model (ISM330DHCX) test accuracy to ~61%. The key
insight was that bias is not a stable identity primitive. The overlapping Allan deviation
(OADEV) noise floor -- ARW, bias instability, rate random walk -- is a physical property
of the die and is stable over time; it doesn't drift in the way a bias offset does. This
session implements the OADEV-based approach that the 2026-06-07 entry marked as deferred.

**Cross-repo research before building:**
Searched satlab, beamwarden, beamrider-agent, ne-body for existing auth hooks and
fingerprinting primitives. Findings: Beamwarden auth is token-only; `Beamrider.metadata`
(JSONField) already exists and is the right place to store commissioned fingerprints;
`HealthVector.hmac_tag` in `agent/health.py` was explicitly deferred and is the natural
attestation insertion point; `Beamrider.serial_number` exists but is set by the operator,
not derived from hardware. No noise characterization existed anywhere.

**Full commissioning stack built (`satlab/commissioning/`):**

- `ism330dhcx.py` — direct smbus2 driver; no library dependency. Reads WHO_AM_I (0x6B),
  configures CTRL1_XL (ODR=104 Hz, ±2g) and CTRL2_G (ODR=104 Hz, ±125 dps via FS_125
  bit), reads 12-byte block from OUTX_L_G. STATUS_REG polling to avoid busy-reading
  stale data. Sensitivity: 0.061 mg/LSB accel, 4.375 mdps/LSB gyro.

- `capture.py` — interleaved STATUS_REG poll loop for both units on the same bus.
  At 104 Hz (9.6 ms/sample), two I2C reads + status checks fit comfortably within the
  ODR window at 100 kHz bus speed. Saves timestamped 6-channel arrays to `.npz`.
  Progress printed every 10 s. Target duration: 120 s (12480 samples per unit).

- `allan.py` — overlapping Allan variance (OADEV) from phase sequence.
  `AVAR(tau) = mean((x[j+2m] - 2x[j+m] + x[j])^2) / (2*tau^2)`.
  Tau points spaced logarithmically (20% step). For white noise with std sigma,
  ADEV(tau) = sigma*sqrt(tau0/tau) — slope -1/2 on log-log; verified analytically.

- `fingerprint.py` — ADEV evaluated at fixed tau points [0.1, 0.3, 1.0, 3.0, 10.0, 30.0] s
  per channel (6 channels × 6 taus = 36 values per unit). Fingerprint hash = SHA-256 of
  flattened vector at 4-decimal scientific notation. HMAC key = SHA-256 of concatenated
  hashes from both units (32 bytes). Cosine distance and MAPE provided for
  distinguishability reporting and ongoing verification respectively.

- `commission.py` — orchestrates: capture (120 s) → fingerprints → saves `fingerprint.json`
  (Beamwarden-safe, no key) + prints `SATLAB_HW_KEY=<hex>` for operator to add to .env.

- `verify.py` — 30 s re-capture (covers taus [0.1, 0.3, 1.0, 3.0] s), MAPE vs baseline.
  Threshold 15%. Exit code 0/1 for scripted checks.

**Beamwarden management command (`set_hw_signature`):**
Loads `fingerprint.json` into `Beamrider.metadata["hw_signature"]` via `update_fields`.
Preserves existing metadata. Guards against accidentally storing `hw_key_hex` server-side
(raises CommandError if the field appears in the JSON -- it should never leave the device).

**`agent/health.py` HMAC tag:**
`_HW_KEY` loaded at module import from `SATLAB_HW_KEY` env. If present, `to_payload()`
computes `HMAC-SHA256(hw_key, "{node_id}:{sequence}")[:32]` and writes it to `hmac_tag`.
Zero behavioral change if env var is absent -- the existing `None` default is preserved.
The HMAC binds the physical hardware (via key derived from fingerprint) to the sequence
number; replay of old packets is caught by the sequence counter.

**Security model:**
If an attacker physically substitutes a unit, the noise fingerprint changes at the next
commissioning-tier check, the derived key mismatches, and HMAC tags diverge. Beamwarden
does not yet verify the HMAC server-side -- it stores the tag alongside the health vector
reading. Server-side verification is the next step: compare the incoming `hmac_tag`
against `HMAC-SHA256(Beamrider.metadata["hw_signature"]["...hw_key..."], msg)`. The
key is never sent over the wire; it is commissioned locally and stored only on the device.

**CLAUDE.md updated:** ISM330DHCX ×2 added to hardware inventory table and subsystem
mapping (ADCS row). `SATLAB_HW_KEY` added to env vars section. `commissioning/` added to
repo structure tree. Full commissioning runbook added as a new section.

### Open threads

- **Hardware not yet wired:** SA0 pin strapping and I2C connections to RPi i2c-1 header
  still need to be made. Verify with `sudo i2cdetect -y 1` before running commission.py.
- **Actual distinguishability unknown:** cosine distance between the two dies will be
  measured at commissioning time. Prior LIS3DH vs LSM9DS1 result was 99-100% accuracy
  (different chip models; trivially distinguishable). Same-model ISM330DHCX die
  distinguishability is the open empirical question this experiment answers.
- **MAPE threshold unvalidated:** 15% was chosen as a reasonable starting point.
  After the first commissioning run, MAPE distribution across 3-4 verify captures will
  establish the empirical baseline for threshold calibration.
- **Server-side HMAC verification not yet built:** Beamwarden stores the tag but does
  not verify it. The verification path requires a Beamwarden API endpoint or background
  task that reads `Beamrider.metadata["hw_key_hex"]` -- but this contradicts the
  current design (key stays local). Better approach: Beamwarden stores the fingerprint
  hash, not the key; verification is a local-only operation run by the operator.
  Revisit the trust model before implementing Beamwarden-side verification.

### beamrider-0004 amber/red incident — Beamwarden ingest timeouts

LED matrix transitioned amber then red during normal operation (evening, 2026-06-15). Log review via `journalctl -u sense-agent` confirmed sensors were healthy throughout: all three channels (lsm9ds1, hts221, lps25h) were cycling ok=3 fail=0 up to 21:12:57.

Root cause: `app.beamwarden.com/api/v1/ingest/` POST requests began timing out at 21:13:17. Network or Beamwarden-side issue; the Pi and I2C sensors were nominal throughout.

| Time | Event |
|---|---|
| 21:12:57 | Last clean cycle: ok=3 fail=0 |
| 21:13:17 | First timeout (attempt 1/2); one sensor retried successfully → LED amber |
| 21:14:39 | ok=1 fail=2 |
| 21:15:53 | ok=0 fail=3 → LED red |

The LED health indicator behaved correctly: amber on partial ingest failure, red on total failure. No code changes required. If this recurs, check Beamwarden Cloud Run instance health and ingest endpoint latency before assuming a Pi-side fault.

---

### RTL-SDR ground station intent identified from what.md

Reviewed `what.md` (original project scoping document). The two Raspberry Pi 4s and RTL-SDR Blog V3 R860 dipole antenna kit on hand were earmarked for a ground station node: RPi 4 + RTL-SDR receiving real or CubeSatSim-broadcast satellite signals on 433 MHz, closing the transmit/receive loop with the flight-side simulator and ingesting received signal data to Beamwarden as a Beamrider node.

Reference cited in what.md: github.com/alanbjohnston/CubeSatSim (broadcasts simulated telemetry over FM/Morse; RTL-SDR ground station receives it). This was never started. The build proceeded directly to USB-serial (iteration 1) and then the Sense HAT node. RPi 4s and RTL-SDR remain unallocated.

Candidate next hardware build: RPi 4 + RTL-SDR V3 + dipole as a dedicated ground station iteration, completing the satlab signal chain: Arduino sensors → flight computer → LoRa/RF → ground station → Beamwarden.

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
