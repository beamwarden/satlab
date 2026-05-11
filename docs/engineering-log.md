# satlab Engineering Log

Entries in descending order — most recent first.

---

## 2026-05-09 — Tier 1 thresholds, health vector schema, cross-link planning

**Status:** Agent extended from telemetry forwarder to sense-assess-act loop.
Wio Tracker cross-link hardware identified and setup checklist written.

### Architecture decision: Python prototype through Tier 2/3, C++ on SBIR award

satlab is now explicitly building toward the Beamrider agent architecture
described in EXPAND.3.S26B. The Python implementation is the reference
prototype; a C++ port targeting ARM Cortex-A / LEON4 is deferred until
Phase II hardware is selected.

### New files

**`agent/thresholds.py`** — Tier 1 threshold evaluation engine.
Pure functions; no state. `evaluate(sensor_name, payload)` returns a list
of `ThresholdViolation` objects (level: SOFT or HARD, field, value, message).
Evaluators defined for all six sensor streams:

| Sensor | Key thresholds |
|---|---|
| `eps_light` | pct <5 (soft), >90 (soft) |
| `structural_sound` | raw >700 (soft), >950 (hard) |
| `tcs_dht` | temp_c <15/>35 (soft), <5/>45 (hard); humidity_pct >75 (soft), >90 (hard) |
| `structural_bmp280` | pressure_hpa <990/>1030 (soft), <960/>1050 (hard); temp same as tcs |
| `adcs_lis3dh` | vector magnitude \|‖g‖−1.0\|>0.20 (soft), >0.50 (hard) |
| `orbit_sgp4` | error_code ≠ 0 (hard) |

ADCS thresholds on total g-vector magnitude rather than per-axis to remain
robust to any bench mounting orientation.

**`agent/health.py`** — Health vector schema and subsystem state machine.

- `NodeState`: NOMINAL / DEGRADED / CRITICAL / SAFE_MODE / SILENT
- `SubsystemState`: NOMINAL / DEGRADED / CRITICAL / UNKNOWN
- `SubsystemHealth`: tracks per-sensor violations independently (structural
  subsystem accumulates from both `structural_sound` and `structural_bmp280`);
  maintains `ae_score` [0,1] anomaly evidence accumulator with decay 0.85/cycle
- `HealthVector`: node_id (from `SATLAB_NODE_ID` env var or generated UUID),
  sequence, top-level state, per-subsystem health, mission_capability [0,1],
  available_for_tasking, nis_summaries (Tier 3 placeholder), hmac_tag (deferred)

Subsystem weights for `mission_capability`: ADCS 30%, EPS 25%, TCS 20%,
Structural 15%, Orbit 10%.

### Modified files

**`agent/main.py`** — Wired Tier 1 + health vector into the main loop.
Agent now runs a full sense-assess-publish cycle:

1. Ingest serial packet to Beamwarden (unchanged)
2. Run `evaluate()` against the payload
3. Update `SubsystemHealth` via `vector.record_sensor()`
4. On orbit interval (30 s): push `orbit_sgp4`, evaluate orbit, push `health_vector`
5. Health vector published at 30 s nominal / 10 s DEGRADED or CRITICAL

Hard violations logged at WARNING; soft at INFO. State transitions logged at
INFO with capability and tasking flag. Health vector ingests to Beamwarden as
`sensor_name="health_vector"` using the existing ingest endpoint — no
Beamwarden changes required.

New env var: `SATLAB_NODE_ID` (optional — stable UUID for health vector identity;
auto-generated at startup if absent).

**`docs/hardware.md`** — Updated pin and address tables to reflect confirmed
hardware (DPS310 at 0x77, LIS3DHTR at 0x19, AHT20 at 0x38). Removed BMP280,
MPU-6050, and SSD1306 OLED from tables. Added notes column explaining
misidentifications. Added OLED deferral note with RAM constraint reason.

### Cross-link: Wio Tracker L1 confirmed (2 units)

The two Meshnology Wio Tracker L1 units (SX1262 LoRa + nRF52840, 3000 mAh,
cases) in the hardware inventory ship pre-flashed with Meshtastic. With 2 units
and 2 RPis, the cross-link architecture is:

```
Node A: Arduino-A → USB serial → RPi-A → USB → Wio-A ┐
                                                       │ LoRa (Meshtastic)
Node B: Arduino-B → USB serial → RPi-B → USB → Wio-B ┘
                                    ↓
                               Beamwarden (ground)
```

This covers all three proposal layers simultaneously. Meshtastic maximum
payload is 237 bytes; health vector JSON will need compact-key serialization
before the cross-link module is written.

**`docs/crosslink-setup.md`** added: five-phase hardware checklist covering
firmware verification, Meshtastic configuration (region, channel PSK via
export/import, node naming), RPi software setup, USB by-id path
disambiguation, connectivity test, and agent integration smoke test.

### Hardware / orders

- Wio Tracker L1 units confirmed pre-flashed with Meshtastic — no reflash required
- Battery charger: Adafruit #4410 Micro-Lipo USB-C charger ×2 ($5.95 ea);
  close 500mA solder jumper on each before use

### Next steps

- Tier 2: statistical residual monitoring (per-parameter 3σ with configurable window)
- `agent/crosslink.py`: Meshtastic SerialInterface wrapper; health vector TX/RX
- Second node bring-up (beamrider-0004): RPi + Arduino + Wio Tracker
- Complete Wio Tracker cross-link setup per `docs/crosslink-setup.md`

---

## 2026-04-27 — Iteration 1 complete: all 6 sensors streaming, agent on systemd

**Status:** All six sensors live and unattended on beamrider-0003. PR #1 open against main.

### What happened

The sensor previously assumed to be a BMP280 at I2C address 0x77 was misidentified. The diagnostic sketch `arduino/diag_bmp_oled` confirmed:

- `reg[0xD0] = 0x0` — not a BMP series sensor (BMP280 returns 0x60)
- `reg[0x0D] = 0x11` — Infineon DPS310 revision 1 (product family upper nibble 0x1)

The Adafruit DPS310 library v1.1.6 does a strict `chip_id == 0x10` check and rejects revision 0x11. Patched `Adafruit_DPS310.cpp` line 134 on beamrider-0003:

```
# Before
if (chip_id.read() != 0x10) {
# After
if ((chip_id.read() & 0xF0) != 0x10) {
```

Sensor name `structural_bmp280` preserved in Beamwarden to avoid re-registration.

### OLED confirmed deferred to iteration 2

With the full sensor suite loaded (AHT20 + DPS310 + LIS3DHTR), the Uno has 1060 bytes of global variables and only 988 bytes of heap available at runtime. The SSD1306 128×64 frame buffer requires 1024 bytes via `malloc()` — it cannot fit. OLED removed from `subsystem_sim.ino` to recover ~8 KB of flash headroom (was at 92%). OLED display planned for iteration 2 (Wio Tracker, nRF52840, 256 KB RAM).

### Sketch libraries (arduino/subsystem_sim) — final iteration 1 state
| Library | Version | Purpose |
|---|---|---|
| Adafruit AHTX0 | latest | AHT20 temp+humidity |
| Adafruit DPS310 | 1.1.6 (patched) | DPS310 pressure + temp |
| Seeed Arduino LIS3DHTR | 1.2.4 | LIS3DHTR accelerometer |

### systemd service

`deploy/satlab-agent.service` installed and enabled on beamrider-0003. Starts after `network-online.target`, restarts on failure with 10 s delay. Logs via `journalctl -u satlab-agent -f`. Serial disconnect/reconnect warnings on startup are expected — the Arduino resets on DTR when pyserial opens the port; the reconnect loop handles it within one cycle.

### Iteration 1 sensors — final state
| Beamwarden sensor | Subsystem | Hardware | Notes |
|---|---|---|---|
| `eps_light` | EPS | LDR analog (A0) | pct 0–100 solar illumination proxy |
| `structural_sound` | Structural | Microphone analog (A1) | raw ADC vibration proxy |
| `tcs_dht` | TCS | AHT20 (I2C 0x38) | temp_c, humidity_pct |
| `structural_bmp280` | Structural | DPS310 (I2C 0x77, chip_id 0x11) | pressure_hpa, temp_c |
| `adcs_lis3dh` | ADCS | LIS3DHTR (I2C 0x19) | ax_g, ay_g, az_g |
| `orbit_sgp4` | Orbital | SGP4 / ISS TLE (NORAD 25544) | pushed every 30 s from RPi agent |

### Next steps
- Merge PR #1 to main
- Iteration 2: replace USB serial with Wio Tracker SX1262 LoRa radio; add OLED on nRF52840 (256 KB RAM)

---

## 2026-04-26 — Iteration 1 sensor bring-up complete

**Status:** All five sensors live, streaming to Beamwarden (beamrider-0003).

### Sensors operational
| Beamwarden sensor | Subsystem | Hardware | Notes |
|---|---|---|---|
| `tcs_dht` | TCS | AHT20 (I2C 0x38) | temp_c: 20.5 °C, humidity_pct: 50.66% |
| `adcs_lis3dh` | ADCS | LIS3DHTR (I2C 0x19) | ax_g, ay_g, az_g in units of g |
| `eps_light` | EPS | LDR analog (A0) | pct 0–100 solar illumination proxy |
| `structural_sound` | Structural | Microphone analog (A1) | raw ADC vibration proxy |
| `orbit_sgp4` | Orbital | SGP4 propagation (ISS, NORAD 25544) | pushed every 30s from RPi agent |

### Hardware confirmed on bench
- Raspberry Pi 3 Model B Rev 1.2 (beamrider-0003, Debian Bookworm)
- Arduino Uno R3 + Grove Base Shield
- Grove LDR light sensor → A0
- Grove sound/microphone sensor → A1
- Grove AHT20 temp+humidity → I2C socket (addr 0x38)
- Grove LIS3DHTR 3-axis accelerometer → I2C socket (addr 0x19)
- USB-B cable (RPi ↔ Arduino, serial at 9600 baud)

### Issues resolved
- **`%f` in avr-libc snprintf outputs `?`** — AVR printf does not include float support by default. Fixed by switching to `dtostrf()` for I2C sensor floats and integer arithmetic for analog percentages. Removing the SSD1306/GFX OLED libraries freed sufficient flash headroom.
- **OLED deferred** — Adafruit SSD1306 + GFX + dtostrf together exceed the Uno's 32KB flash. OLED support deferred to iteration 2 (Wio Tracker, nRF52840, 1MB flash).
- **Sensor misidentification** — Kit documentation described sensor as "DHT11 on D3/D7" but actual chip is AHT20 (I2C). Confirmed by I2C scanner (address 0x38). Sketch updated from DHT library to Adafruit AHTX0.
- **Accelerometer misidentification** — Assumed MPU-6050 (0x68); actual sensor is LIS3DHTR (0x19). Confirmed by I2C scanner. Sketch updated to Seeed LIS3DHTR library; payload uses ax_g/ay_g/az_g in g-units (no gyro).
- **`eps_light` not ingesting** — Arduino `snprintf` with `%.1f` emitted `?` for float pct field, causing JSON parse failure silently dropped at DEBUG log level. Fixed with integer arithmetic.
- **Serial reconnection** — Agent crashed on Arduino reset (USB disconnect). Fixed: `serial_reader.py` now wraps port open in retry loop with 3s reconnect delay.
- **Beamwarden URL** — Ingest endpoint is `/api/v1/ingest/` (not `/api/v1/readings/ingest/`).
- **Sensor seeding** — All six sensors must be pre-registered in Beamwarden for beamrider-0003; `Sensor.objects.get_or_create` requires `company` and `business_unit` from the beamrider object.

### Sketch libraries (arduino/subsystem_sim)
| Library | Version | Purpose |
|---|---|---|
| Adafruit AHTX0 | latest | AHT20 temp+humidity |
| Adafruit BMP280 | latest | BMP280 pressure (not yet wired) |
| Seeed Arduino LIS3DHTR | 1.2.4 | LIS3DHTR accelerometer |

### Sensors registered in Beamwarden (beamrider-0003) but not yet wired
- `structural_bmp280` — BMP280 air pressure + temp (I2C 0x76/0x77)
- `tcs_dht` sensor type registered as `tcs_dht`; `adcs_mpu6050` registered but superseded by `adcs_lis3dh`

### Next steps
- Wire BMP280 (air pressure) to I2C bus
- Set up agent as systemd service on beamrider-0003 for persistence across reboots
- Iteration 2: replace USB serial with Wio Tracker SX1262 LoRa radio

---
