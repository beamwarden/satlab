# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## satlab — Satellite Simulator Lab Station

A hardware-in-the-loop satellite simulator built on a Raspberry Pi (flight computer) and Arduino (subsystem controller). The RPi runs flight software and mission logic; the Arduino reads physical sensors and drives actuators, simulating spacecraft subsystems in real time.

The simulator integrates with **Beamwarden** (the fleet control plane) as a registered Beamrider node, and uses **ne-body** (SGP4/UKF orbital state estimator) for orbit propagation and position overlay.

---

## Phased build plan

**Iteration 1 — Serial/USB (current)**
Arduino reads sensors → sends JSON telemetry over USB serial → RPi agent parses and ingests to Beamwarden.

**Iteration 2 — Radio**
Replace USB serial transport with LoRa radio (Wio Tracker SX1262). Same packet schema; swap the transport layer.

**Iteration 3 — Remote management**
Beamwarden deploys and manages the Beamrider agent on the RPi via SSH/Ansible, mirroring ground station operations. (Distinct from the GitHub Actions self-hosted-runner deploy pipeline described in "CI/CD" below — that's an earlier, simpler mechanism solving the same "deploy without LAN access" problem via push-to-deploy, not Beamwarden-driven.)

---

## Hardware inventory

| Item | Qty | Role | Status |
|---|---|---|---|
| Raspberry Pi 3 (32 GB) | 2 | Flight computer / RPi agent (beamrider-0003) | Operational |
| Raspberry Pi 5 | 1 | Sense HAT node (beamrider-0004) | Operational |
| Arduino Uno R3 | 1 | Primary subsystem controller | Operational |
| Arduino Uno Q | 1 | Secondary / spare | On hand |
| Arduino Sensor Kit | 1 | General sensors | Operational |
| Arduino Modulino Thermo | 1 | TCS (thermal control) | Operational |
| MQ4 Methane Gas Sensor | 2 | Propulsion / atmosphere analog | Operational |
| Adafruit KB2040 | 1 | Auxiliary edge node (CircuitPython/Arduino) | On hand |
| Inventr.io Shields Kit | 1 | Sensor expansion | On hand |
| Inventr.io 37 Sensor Kit | 1 | General sensor suite | On hand |
| Inventr.io Hero Board | 1 | Development board | On hand |
| Canaduino WWVB/MSF 60 kHz Atomic Clock AM receiver | 1 | Precise time reference | Operational |
| XIITIA GY-NEO7mV2 GPS Module | 3 | Orbital position simulation | Operational |
| Meshnology Wio Tracker L1 (SX1262 LoRa + nRF52840, 3000 mAh) | 2 | Iteration 2 radio layer | On hand |
| NUCLEO-144 STM32H753ZI | 1 | Cortex-M7 480MHz eval board — candidate ADCS inner loop controller | On hand |
| Breadboards, connectors, cables, soldering station | — | Integration | On hand |
| ST ISM330DHCX 6DoF IMU | 2 | ADCS hardware signature pair: 0x6A (SA0 low) + 0x6B (SA0 high) on RPi I2C; commissioning + HMAC attestation | Operational |
| Adafruit LSM6DSOX 6DoF IMU (STEMMA QT) | 1 | ADCS primary: accel + gyro, Qwiic/Stemma QT | On hand |
| Adafruit LSM9DS1 9DoF Breakout | 1 | ADCS magnetometer + secondary gyro/accel + temp | On hand |
| Adafruit BNO055 9DoF Absolute Orientation IMU | 1 | ADCS absolute orientation fusion output (quaternions) | On hand |
| Raspberry Pi Sense HAT | 1 | RPi-mounted sensor suite: LSM9DS1 + pressure + humidity + temp + 8x8 LED matrix | On hand |
| Adafruit TMAG5273 3D Hall Effect Magnetometer (STEMMA QT) | 1 | Precision magnetic field sensing | On hand |
| JST PH 2mm 3-Pin Socket to Color Coded Cable - 200mm | 1 | Wiring / connector | On hand |
| Short Male Header Kit for ItsyBitsy | 4 | Headers / integration | On hand |

---

## Subsystem mapping

| Spacecraft subsystem | Sensor | Notes |
|---|---|---|
| ADCS | LSM6DSOX (accel + gyro, STEMMA QT) + LSM9DS1 (magnetometer) + BNO055 (absolute orientation fusion) + ISM330DHCX ×2 (hardware signature commissioning pair) | LSM6DSOX is primary for ongoing telemetry; ISM330DHCX pair (0x6A / 0x6B on RPi I2C) used for noise fingerprinting and HMAC attestation |
| EPS | Light sensor / LDR (solar panel / illumination analog) | |
| TCS | Temp/humidity sensor + Arduino Modulino Thermo + Sense HAT (HTS221 humidity + LPS25H pressure/temp) | Sense HAT adds second independent temperature measurement on the RPi |
| Structural | Air pressure sensor + sound/microphone sensor | |
| Propulsion / atmosphere | MQ4 methane sensor | |
| Orbital position | GY-NEO7mV2 GPS + SGP4 propagation | |
| Time reference | WWVB 60 kHz atomic clock receiver | |
| Local status display | OLED (on Arduino) + Sense HAT 8x8 RGB LED matrix (on RPi) | LED matrix displays health vector state (green/amber/red) |

---

## Repository structure

```
satlab/
├── arduino/
│   └── subsystem_sim/
│       └── subsystem_sim.ino   # Sensor reads → JSON over serial
├── agent/
│   ├── main.py                 # Entry point
│   ├── serial_reader.py        # pySerial interface to Arduino
│   ├── beamwarden.py           # Beamwarden ingest client
│   ├── orbit.py                # SGP4 orbit propagation (ne-body heritage)
│   └── requirements.txt
├── commissioning/              # ISM330DHCX hardware signature experiment
│   ├── ism330dhcx.py           # Direct I2C driver (smbus2, no library dependency)
│   ├── capture.py              # High-rate dual-unit data collection
│   ├── allan.py                # Overlapping Allan deviation computation
│   ├── fingerprint.py          # ADEV fingerprint extraction and HMAC key derivation
│   ├── commission.py           # Orchestrate: capture → fingerprint → save
│   ├── verify.py               # Re-measure and compare to baseline
│   └── requirements.txt        # smbus2, numpy
└── docs/
    ├── hardware.md             # Wiring and pin mapping
    └── subsystem-map.md        # Sensor → subsystem mapping detail
```

---

## Serial protocol

**Baud rate: 9600** — matches realistic spacecraft UART housekeeping rates and is consistent with the SBIR's ≤1 kbps cross-link budget. The Wio Tracker SX1262 LoRa link (iteration 2) operates near this rate at reliable range settings (SF10/BW125 ≈ 980 bps). Designing to it in iteration 1 avoids format rework at radio integration.

Arduino sends newline-delimited JSON at a fixed interval (default 10 s):

```json
{"ts":"T+30s","subsystem":"tcs","sensor":"dht","payload":{"temp_c":23.4,"humidity_pct":45.1}}
```

The `ts` field is a boot-relative placeholder — the RPi agent replaces it with wall-clock UTC before ingesting to Beamwarden.

**Iteration 2 note:** JSON is acceptable over USB. For the LoRa link, the verbose field names will approach the SBIR's ≤256-byte binary health vector budget. The packet schema will need to move to compact keys or a binary struct at that transition.

---

## Environment variables

```
SATLAB_SERIAL_PORT    Serial device (e.g. /dev/ttyUSB0 or /dev/ttyACM0)
BEAMWARDEN_URL        Base URL of Beamwarden instance
BEAMWARDEN_TOKEN      Beamrider bearer token from Beamwarden
SATLAB_NORAD_ID       NORAD ID to propagate (default: 25544 — ISS)
NEBODY_URL            Base URL of the ne-body API (e.g. http://keep-0001:8000)
NEBODY_API_KEY        (optional) API key for ne-body's auth middleware
SATLAB_HW_KEY         64-char hex HMAC key derived during ISM330DHCX commissioning;
                      printed by commission.py. If set, each HealthVector publish
                      includes an HMAC-SHA256 tag binding node_id + sequence to
                      the physical hardware signature.
```

TLE source is the ne-body cache endpoint (`GET {NEBODY_URL}/tle/{norad_id}/latest`). ne-body polls Space-Track hourly; satlab reads from ne-body's cache every 3600 s. The agent falls back to a bundled ISS TLE if `NEBODY_URL` is unset or ne-body is unreachable. satlab no longer requires Space-Track credentials.

---

## Hardware signature commissioning (ISM330DHCX)

Both ISM330DHCX units connect to the RPi I2C bus (i2c-1 on RPi 3/4, check with `sudo i2cdetect -y 1`):
- Unit 0: SA0 pin to GND → address 0x6A
- Unit 1: SA0 pin to 3.3V → address 0x6B

Run once after wiring. Takes ~120 s. Run from beamrider-0003 with the agent stopped.

```bash
# 1. Install commissioning deps
pip install -r commissioning/requirements.txt --break-system-packages

# 2. Verify both units are visible on the bus
sudo i2cdetect -y 1   # expect 0x6A and 0x6B to appear

# 3. Run commissioning (2 min capture + fingerprint computation)
cd commissioning && python commission.py --bus 1 --duration 120 --out ~/commissioning_output

# 4. Register fingerprint with Beamwarden (on beamwarden host)
python manage.py set_hw_signature beamrider-0003 ~/commissioning_output/fingerprint.json

# 5. Add hw key to agent .env (printed by commission.py)
echo "SATLAB_HW_KEY=<printed-hex>" >> ~/satlab/.env

# 6. Periodic verification (optional; 30 s)
python commissioning/verify.py --baseline ~/commissioning_output/fingerprint.json
```

The agent reads `SATLAB_HW_KEY` at startup. If set, each HealthVector publish includes
`hmac_tag = HMAC-SHA256(hw_key, "{node_id}:{sequence}")[:32]`.

---

## RPi setup (Beamrider-0003)

**Hardware:** Raspberry Pi 3 Model B Rev 1.2, Debian GNU/Linux 12 (Bookworm) — repo cloned at `~/satlab`

```bash
# 1. Install Python deps (Bookworm ships Python 3.11)
pip install -r agent/requirements.txt --break-system-packages

# 2. Add jeb to dialout group for serial port access (once; requires re-login)
sudo usermod -aG dialout jeb

# 3. Identify the Arduino serial device after plugging in USB
ls /dev/ttyACM* /dev/ttyUSB*

# 4. Set environment variables
export SATLAB_SERIAL_PORT=/dev/ttyACM0   # adjust if needed
export BEAMWARDEN_URL=http://<beamwarden-host>:8000
export BEAMWARDEN_TOKEN=<token-from-beamwarden>
export SATLAB_NORAD_ID=25544
export NEBODY_URL=http://keep-0001:8001          # ne-body backend port; falls back to 192.168.1.206:8001 if hostname resolution fails
export NEBODY_API_KEY=<key-if-nebody-auth-enabled>  # omit if ne-body runs without auth

# 5. Run the agent
cd agent && python main.py
```

Register beamrider-0003 in Beamwarden (admin UI or API) before running the agent to obtain the bearer token.

**Continuous deployment:** see "CI/CD" below — after the one-time bootstrap, pushes to `main` touching `agent/**` deploy automatically.

---

## RPi setup (Beamrider-0004 — Sense HAT node)

**Hardware:** Raspberry Pi 5, Debian GNU/Linux 13 (Trixie), Raspberry Pi Sense HAT stacked on GPIO header. Runs `sense-agent/main.py` — no Arduino, no serial, no orbit propagation.

**Pi 5 / Sense HAT I2C note:** On Pi 5, the GPIO header I2C bus is still i2c-1, but RTIMULib may auto-detect the wrong bus. If IMU reads fail, check which bus has the sensors (`sudo i2cdetect -y 1` vs `-y 4`) and edit `/etc/RTIMULib.ini` → set `I2CBus=1` (or whichever bus responds). The apt `sense-hat` package on Trixie is Pi 5 compatible.

```bash
# 1. Enable I2C and SPI (required for Sense HAT sensors and LED matrix)
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# 2. Install sense-hat via apt (installs RTIMULib2 and kernel driver; do NOT pip-install)
sudo apt install sense-hat

# 3. Clone the repo
git clone https://github.com/<org>/satlab ~/satlab

# 4. Install Python deps (httpx only; sense-hat is already installed via apt)
pip install -r ~/satlab/sense-agent/requirements.txt --break-system-packages

# 5. Populate the env file
cat > ~/satlab/.env <<EOF
BEAMWARDEN_URL=https://<beamwarden-host>
BEAMWARDEN_TOKEN=<token-from-beamwarden-for-beamrider-0004>
EOF

# 6. Run the agent (verify sensors before installing service)
cd ~/satlab/sense-agent && python3 main.py
```

Register beamrider-0004 in Beamwarden and add three sensors before running: `lsm9ds1` (adcs), `hts221` (tcs), `lps25h` (tcs). Then obtain the bearer token.

First-time service install (from dev machine, after Pi is reachable):
```bash
./deploy/install-sense-service.sh --host beamrider-0004.local
```

Subsequent deploys:
```bash
./deploy/deploy-sense.sh
```

**LED matrix health indicator:** green = all sensors ingesting OK, amber = partial failure, red = all sensors failed or Beamwarden unreachable.

**Continuous deployment:** see "CI/CD" below — after the one-time bootstrap, pushes to `main` touching `sense-agent/**` deploy automatically.

---

## CI/CD (GitHub Actions self-hosted runner)

Routine deploys to both Pis happen automatically via GitHub Actions on push to `main` — no LAN/SSH access needed once set up. `.github/workflows/deploy-agent.yml` and `.github/workflows/deploy-sense-agent.yml` each run on a self-hosted runner living on the target Pi itself (labels `beamrider-0003` / `beamrider-0004`); the runner dials **out** to GitHub, so this works regardless of where the developer is physically. Each workflow reproduces the existing manual deploy scripts' logic (`git pull --ff-only`, `pip install --break-system-packages`, `systemctl restart`, verify) as plain shell steps against the live `/home/jeb/satlab` checkout — deliberately not `actions/checkout`, to avoid its `git clean` semantics wiping the untracked, manually-populated `.env`.

**Security note — this repo is public.** Self-hosted runners on public repos are a known risk: a `pull_request`/`pull_request_target`-triggered workflow from a forked PR would get code execution on the runner. Both workflows here trigger on `push` only, never `pull_request`/`pull_request_target` — push events on `main` only fire for actors who already have write access, so this cannot be triggered by an external contributor. Defense in depth beyond that: the runner on each Pi runs as a dedicated low-privilege `satlab-ci` system user (not `jeb`, which has sudo + `dialout`), with a sudoers grant scoped to exactly `systemctl restart <service>` / `systemctl is-active <service>` — see `deploy/satlab-ci.sudoers.tmpl`. GitHub Environments (`beamrider-0003`, `beamrider-0004`) with required reviewers add a manual approval click per deploy.

**Why `main`, not `develop`:** `main` was previously unused as an integration branch (no merge history). It was adopted deliberately as the deploy gate so a bad push requires a conscious develop→main promotion before it reaches live hardware with a serial-attached Arduino and rate-limited Space-Track credentials, rather than firing on every WIP commit.

**One-time bootstrap** (requires the Pi to be reachable — SSH/LAN or equivalent; cannot be done remotely otherwise): `deploy/install-runner.sh --host <pi>.local --label <beamrider-0003|beamrider-0004> --token <REG_TOKEN>`, where `<REG_TOKEN>` is generated fresh (short-lived, ~1hr) via `gh api -X POST repos/beamwarden/satlab/actions/runners/registration-token --jq .token`. See the script's header comment for the full step list.

`deploy/deploy.sh` and `deploy/deploy-sense.sh` remain as the documented manual fallback — see their header comments for when to use them instead of waiting on CI.

---

## Arduino development (on beamrider-0003)

Sketches are compiled and uploaded directly from the RPi using **arduino-cli**. Kill the satlab agent before uploading (it holds the serial port).

```bash
arduino-cli compile --fqbn arduino:avr:uno /path/to/sketch && \
arduino-cli upload --fqbn arduino:avr:uno -p /dev/ttyACM0 /path/to/sketch && \
sleep 3 && \
python3 -c "
import serial, time
s = serial.Serial('/dev/ttyACM0', 9600, timeout=5)
time.sleep(2)
for _ in range(20):
    line = s.readline().decode('utf-8', errors='replace').strip()
    if line: print(line)
"
```

Sketches can be compiled from the repo path directly (e.g. `~/satlab/arduino/subsystem_sim`) or copied to `/tmp` first. Read at least 20 lines — diagnostic sketches emit multi-line output and the critical values appear after the I2C scan.

Install a library:
```bash
arduino-cli lib install "Adafruit AHTX0"
```

---

## Related systems

- **Beamwarden** — `http://localhost:8000` (local) or KEEP-0001. satlab registers as a Beamrider node.
- **ne-body** — SGP4 propagation and TLE cache endpoint. satlab pulls TLEs from ne-body's `/tle/{norad_id}/latest` endpoint rather than polling Space-Track directly.
