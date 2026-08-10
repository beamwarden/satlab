---
name: satlab-arduino-upload
description: Compile and upload Arduino sketches to satlab's beamrider-0003 via arduino-cli, including the read-back verification loop. Use when modifying or flashing Arduino firmware (subsystem_sim, wheel_controller, etc.).
---

Migrated from the project's CLAUDE.md 2026-08-10 (moved out of always-loaded context — only needed when actually flashing firmware).

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
