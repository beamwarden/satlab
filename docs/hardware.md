# Hardware Reference

## Wiring — Iteration 1 (Serial/USB)

```
Raspberry Pi 3
    USB-A ──────────────────────── Arduino Uno (USB-B)
```

The RPi powers and communicates with the Arduino over a single USB cable.
Serial device on RPi: typically `/dev/ttyACM0` or `/dev/ttyUSB0`.

## Arduino pin assignments

| Pin | Sensor | Subsystem |
|---|---|---|
| A0 | LDR light sensor | EPS |
| A1 | Sound / microphone module | Structural |
| I2C (A4/A5) | AHT20 (temp + humidity) | TCS |
| I2C (A4/A5) | DPS310 (air pressure + temp) | Structural |
| I2C (A4/A5) | LIS3DHTR (accelerometer) | ADCS |

All I2C devices share the same bus (A4=SDA, A5=SCL). Confirmed I2C addresses:

| Device | Address | Notes |
|---|---|---|
| AHT20 | 0x38 | Replaces assumed DHT11 on D7 |
| DPS310 | 0x77 | Replaces assumed BMP280; chip_id=0x11 (rev 1); Adafruit DPS310 lib patched for strict chip_id check |
| LIS3DHTR | 0x19 | Replaces assumed MPU-6050; no gyro — ax_g/ay_g/az_g only |

**OLED deferred to iteration 2.** SSD1306 128×64 frame buffer requires 1024 bytes via `malloc()`; Uno has only 988 bytes of heap available with the full sensor suite loaded. Planned for Wio Tracker nRF52840 (256 KB RAM).

## Arduino Modulino Thermo

Connects via I2C. Add to the existing I2C bus. Use the Arduino Modulino library.
Map to `tcs_modulino_thermo` sensor in Beamwarden.

## MQ4 Methane Sensor

Analog output → connect to A2 (add to sketch when wired up).
Requires 2–5 minute warm-up after power-on before readings stabilize.
Map to `propulsion_mq4` sensor in Beamwarden.

## GPS Module (GY-NEO7mV2)

UART interface. On RPi: use `gpsd` or direct serial read.
On Arduino: SoftwareSerial on D4(RX)/D5(TX) — add to sketch when wired.
Map to `orbit_gps` sensor in Beamwarden.

## Iteration 2 — Radio (Wio Tracker SX1262 LoRa)

Replace USB serial transport with LoRa radio link.
Same JSON packet schema; swap the physical layer only.

- Arduino → Wio Tracker (LoRa TX node)
- RPi → Wio Tracker (LoRa RX node, connected via USB serial)

The `serial_reader.py` agent code requires no changes for iteration 2 —
the Wio Tracker RX node presents as a virtual serial port to the RPi.
