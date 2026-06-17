# satlab — Project Plan
**Last updated:** 2026-06-17

satlab is a hardware-in-the-loop satellite simulator lab station. It consists of physical nodes running real sensors and actuators, integrated with Beamwarden as registered Beamrider nodes. The lab serves two purposes: technical credentialing for SBIR and commercial proposals, and ongoing experimentation with sensor fusion, hardware attestation, and autonomous health management.

---

## Current State (as of 2026-06-17)

### Operational nodes

| Node | Hardware | Function | Status |
|---|---|---|---|
| beamrider-0001 | RPi 3 + MightyOhm Geiger (emitter-0001) | Radiation telemetry via USB-serial | Operational |
| beamrider-0003 | RPi 3 (flight computer) + Arduino Uno R3 (sensor subsystem) | Multi-sensor telemetry: TCS, structural, EPS, ADCS | Operational |
| beamrider-0004 | RPi 5 + Sense HAT | ADCS + TCS telemetry; 8×8 LED health display | Operational |

All three nodes ingest to production Beamwarden (`app.beamwarden.com`). Beamforge UKF/NIS anomaly detection runs against all active sensors in real time.

### Sensors active on beamrider-0003

| Sensor | Subsystem | Interface |
|---|---|---|
| AHT20 | TCS (temp + humidity) | I2C 0x38 |
| DPS310 | Structural (pressure + temp) | I2C 0x77 |
| LIS3DHTR | ADCS (accel) | I2C 0x19 |
| LDR | EPS (light / solar analog) | A0 |
| Sound / microphone | Structural | A1 |
| Arduino Modulino Thermo | TCS | I2C |

---

## Build Tracks

---

### Track 1 — Hardware Signature Commissioning (IN PROGRESS)

**Goal:** Bind each Beamrider node's identity to its physical hardware using overlapping Allan deviation noise fingerprinting of ISM330DHCX IMU pairs. HMAC tags on health vector payloads attest that data originated from a specific physical unit.

**What is built:**
- `satlab/commissioning/` package: smbus2 I2C driver, dual-unit 120 s capture, OADEV computation, fingerprint extraction, `commission.py` + `verify.py` orchestration
- `beamwarden` management command: `set_hw_signature` loads fingerprint into `Beamrider.metadata`
- `agent/health.py`: HMAC tag computed via `SATLAB_HW_KEY` env var on every health vector publish

**Hardware on hand:**
- ST ISM330DHCX ×2 (0x6A + 0x6B via SA0 pin strapping)
- SparkFun ISM330DHCX Qwiic (SEN-20176, third unit)

**Remaining steps:**
1. Wire SA0 pins on both units (GND → 0x6A, 3.3V → 0x6B); connect to RPi i2c-1
2. Verify with `sudo i2cdetect -y 1`; confirm both addresses appear
3. Run `python commission.py --bus 1 --duration 120`; record `SATLAB_HW_KEY`
4. Run `set_hw_signature` management command on Beamwarden
5. Add `SATLAB_HW_KEY` to beamrider-0003 `.env`; restart agent; confirm `hmac_tag` in payloads
6. Run `verify.py` after 24 h to confirm MAPE stays below 15% threshold
7. Assess same-model distinguishability (cosine distance between the two dies)

**Blocker:** None. Hardware and software both ready. Physical wiring is the only remaining step.

---

### Track 2 — LoRa Radio Transport (Iteration 2)

**Goal:** Replace the USB serial link between the Arduino and RPi with a Wio Tracker SX1262 LoRa radio pair. Same JSON packet schema; swap only the transport layer. No changes to the beamrider agent.

**Hardware on hand:**
- Meshnology Wio Tracker L1 (SX1262 LoRa + nRF52840, 3000 mAh) ×3
- Adafruit #4410 Micro-Lipo USB-C charger ×2

**Architecture:**
- Arduino → Wio Tracker TX (LoRa at SF10/BW125, ~980 bps, ≤256-byte packets)
- RPi → Wio Tracker RX (presents as virtual serial port via USB)
- `serial_reader.py` requires no changes

**Steps:**
1. Flash Wio Tracker TX firmware (Arduino side): read from Arduino serial, repackage and transmit over LoRa
2. Flash Wio Tracker RX firmware (RPi side): receive LoRa packets, forward over USB-serial to RPi
3. Identify RX USB device by-id path; update `SATLAB_CROSSLINK_PORT`
4. Verify telemetry flows to Beamwarden with both Arduinos and both Wio Trackers plugged in
5. Document RF range and link margin at operating distance

**Dependency:** Track 1 should be complete before swapping transports to avoid losing visibility during the transition.

---

### Track 3 — Reaction Wheel ADCS Demonstrator

**Goal:** Single-axis reaction wheel hardware-in-the-loop demonstrator. Platform rotates; reaction wheel counter-rotates; BNO055 quaternion feedback drives attitude control. Inner velocity loop on Arduino Uno Q via SimpleFOC; outer attitude loop on RPi at ~20 Hz.

**Hardware on hand:**
- Arduino Uno Q (inner loop controller)
- Adafruit BNO055 (outer attitude loop, quaternion output)
- Adafruit LSM6DSOX (tumbling FSM gyro input)
- 608ZZ bearings: to acquire
- IdeaFormer PEO/PEI flex plate 235×235mm (on hand; install pending)
- Creality Ender 3 (operational; E-steps corrected)
- Digital calipers (for hole-fit verification)

**Hardware to acquire:**
- iPower GM4108H-120T BLDC gimbal motor
- SimpleFOC Shield v2
- AS5600 magnetic encoder + 10×2mm diametrically magnetized magnet
- 608ZZ bearings ×2
- M8 bolts + nuts (flywheel tuning masses)

**CAD (in progress, uncommitted):**
- `cad/flywheel_gm4108h.scad`: parametric rim-loaded flywheel, M8 tuning pockets; rotor bolt pattern is placeholder pending motor measurement
- `cad/print_test_coupon.scad`: M8 + M3 hole-fit validation coupon; Z height suspect (~4mm vs 6mm modeled), needs re-measurement on new plate

**Steps:**
1. Install PEI flex plate (IPA clean bed, re-level)
2. Print test coupon; measure all three axes with calipers; resolve Z discrepancy
3. Acquire GM4108H, SimpleFOC Shield, AS5600 + magnet, 608ZZ bearings, M8 hardware
4. Measure GM4108H rotor bolt circle; update `mount_*`/`boss_*` in `flywheel_gm4108h.scad`
5. Print flywheel; print motor holder (from scratch, GM4108H round face)
6. Wire AS5600 + SimpleFOC Shield + GM4108H to Uno Q; run `find_pole_pairs`; confirm motor spins both directions
7. Wire BNO055 and LSM6DSOX to Uno Q and RPi respectively; confirm I2C addresses no conflict
8. Thread 4 wires (5V, GND, TX, RX) through hollow pivot axle; seat axle in 608ZZ bearings
9. Implement inner velocity loop (SimpleFOC) + tumbling FSM (LSM6DSOX gyro, hysteresis bands: detumble >360 dps, re-engage <45 dps)
10. Implement outer attitude loop on RPi (BNO055 quaternion → velocity command to Uno Q)
11. Verify counter-rotation against commanded attitude step; tune PID gains (reference: charleslabs P=2.5, D=400)
12. Wire reaction wheel telemetry into Beamwarden as a new sensor on beamrider-0003

---

### Track 4 — Ground Station (RTL-SDR)

**Goal:** RPi 4 + RTL-SDR V3 R860 receiving real or CubeSatSim-broadcast satellite signals, registered in Beamwarden as a new Beamrider node. Closes the transmit/receive loop: flight simulator transmits, ground station receives, both ingest to Beamwarden.

**Hardware on hand:**
- Raspberry Pi 4 Model B (2 GB) ×2 (one for ground station, one spare/second node)
- RTL-SDR Blog V3 R860
- Dipole antenna kit

**Reference:** github.com/alanbjohnston/CubeSatSim — broadcasts simulated satellite telemetry over FM/Morse at 433 MHz; RTL-SDR receives it.

**Steps:**
1. Provision one RPi 4 (Debian Bookworm or Trixie); install `rtl-sdr` package
2. Connect RTL-SDR dongle + dipole; confirm `rtl_test` sees the device
3. Establish CubeSatSim signal source (Wio Tracker TX on 433 MHz, or separate CubeSatSim node)
4. Write ground station agent: demodulate/decode received packets, format as Beamwarden ingest payload
5. Register new Beamrider node in Beamwarden; obtain bearer token
6. Deploy agent as systemd service; confirm telemetry flowing
7. Evaluate: SenseCap Solar Node as an outdoor RF source for extended range testing

**Dependency:** Track 2 (LoRa) provides the Wio Tracker TX infrastructure that the ground station can receive from.

---

### Track 5 — ADCS Sensor Suite Integration

**Goal:** Bring the full on-hand ADCS sensor suite (LSM6DSOX, LSM9DS1, BNO055, TMAG5273, NEO-M9N GPS) online as Beamwarden sensors. Upgrade beamrider-0003 from the current LIS3DHTR placeholder to a real 9-DoF + magnetometer + orientation stack.

**Hardware on hand:**
- Adafruit LSM6DSOX 6DoF IMU (STEMMA QT)
- Adafruit LSM9DS1 9DoF Breakout
- Adafruit BNO055 9DoF Absolute Orientation IMU (shared with Track 3)
- Adafruit TMAG5273 3D Hall Effect Magnetometer
- SparkFun GPS Breakout NEO-M9N, SMA (Qwiic)
- GPS/GNSS Magnetic Mount Antenna 3m SMA
- XIITIA GY-NEO7mV2 GPS Modules ×3
- Canaduino WWVB/MSF 60 kHz Atomic Clock receiver
- MQ4 Methane Gas Sensor ×2
- SparkFun Qwiic Cable Kit ×2

**Steps:**
1. Wire LSM6DSOX (STEMMA QT) to RPi I2C; confirm address (0x6A or 0x6B); add ingest sensor
2. Wire LSM9DS1 to RPi I2C; add mag + secondary accel/gyro ingest sensor
3. Wire NEO-M9N GPS via Qwiic to RPi; connect SMA antenna; configure `gpsd`; add orbit position sensor
4. Wire WWVB receiver; validate time reference against NTP; document sync accuracy
5. Wire MQ4 sensors to Arduino A2; add propulsion/atmosphere sensor in sketch and Beamwarden
6. Evaluate TMAG5273 placement for magnetic attitude determination
7. Evaluate whether BNO055 attitude output should feed both the reaction wheel (Track 3) and Beamwarden simultaneously

---

### Track 6 — Remote Management (Iteration 3)

**Goal:** Beamwarden deploys and manages the beamrider agent on RPi nodes via SSH/Ansible, mirroring operational ground station management.

**Steps:**
1. Define Ansible playbook for beamrider agent install, `.env` configuration, and service lifecycle
2. Integrate playbook trigger into Beamwarden (deploy button on node detail page)
3. Validate against beamrider-0003 and beamrider-0004
4. Document as the standard provisioning path; replace current `install-sense-service.sh` approach

**Dependency:** Tracks 1 and 2 should be stable before automating deployment.

---

## Hardware Acquisition Queue

Items needed before blocked tracks can proceed, in priority order:

| Item | Blocks | Priority |
|---|---|---|
| iPower GM4108H-120T BLDC motor | Track 3 | High |
| SimpleFOC Shield v2 | Track 3 | High |
| AS5600 encoder + 10×2mm magnet | Track 3 | High |
| 608ZZ bearings ×2 | Track 3 | High |
| M8 hardware (bolts + nuts) | Track 3 | High |

---

## Reference Links

- CubeSatSim: github.com/alanbjohnston/CubeSatSim
- SimpleFOC: docs.simplefoc.com
- NASA CFS: ntrs.nasa.gov/api/citations/20150023353/downloads/20150023353.pdf
- SGP4: pypi.org/project/sgp4
- RTL-SDR: rtl-sdr.com
- CelesTrak: celestrak.org
- pySerial: pyserial.readthedocs.io
