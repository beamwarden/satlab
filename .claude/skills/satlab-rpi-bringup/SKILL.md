---
name: satlab-rpi-bringup
description: Bring-up steps for satlab's Raspberry Pi nodes (beamrider-0003 flight computer, beamrider-0004 Sense HAT node) — package installs, env vars, service registration, Pi 5 I2C bus quirk. Use when setting up, redeploying, or troubleshooting an RPi node.
---

Migrated from the project's CLAUDE.md 2026-08-10 (moved out of always-loaded context — only needed during hardware bring-up, not every session).

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
export SPACETRACK_USER=<email>
export SPACETRACK_PASS=<password>

# 5. Run the agent
cd agent && python main.py
```

Register beamrider-0003 in Beamwarden (admin UI or API) before running the agent to obtain the bearer token.

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
