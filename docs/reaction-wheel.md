# Reaction Wheel Attitude Control — Build Document

Single-axis reaction wheel demonstrator integrated into the satlab HIL simulator. A BLDC gimbal motor + flywheel mounted on a free-rotating pivot platform; the Arduino Uno Q runs SimpleFOC velocity control on the inner loop; the RPi agent closes the outer attitude loop against BNO055 quaternion feedback and accepts attitude commands from Beamwarden.

Fallback: if the pivot frame is not yet built, the wheel + control stack runs as a momentum wheel demonstrator. Wheel speed control, BNO055 attitude sensing, and Beamwarden telemetry are all fully functional without body rotation. Software is identical either way.

---

## Reference

- charleslabs.fr reaction wheel project (cascaded PID structure, tumbling FSM, flywheel sizing approach)
- SimpleFOC documentation: docs.simplefoc.com
- iPower GM4108H-120T datasheet

---

## Hardware

### Parts to acquire

| Item | Part | Qty | ~Cost |
|---|---|---|---|
| Gimbal BLDC | iPower GM4108H-120T (120KV) | 1 | $25 |
| FOC driver | SimpleFOC Shield v2 | 1 | $30 |
| Magnetic encoder | AS5600 breakout (I2C, 12-bit) | 1 | $5 |
| Encoder magnet | 6×2.5mm diametrically magnetized disk | 1 | $2 |
| Pivot bearings | 608ZZ | 2 | $2 |
| Power | 3S LiPo 1000mAh or bench PSU (12V/3A) | 1 | $15–40 |
| Flywheel | 3D printed disk or machined aluminum | 1 | — |
| Pivot frame | 3D printed or aluminum extrusion | — | — |

### Parts already on hand (relevant to this build)

| Item | Role |
|---|---|
| Arduino Uno Q | Wheel controller — runs SimpleFOC inner loop |
| Arduino Uno R3 | Sensor telemetry — unchanged |
| Raspberry Pi 3 (×2) | RPi agent / outer attitude loop |
| BNO055 | Attitude reference — quaternion output to RPi outer loop |
| LSM6DSOX | Gyro source for tumbling detection on Uno Q |
| Breadboards, connectors, cables | Integration |

### Motor selection rationale

Standard hobby ESCs and drone motors are unsuitable: hobby ESCs are unidirectional, and high-KV drone motors have poor low-speed resolution. Gimbal motors (low KV, designed for smooth precise torque) are the correct class. The GM4108H-120T at 120KV on 12V gives a manageable top speed with good low-RPM authority.

SimpleFOC Shield v2 stacks directly onto the Uno Q as an Arduino shield — no breadboarding required for the motor driver stage.

### Encoder mounting

Epoxy the 6×2.5mm diametrically magnetized disk magnet to the motor shaft end. Mount the AS5600 breakout centered over the shaft on a small standoff (1–2mm gap). The AS5600 connects to Uno Q I2C (SDA/SCL).

---

## Architecture

```
Beamwarden
    │  attitude commands (target quaternion)
    │  telemetry (attitude, wheel RPM, fault state)
    ▼
RPi Agent  ←── BNO055 (I2C, quaternion attitude)
    │  outer attitude PID → wheel velocity setpoint (rad/s)
    │  serial JSON → Uno Q
    │  serial JSON ← Uno Q (wheel telemetry)
    │
    ├── Uno R3  (existing sensor telemetry pipeline — unchanged)
    │
    └── Uno Q   ←── AS5600 (I2C, rotor position)
            SimpleFOC velocity mode
            inner velocity PID @ 100Hz
            → SimpleFOC Shield → GM4108H → flywheel
```

### Control loops

**Inner loop — Uno Q (100Hz)**
Velocity PID in SimpleFOC. Receives a wheel speed setpoint in rad/s from the RPi, drives the GM4108H via FOC, reads rotor position from the AS5600 for commutation and speed feedback.

**Outer loop — RPi agent**
Attitude PID. Reads BNO055 quaternion, computes angular error from the commanded target, outputs a wheel velocity setpoint to Uno Q over serial. Runs at ~20Hz; much slower than the inner loop to maintain cascade stability.

**Tumbling FSM — Uno Q**
Two states: `NOMINAL` and `TUMBLING`. If `|angular_rate|` from the LSM6DSOX exceeds the threshold, Uno Q enters detumble autonomously (spins wheel to counter), independent of the RPi command channel. Reports `mode` in every telemetry frame so Beamwarden can observe.

---

## Serial protocol

Baud rate 9600 on both serial links, consistent with the rest of the satlab serial protocol.

**Uno Q → RPi (10Hz wheel telemetry):**
```json
{"ts":"<utc>","subsystem":"adcs","sensor":"wheel","payload":{"rpm":125,"fault":false,"mode":"hold"}}
```

**RPi → Uno Q (velocity setpoint, event-driven):**
```json
{"cmd":"vel","val":78.5}
```

**RPi → Beamwarden (attitude, 5Hz):**
```json
{"ts":"<utc>","subsystem":"adcs","sensor":"bno055","payload":{"qw":0.99,"qx":0.01,"qy":0.02,"qz":0.0}}
```

`mode` values: `hold`, `slew`, `detumble`, `idle`, `fault`

---

## Firmware

### Uno Q — `arduino/wheel_controller/wheel_controller.ino`

Responsibilities:
- Initialize SimpleFOC with AS5600 encoder and SimpleFOC Shield driver
- Run `motor.loopFOC()` + `motor.move()` at 100Hz in the main loop
- Parse incoming serial JSON for `{"cmd":"vel","val":<float>}` setpoints
- Run tumbling FSM against LSM6DSOX gyro reads
- Emit wheel telemetry JSON at 10Hz

Key SimpleFOC configuration:
```cpp
BLDCMotor motor = BLDCMotor(11);        // pole pairs for GM4108H-120T
BLDCDriver3PWM driver = BLDCDriver3PWM(9, 5, 6, 8);
MagneticSensorI2C sensor = MagneticSensorI2C(AS5600_I2C);

motor.controller = MotionControlType::velocity;
motor.PID_velocity.P = 0.5;
motor.PID_velocity.I = 10;
motor.PID_velocity.D = 0.001;
motor.voltage_limit = 6;                // start conservative
```

Tune PID gains on the bench before mounting on the pivot frame.

### RPi agent additions

**`agent/wheel_reader.py`**
Second serial reader (same pattern as `serial_reader.py`). Opens `SATLAB_WHEEL_PORT`, reads newline-delimited JSON from Uno Q, forwards telemetry frames to Beamwarden ingest.

**`agent/wheel_controller.py`**
Outer attitude loop. Reads BNO055 quaternion via I2C (`smbus2` or `adafruit-circuitpython-bno055`), computes quaternion error against commanded target, runs attitude PID, writes velocity setpoints to Uno Q serial port. Exposes `set_target(q: Quaternion)` for Beamwarden command handling.

**`agent/main.py` changes**
- Spawn `wheel_reader` thread alongside existing `serial_reader` thread
- Instantiate `wheel_controller`, wire to BNO055 and Beamwarden command subscription

### New environment variable

```
SATLAB_WHEEL_PORT    Serial device for Uno Q (e.g. /dev/ttyACM1)
```

---

## Build sequence

1. **Validate motor + encoder open-loop**
   Wire AS5600 + SimpleFOC Shield + GM4108H to Uno Q. Run SimpleFOC `find_pole_pairs` utility. Confirm motor spins in both directions, encoder reads cleanly.

2. **Close inner velocity loop**
   Load `wheel_controller.ino`. Tune `PID_velocity` gains. Verify setpoint tracking at low RPM (±50 rad/s) and saturation behavior at high RPM.

3. **Add serial command interface to Uno Q**
   Parse `{"cmd":"vel","val":<n>}` from RPi serial. Emit telemetry JSON at 10Hz. Test with `minicom` or a Python one-liner before wiring to agent.

4. **Add `wheel_reader.py` to RPi agent**
   Confirm wheel telemetry appears in Beamwarden.

5. **Wire BNO055 to RPi I2C, validate quaternion reads**
   Confirm stable quaternion output. Check for I2C address conflicts with other devices on the bus.

6. **Implement `wheel_controller.py`, tune outer attitude PID**
   Command attitude holds without the pivot frame (wheel spins, no body motion). Verify setpoint tracking in telemetry.

7. **Build flywheel**
   3D print or machine a disk. Heavier rim = more angular momentum storage = more authority. Size to match motor shaft.

8. **Build pivot frame**
   Mount platform on 608ZZ bearings for single-axis rotation. Secure motor + flywheel to platform. BNO055 mounts on the platform (rotates with it).

9. **Validate body counter-rotation**
   Command a wheel speed step. Observe platform counter-rotation. Verify BNO055 tracks the motion and outer loop converges.

10. **Integrate tumbling FSM**
    Manually disturb platform. Confirm Uno Q detects tumbling, spins up wheel to counter, reports `mode: detumble` to Beamwarden.

---

## Open questions

- **Flywheel dimensions:** Moment of inertia target depends on platform mass and desired slew rate. Start with charleslabs approach (adjustable hardware placement) and measure empirically.
- **Power architecture:** Bench PSU preferred during development. 3S LiPo for untethered operation. Determine whether Uno Q and SimpleFOC Shield share a supply rail with the rest of the system or run isolated.
- **I2C bus:** BNO055 on RPi I2C. AS5600 on Uno Q I2C. No conflict. Confirm LSM6DSOX address (0x6A or 0x6B) does not collide with AS5600 (0x36) if both end up on the same Uno Q bus.
- **Outer loop rate:** 20Hz is a starting point. May need adjustment based on BNO055 output data rate and serial latency.
