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
| D7 | DHT11 (temp + humidity) | TCS |
| I2C (A4/A5) | BMP280 (air pressure) | Structural / TCS |
| I2C (A4/A5) | MPU-6050 (accelerometer + gyro) | ADCS |
| I2C (A4/A5) | SSD1306 OLED 128×64 | Status display |

All I2C devices share the same bus (A4=SDA, A5=SCL). Default I2C addresses:

| Device | Address |
|---|---|
| BMP280 | 0x76 (or 0x77 if SDO pulled high) |
| MPU-6050 | 0x68 (or 0x69 if AD0 pulled high) |
| SSD1306 | 0x3C |

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
