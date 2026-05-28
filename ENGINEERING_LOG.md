# Engineering Log — satlab

Narrative record of daily progress, decisions, and open threads.
Most recent entry first.

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
