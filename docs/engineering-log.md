# satlab Engineering Log

Entries in descending order — most recent first.

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
