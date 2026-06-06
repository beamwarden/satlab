# Reaction Wheel Attitude Control — Build Document

Single-axis reaction wheel demonstrator integrated into the satlab HIL (Hardware-in-the-Loop) simulator. A BLDC (Brushless DC) gimbal motor + flywheel mounted on a free-rotating pivot platform; the Arduino Uno Q runs SimpleFOC velocity control on the inner loop; the RPi (Raspberry Pi) agent closes the outer attitude loop against BNO055 quaternion feedback and accepts attitude commands from Beamwarden.

Fallback: if the pivot frame is not yet built, the wheel + control stack runs as a momentum wheel demonstrator. Wheel speed control, BNO055 attitude sensing, and Beamwarden telemetry are all fully functional without body rotation. Software is identical either way.

---

## Reference

- charleslabs.fr reaction wheel project (cascaded PID (Proportional-Integral-Derivative) structure, tumbling FSM (Finite State Machine), flywheel sizing approach)
- SimpleFOC documentation: docs.simplefoc.com
- iPower GM4108H-120T product page: shop.iflight.com/ipower-motor-gm4108h-120t-brushless-gimbal-motor-pro217

---

## Hardware

### Parts to acquire

| Item | Part | Qty | ~Cost |
|---|---|---|---|
| Gimbal BLDC | iPower GM4108H-120T (24N/22P, ~27KV (RPM/volt), 10mm hollow shaft) | 1 | $35.90 |
| FOC (Field-Oriented Control) driver | SimpleFOC Shield v2 | 1 | $30 |
| Magnetic encoder | AS5600 breakout (I2C (Inter-Integrated Circuit), 12-bit) | 1 | $5 |
| Encoder magnet | 10×2mm diametrically magnetized disk (for 10mm shaft) | 1 | $2 |
| Pivot bearings | 608ZZ | 2 | $2 |
| Pivot axle | Hollow steel shaft, ~8mm OD (outer diameter), ~100mm length | 1 | $5 |
| Power | 3S LiPo (Lithium Polymer, 3 cells in series) 1000mAh or bench PSU (Power Supply Unit) (12V/3A) | 1 | $15–40 |
| Flywheel | 3D printed rim-loaded disk — see [3D printed parts](#3d-printed-parts) (`cad/flywheel_gm4108h.scad`) | 1 | — |
| Pivot frame | 3D printed or aluminum extrusion — see [3D printed parts](#3d-printed-parts) | — | — |

### Parts already on hand (relevant to this build)

| Item | Role |
|---|---|
| Arduino Uno Q | Wheel controller — mounts on platform, runs SimpleFOC inner loop |
| Arduino Uno R3 | Sensor telemetry — unchanged, stays on base |
| Raspberry Pi 3 (×2) | RPi agent / outer attitude loop — stays on base |
| BNO055 | Attitude reference — mounts on platform, quaternion output to RPi outer loop |
| LSM6DSOX | Gyro source for tumbling detection — mounts on platform, wired to Uno Q |
| Breadboards, connectors, cables | Integration |

### Motor selection rationale

Standard hobby ESCs (Electronic Speed Controllers) and drone motors are unsuitable: hobby ESCs are unidirectional, and high-KV drone motors have poor low-speed resolution. Gimbal motors (low KV, designed for smooth precise torque) are the correct class. The GM4108H-120T at 120KV on 12V gives a manageable top speed with good low-RPM authority.

SimpleFOC Shield v2 stacks directly onto the Uno Q as an Arduino shield — no breadboarding required for the motor driver stage.

### Encoder mounting

Epoxy a 10×2mm diametrically magnetized disk magnet to the motor shaft end (shaft OD is 10mm; hollow ID (inner diameter) is 8mm). Mount the AS5600 breakout centered over the shaft on a small standoff (1–2mm gap). The AS5600 connects to Uno Q I2C (SDA (Serial Data) / SCL (Serial Clock)).

### Platform wire routing

The Uno Q, SimpleFOC Shield, BNO055, and LSM6DSOX all mount on the rotating platform. The only wires that cross the pivot axis are the four connecting the platform to the base: 5V, GND (ground), serial TX (transmit), serial RX (receive).

Route these four wires through the bore of a hollow pivot axle. Because the wires run along the axis of rotation — not offset from it — they experience zero torsion regardless of platform angle. The platform rotates around the wires; the wires do not move. No slipring required, no slack management, no wire stress at any angle.

Pivot axle: ~8mm OD hollow steel shaft, seated in 608ZZ bearings at each end of the frame. Wires exit the axle bore at both ends and connect to the platform PCB/breadboard on one side and the base (RPi serial port, 5V supply) on the other.

---

## Architecture

```
Beamwarden
    │  attitude commands (target quaternion)
    │  telemetry (attitude, wheel RPM (revolutions per minute), fault state)
    ▼
RPi Agent [base]  ←─────────────── serial (4 wires through hollow pivot axle)
    │  outer attitude PID                          │
    │                                              │
    ├── Uno R3 [base]                    ┌─────────┴──── PLATFORM (rotates) ────┐
    │   existing sensor telemetry        │  Uno Q ←── AS5600 (I2C, rotor pos)   │
    │                                    │  SimpleFOC velocity mode              │
    └── serial ←──────────────────────── │  inner PID @ 100Hz                   │
                                         │  → SimpleFOC Shield → GM4108H        │
                                         │    → flywheel                         │
                                         │  BNO055 (I2C → Uno Q → serial → RPi) │
                                         │  LSM6DSOX (I2C → Uno Q, tumbling FSM)│
                                         └───────────────────────────────────────┘
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

`subsystem` value `adcs` refers to the ADCS (Attitude Determination and Control System) subsystem.

`mode` values: `hold`, `slew`, `detumble`, `idle`, `fault`

---

## 3D printed parts

### CAD heritage

The mechanical design derives from the **charleslabs.fr reaction wheel** (repo: `gaspode-wonder/reaction_wheel`, MIT). That project ships editable CAD (STEP + SolidWorks) and STLs for four printed parts — `base`, `satellite disk`, `motor holder`, `flywheel` — driven by a **NEMA 17 stepper + DRV8825**. satlab uses a **GM4108H BLDC gimbal motor + SimpleFOC** instead, so the **electronics and firmware do not transfer**; only the mechanical concepts do.

Reference dimensions measured from their STLs:

| Part | Size (mm) | Reuse for satlab |
|---|---|---|
| Flywheel | 130 OD × 16 thick | **Concept reused** — rim disk + adjustable M8 tuning masses. Re-bored for the GM4108H rotor (see `cad/flywheel_gm4108h.scad`). |
| Satellite disk (platform) | 130 OD × 29 | Geometry reference for our rotating platform; needs the hollow-axle wire pass-through our design adds. |
| Base | 70 × 70 × 20 | Dimensional starting point; their base is battery/untethered, ours routes 4 wires through a hollow axle. |
| Motor holder (26 / 40 mm) | 59 × 37 × 30/44 | **Does not transfer** — bored for a NEMA 17 square face. Needs a from-scratch holder for the round GM4108H bolt pattern. |

Their flywheel tunes moment of inertia with **3× M8×20 bolts + nuts** slid in the wheel — this is the "adjustable hardware placement" approach our Open questions cite.

### Control heritage (informative)

Their firmware (`PID.h`, `Arduino_ReactionWheel.ino`) confirms the cascaded-PID + tumbling-FSM structure this build targets, and is a useful gain/threshold starting point even though it runs on a stepper:

- **Cascaded PID** — attitude PID output feeds the speed PID setpoint. Their `PIDAngleController` wraps angle error to ±180°.
- **Attitude gains**: P = 2.5, I = 0, D = 400 (heavy derivative, no integral).
- **Tumbling FSM with hysteresis**: drops to detumble above **360 °/s**, re-engages attitude hold below **45 °/s**. Maps directly onto our `NOMINAL`/`TUMBLING` FSM — adopt the hysteresis band rather than a single threshold to avoid chatter.

### Flywheel — `cad/flywheel_gm4108h.scad`

Parametric OpenSCAD model for our motor: a **rim-loaded disk** (mass concentrated in a thick outer rim, thin central web) to maximize moment of inertia per gram. Default OD 120 mm, rim 16 mm tall × 12 mm wide. The flywheel bolts to the **rotor (spinning bell)** — the shaft end stays reserved for the AS5600 encoder magnet. A ring of M8 pockets carries the charleslabs-style adjustable tuning masses.

> **VERIFY BEFORE PRINTING:** the GM4108H rotor bolt-circle diameter, hole count, hole size, and center-boss diameter in the `.scad` are placeholders — measure your motor and set the `mount_*` / `boss_*` parameters before slicing.

Render to STL:
```bash
openscad -o cad/flywheel_gm4108h.stl cad/flywheel_gm4108h.scad
```

Print notes: PLA is fine for the demonstrator (PETG if it sits near motor heat); 50–60% infill or solid rim (6+ perimeters) to keep mass in the rim; print web-side down, counterbores up — no supports.

### Motor holder (to design)

The GM4108H needs a holder matched to its round body and bolt pattern — the charleslabs NEMA 17 holder cannot be reused. Hold the motor coaxial with the rotating platform, leave clearance for the AS5600 standoff over the shaft end, and seat against the platform plate. Not yet modeled.

### Pivot frame (to design)

Seats the ~8 mm hollow steel axle in two 608ZZ bearings (608 ID = 8 mm, matches) with the four platform wires routed through the axle bore. Print the bearing seats as tight press-fits or add M3 captive-nut clamps. Not yet modeled.

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
BLDCMotor motor = BLDCMotor(11);        // 24N/22P → 11 pole pairs
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
   Thread four wires (5V, GND, TX, RX) through the hollow pivot axle. Seat axle in 608ZZ bearings at each end of the frame. Mount platform on axle. Secure motor + flywheel, Uno Q, BNO055, and LSM6DSOX to platform. Connect wire ends: platform side to Uno Q, base side to RPi serial and 5V supply.

9. **Validate body counter-rotation**
   Command a wheel speed step. Observe platform counter-rotation. Verify BNO055 tracks the motion and outer loop converges.

10. **Integrate tumbling FSM**
    Manually disturb platform. Confirm Uno Q detects tumbling, spins up wheel to counter, reports `mode: detumble` to Beamwarden.

---

## Open questions

- **Flywheel dimensions:** Moment of inertia target depends on platform mass and desired slew rate. Start with charleslabs approach (adjustable hardware placement) and measure empirically. Parametric model in `cad/flywheel_gm4108h.scad` (rim-loaded, M8 tuning pockets); GM4108H rotor bolt pattern still needs measuring.
- **Power architecture:** Bench PSU (12V/3A) preferred during development; 3S LiPo for untethered operation (confirmed compatible). Determine whether Uno Q and SimpleFOC Shield share a supply rail with the rest of the system or run isolated.
- **Max wheel speed:** ~325 RPM at 12V (no-load). Load reduces this; factor into angular momentum budget when sizing the flywheel.
- **I2C bus:** BNO055 on RPi I2C. AS5600 on Uno Q I2C. No conflict. Confirm LSM6DSOX address (0x6A or 0x6B) does not collide with AS5600 (0x36) if both end up on the same Uno Q bus.
- **Outer loop rate:** 20Hz is a starting point. May need adjustment based on BNO055 output data rate and serial latency.
