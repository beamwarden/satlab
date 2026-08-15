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

**Reconciled against hangar (192.168.1.223:8788), re-verified 2026-08-09** — several items below were carried over from the original build plan as "to acquire" but have actually been on hand for a while; moved to the table below. Genuinely still outstanding:

| Item | Part | Qty | ~Cost | Source |
|---|---|---|---|---|
| Pivot axle | [K&S #9807](https://www.amazon.com/Engineering-KS9807-Round-Alum-Tube/dp/B005WPAL7A) round **aluminum** tube, 8mm OD × 0.45mm wall × 300mm (cut to ~100mm) — OD matches the 608ZZ bearing ID; substituted for the originally-specced steel, which isn't a normal stock size at 8mm OD hollow | 1 pack (2pcs) | ~$8 | Amazon |
| Power | Either: [OVONIC 4S 1300mAh 14.8V 100C, XT60](https://www.amazon.com/OVONIC-Battery-1300mAh-Connector-Quadcopter/dp/B0FS13VNNH) (2-pack) — 4S chosen over 3S so pack voltage (16.8V full → ~13.2V low-cutoff) stays inside the SimpleFOC Shield's recommended 12–24V `TB_PWR` input range across the whole discharge curve; a 3S pack sags to ~9.9V and spends real time under that floor. `motor.voltage_limit` in firmware caps drive voltage regardless of supply, so the extra headroom doesn't force higher RPM. If it mounts on the rotating platform per the wire-routing design (only 5V/GND/TX/RX cross the pivot axle, not motor power), factor its mass into the flywheel/moment-of-inertia budget — **or** [Pyramid PS3KX bench PSU](https://www.amazon.com/Universal-Compact-Bench-Power-Supply/dp/B0002JTD2K) (13.8V DC, 2.5A cont/3A surge, wires directly into `TB_PWR` screw terminal) for tethered bench dev during build steps 1–6. Dedicated to this build — the on-hand Meshnology 3000mAh LiPoly is earmarked for the Wio Tracker L1 crosslink, not this | 1 | varies | Amazon |
| M8 bolts + nuts | [Bonost 1380pc metric assortment](https://www.amazon.com/Bonost-1380pcs-Nuts-Bolts-Assortment/dp/B0DSV5FFSB), grade 8.8 zinc-plated, M4–M8, bolt lengths 12–30mm — covers M8×20 tuning bolts + matching nuts in one kit | 1 kit | varies | Amazon |
| 4S LiPo charger | [ISDT PD60S](https://www.amazon.com/ISDT-Battery-Balance-Charger-Battery%EF%BC%8CLife/dp/B08F7C1T2T), USB-C input, 60W/6A, 1–4S balance charging — found 2026-08-09 while reconciling against hangar: the on-hand **Adafruit #4410 Micro-Lipo USB-C charger (×2) is single-cell (3.7V/4.2V) only** and cannot charge the 4S pack above. New dependency introduced by the 3S→4S switch, not previously listed. Only needed if going the LiPo route; not required for the bench-PSU-only path | 1 | ~$25 | Amazon |
| Pivot frame | 3D printed, `cad/pivot_frame.scad` — see [3D printed parts](#3d-printed-parts). Modeled and rendering clean 2026-08-09, not yet printed | — | — | — |
| Motor holder | 3D printed, `cad/motor_holder_gm4108h.scad` — see [3D printed parts](#3d-printed-parts). Mounting bracket modeled and rendering clean 2026-08-10 (from caliper measurement, not the conflicting published specs); AS5600 standoff arm not yet included, not yet printed | 1 | — | — |

### Parts already on hand (relevant to this build)

| Item | Role |
|---|---|
| iPower GM4108H-120T BLDC gimbal motor | Reaction wheel drive |
| SimpleFOC Shield v2 (IR2104/INA240) | FOC driver, stacks on Uno Q |
| AS5600 breakout + 10×2mm magnet | Rotor position feedback (see corrected mounting note above) |
| 608ZZ bearings | ×10 on hand, 3 needed for the pivot frame (2 in the platform hub for rotation, 1 in the base as an anchor bushing — see `cad/pivot_frame.scad`) |
| Motor mounting screws | Found in a packet with the motor, 2026-08-08: 2.78mm shaft, 5.39mm head. Thread directly into the rotor's tapped holes — no nuts needed. `cad/flywheel_gm4108h.scad`'s `mount_bolt_d`/`mount_cbore_d` are sized for these exact screws. |
| Flywheel | **Printed 2026-08-08** on the K2 Pro Combo — see the print note above. Mount-hole fit validated via quarter-coupon test 2026-08-10 (`mount_cbore_h = 5.9mm`); full-size reprint at this setting not yet done. |
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

**Corrected 2026-08-08** (physical inspection with a spin test + caliper measurements): the shaft does *not* rotate — it's fixed to the stationary base plate, the same face the phase wires terminate on. The rotating part is the outer bell (barrel + the opposite cap, confirmed turning together as one piece), which is also the face the flywheel bolts to (see `cad/flywheel_gm4108h.scad`). The original plan to epoxy the magnet to "the shaft end" would put it on the part that never moves, which would give the encoder nothing to read.

Epoxy the 10×2mm diametrically magnetized disk magnet to the rotating bell instead — centered over its recessed bore, on the same face the flywheel mounts to (or to the back of the flywheel hub itself, once mounted). Mount the AS5600 breakout on a small standoff (1–2mm gap) fixed to the stationary side (the base plate or a bracket on the motor holder — see below), so it reads the magnet sweeping past on each rotation. The AS5600 connects to Uno Q I2C (SDA (Serial Data) / SCL (Serial Clock)).

### Platform wire routing

The Uno Q, SimpleFOC Shield, BNO055, and LSM6DSOX all mount on the rotating platform. The only wires that cross the pivot axis are the four connecting the platform to the base: 5V, GND (ground), serial TX (transmit), serial RX (receive).

Route these four wires through the bore of a hollow pivot axle. Because the wires run along the axis of rotation — not offset from it — they experience zero torsion regardless of platform angle. The platform rotates around the wires; the wires do not move. No slipring required, no slack management, no wire stress at any angle.

Pivot axle: ~8mm OD hollow aluminum tube (K&S #9807), seated in 608ZZ bearings at each end of the frame. Wires exit the axle bore at both ends and connect to the platform PCB/breadboard on one side and the base (RPi serial port, 5V supply) on the other.

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

Parametric OpenSCAD model for our motor: a **rim-loaded disk** (mass concentrated in a thick outer rim, thin central web) to maximize moment of inertia per gram. Default OD 120 mm, rim 16 mm tall × 12 mm wide. The flywheel bolts to the **rotor (spinning bell)** — confirmed by spin test and caliper to be the cap opposite the wire-exit base, with no shaft protrusion on that face (see the encoder mounting correction above). A ring of M8 pockets carries the charleslabs-style adjustable tuning masses.

> **MEASURED 2026-08-08:** rotor bolt pattern confirmed off the physical motor — 4 holes, 30.80mm bolt-circle diameter, 47.13mm cap OD, 7.85mm recessed center bore (no protrusion). `mount_bolt_d`/`mount_cbore_d` are sized off the motor's own screw packet (found partway through the session): 2.78mm shaft, 5.39mm head — motor holes are tapped, not clearance-bored.
>
> **PRINTED SUCCESSFULLY 2026-08-08** on the K2 Pro Combo (stock 0.4mm nozzle — corrected 2026-08-09; this was wrongly logged as 0.2mm originally, no such nozzle was ever installed) — third attempt, after two `F00528` ("printing without extruding") faults, not a clog. Fixed with reduced speeds (outer wall ~25-30mm/s, inner wall ~35-40mm/s, infill ~50-60mm/s, 4-5 slow first layers) and 0.18mm layer height; print time went from an estimated 4h4m to 10h35m. Root cause of the flow limit that the speed reduction fixed is unconfirmed — the original "fine 0.2mm nozzle" explanation was wrong along with the nozzle size, so don't trust that mechanism, only the fix. Part came out clean — correct hole count/spacing, good surface finish, no warping — but the orange/black color split (`flywheel_orange()`/`flywheel_black()` below) did not visibly alternate on the CFS despite slicing clean with two filament slots assigned; not yet diagnosed (bay-color mismatch vs. the swap never triggering are both still open).
>
> **TEST-FIT 2026-08-09: zero thread engagement, `mount_cbore_h` corrected.** Motor screws sat flush with both the top and bottom faces of the hub when seated — because the clearance through-hole already spans the full 16mm hub regardless of counterbore depth, the screw was landing exactly at the bottom face with nothing left to bite into the motor's tapped hole. The motor's screw packet turned out to have two screw types; MEASURED shank length (below the head) on both: 12.6mm (large head, 5.39mm dia — the design target, matches `mount_cbore_d`) and 10.97mm (flush/countersunk head, not used here). Fix: solved `mount_cbore_h` directly from the 12.6mm shank for 4mm of engagement — `16 - 12.6 + 4 = 7.4mm` (up from 3mm).
>
> **QUARTER-COUPON TEST 2026-08-09, second pass: 4mm target still too deep.** Printed a 90°-wedge test coupon (`flywheel_gm4108h_quarter_test.stl`, `render_part="quarter"`, one full mount hole) instead of the full part to iterate fast. With the screw seated as far as it would go, a ~1mm gap remained between the hub's motor-facing face and the motor — the screw was bottoming out **in the motor's tapped hole** before its head reached the counterbore shoulder, not a head-seating problem. That means real engagement was only ~3mm, not the 4mm targeted. Backed `mount_cbore_h` off to 5.9mm (2.5mm target engagement, with margin below the ~3mm observed limit since only one of the 4 holes has been tested and tapped-hole depth could vary slightly hole to hole).
>
> **QUARTER-COUPON TEST 2026-08-10, third pass: PASSED.** Reprinted the same test coupon at `mount_cbore_h = 5.9mm` — flush seating against the motor, no gap. Cleared to print the full flywheel at this setting.

Render to STL:
```bash
openscad -o cad/flywheel_gm4108h.stl cad/flywheel_gm4108h.scad
```

For the CFS alternating-color print, render the two halves separately and import both into your slicer at the same origin (see `color_segments`/`color_cap_height` params and the `render_part` switch at the bottom of the `.scad`):
```bash
openscad -D 'render_part="orange"' -o cad/flywheel_gm4108h_orange.stl cad/flywheel_gm4108h.scad
openscad -D 'render_part="black"' -o cad/flywheel_gm4108h_black.stl cad/flywheel_gm4108h.scad
```

**COLOR-SPLIT DIAGNOSIS 2026-08-10.** The alternating orange/black cap didn't visibly show up on the 2026-08-08 physical print despite slicing clean with two filament slots assigned. Reviewed the `.scad` logic:

- Fixed a real bug in `color_cap()`: it passed `wheel_od` (120, the *diameter*) into `pie_mask()`'s radius argument instead of `wheel_od/2`. Harmless in practice — the `intersection()` with `flywheel()` in `flywheel_orange()` clips it back to the real 60mm radius regardless — so this wasn't the cause of the print failure, just sloppy. Fixed either way.
- The more likely real cause is a **slicer import problem, not a geometry problem**: the two STLs are exported at fixed absolute coordinates from OpenSCAD (black spans the full 0–16mm height minus the orange sliver; orange occupies only the top 13–16mm within specific wedges) and need to land in the slicer at those *exact same* relative positions to combine into one two-color part. Two things can break that silently: (1) auto-arrange spreading the two objects apart in X/Y instead of stacking them at the same origin, and (2) a "drop to bed" import behavior repositioning each object independently in Z — since `flywheel_orange()`'s native Z-range is 13–16mm, if the slicer drops it to sit on the bed at Z=0 instead of preserving its designed height, it ends up buried inside the black body's footprint instead of capping it. Either failure mode would still slice "clean" (no errors) while silently producing two separate single-color objects instead of one combined part — consistent with what was observed. Not yet confirmed which (if either) actually happened; check both before the next attempt.

**Fast color-swap test coupon** (`quarter_orange`/`quarter_black`, same trick as the mount-hole `quarter` coupon — small and fast instead of another ~10h bet): a 90° wedge straddling one real color boundary, black body kept as a solid full-height chunk (mirrors what `flywheel_black()` actually is) rather than a disconnected sliver, so it exercises the same import/alignment risk as the full print.
```bash
openscad -D 'render_part="quarter_orange"' -o cad/flywheel_gm4108h_quarter_orange.stl cad/flywheel_gm4108h.scad
openscad -D 'render_part="quarter_black"' -o cad/flywheel_gm4108h_quarter_black.stl cad/flywheel_gm4108h.scad
```
Both render clean (manifold, no errors) 2026-08-10.

**COLOR-SWAP TEST 2026-08-10: PASSED.** Imported both STLs together in Creality Print; it detected the shared coordinate space and offered "load as a single object with multiple parts" — confirming the alignment concern above never actually materialized. Assigned the orange/black parts to separate CFS slots under the Objects tab. Printed clean: sharp, correctly-registered orange/black transition, no bleed. Root cause was the slicer import workflow (importing as two independent objects rather than one multi-part object), not the `.scad` geometry. **Full-size CFS flywheel reprint with this same import method is now cleared** — no longer blocked on the unresolved color issue from the 2026-08-08 print.

Print notes: PLA is fine for the demonstrator (PETG if it sits near motor heat); 50–60% infill or solid rim (6+ perimeters) to keep mass in the rim; print web-side down, counterbores up — no supports. **This printer needs wall/infill speeds well below slicer defaults (see the 2026-08-08 note above) — cause unconfirmed, not specifically a fine-nozzle issue** (this is a stock 0.4mm nozzle; an earlier version of this doc wrongly attributed the fix to a 0.2mm nozzle that was never installed).

### Motor holder — mounting bracket modeled 2026-08-10, `cad/motor_holder_gm4108h.scad`

The GM4108H needs a holder matched to its round body and bolt pattern — the charleslabs NEMA 17 holder cannot be reused. Published specs for this motor's stationary base-plate mounting conflicted between sources (one datasheet gave 12mm hole spacing / 10mm shaft OD, a SimpleFOC community thread modifying CAD for this same motor gave 27mm hole spacing / 15mm shaft OD) — same failure mode that cost two wasted flywheel print attempts, so this was measured off the physical unit instead of guessed:
- Base OD 47.05mm (matches the separately-measured rotor bell OD of 47.13mm)
- 4 mounting holes, clean square pattern, 26.32mm side, 2.3mm diameter
- Center hex lock-nut: 12.8mm across-flats, ~1mm proud of the base plate
- Base plate thickness ~4.59mm

Design: bolts to the motor's **stationary** base plate (wire-exit face, opposite the rotating bell/flywheel end) and sits flat on the `platform()` deck with the motor standing upright — base plate down, flywheel spinning in a horizontal plane well above the deck. No standoff height needed beyond the motor's own body length. Built as an open skeletal cross (center hub + 4 arms to corner bosses) rather than a solid disk, so the 3-wire phase harness can exit in whatever direction it actually comes off the base plate without needing that angle measured. Two mounting tabs (M3 clearance) for zip-tie/screw attachment to the platform's generic tie-down holes.

Render to STL:
```bash
openscad -o cad/motor_holder_gm4108h.stl cad/motor_holder_gm4108h.scad
```
Renders clean (manifold, no errors) 2026-08-10. **Not yet printed or test-fit.**

**Scope note — AS5600 standoff not yet included.** The doc's original design intent also has this holder carrying a fixed standoff for the AS5600, positioned near the rotating bell's flywheel face — the *opposite* end of the motor from where this bracket bolts on. That needs the motor's axial body length, which hasn't been calipered (only the published 32.3mm datasheet figure — and this project has been burned twice already trusting this motor's published specs over physical measurement). This pass covers the mounting bracket only; measure motor length before extending it.

### Pivot frame — modeled 2026-08-09, `cad/pivot_frame.scad`

Two printable bodies, selected via `render_part`: `base` (fixed foot, anchors the axle) and `platform` (rotating disk). Kinematics: **the axle is stationary**; the platform spins freely around it on two 608ZZ bearings stacked in its hub barrel (`hub_height` = 32mm separation for tip stability), matching the "wires don't move, platform rotates around them" design in [Platform wire routing](#platform-wire-routing) above. The base gets a 608ZZ pocket too — not for rotation, just as a precision-bore anchor bushing for the axle, reusing one known-good bore diameter instead of guessing a plain hole tolerance.

```bash
openscad -D 'render_part="base"' -o cad/pivot_frame_base.stl cad/pivot_frame.scad
openscad -D 'render_part="platform"' -o cad/pivot_frame_platform.stl cad/pivot_frame.scad
```

Both render clean (manifold, no errors) as of 2026-08-09. Also open: whether the press-fit alone holds the axle rigid in the base pocket, or whether it needs a drop of thread-lock/epoxy once fit is validated. Perimeter tie-down holes on the platform are generic M3 zip-tie/adhesive points — Uno Q / BNO055 / LSM6DSOX exact footprints aren't confirmed yet, so nothing is bolted to a specific hole pattern for those.

**BEARING TEST 2026-08-10: too tight, `bearing_fit_clearance` corrected.** Printed `pivot_frame_bearing_test.stl` at the original -0.15mm guess (designed pocket 21.85mm). Measured: bearing OD 22.00mm (matches nominal), printed pocket 21.64mm — 0.36mm of interference, not the intended 0.15mm. This printer shrinks holes ~0.21mm beyond the designed value, more than first assumed; the bearing would not press in without cracking the part at this size. Corrected `bearing_fit_clearance` to +0.06mm (designs the pocket 0.06mm *over* nominal bearing OD) to compensate for the observed shrinkage and land back near the original 21.85mm light-press-fit target. Re-rendered clean 2026-08-10.

**BEARING TEST 2026-08-10, second pass: PASSED.** Reprinted the coupon at `bearing_fit_clearance = +0.06mm` — bearing seated flush, no force issues, no cracking. **`pivot_frame_base.stl` and `pivot_frame_platform.stl` are cleared to print at this setting.**

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
- **Power architecture:** Bench PSU (Pyramid PS3KX, 13.8V) preferred during development; 4S LiPo (14.8V nominal, chosen over 3S to stay inside the shield's 12–24V range across the discharge curve) for untethered operation once the pivot frame is built. Determine whether Uno Q and SimpleFOC Shield share a supply rail with the rest of the system or run isolated.
- **Max wheel speed:** ~325 RPM at 12V (no-load). Load reduces this; factor into angular momentum budget when sizing the flywheel.
- **I2C bus:** BNO055 on RPi I2C. AS5600 on Uno Q I2C. No conflict. Confirm LSM6DSOX address (0x6A or 0x6B) does not collide with AS5600 (0x36) if both end up on the same Uno Q bus.
- **Outer loop rate:** 20Hz is a starting point. May need adjustment based on BNO055 output data rate and serial latency.
