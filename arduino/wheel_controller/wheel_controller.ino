/*
 * satlab — Reaction Wheel Controller (Uno Q)
 *
 * Inner velocity loop for the single-axis reaction-wheel demonstrator. Runs
 * SimpleFOC closed-loop velocity control on the GM4108H gimbal motor via the
 * AS5600 rotor encoder, parses wheel-speed setpoints from the RPi over
 * serial, runs the tumbling-detection FSM against the LSM6DSOX gyro, and
 * emits wheel telemetry. See docs/reaction-wheel.md for the full build doc.
 *
 * BNO055 attitude sensing is NOT on this board -- it wires directly to the
 * RPi's own I2C bus (see docs/reaction-wheel.md Build sequence step 5). This
 * board only reads AS5600 (rotor position, via SimpleFOC) and LSM6DSOX
 * (tumbling detection).
 *
 * Serial protocol (9600 baud, matches the rest of the satlab serial link):
 *   RPi -> Uno Q (event-driven):  {"cmd":"vel","val":78.5}
 *   Uno Q -> RPi (10Hz):          {"ts":"T+30s","subsystem":"adcs","sensor":"wheel","payload":{"rpm":125,"fault":false,"mode":"hold"}}
 *
 * Required libraries (install via arduino-cli lib install):
 *   Simple FOC
 *   Adafruit LSM6DS
 *   Adafruit Unified Sensor
 *
 * LSM6DSOX I2C address: 0x6A (Adafruit breakout default, SDO/SA0 low).
 * Per docs/reaction-wheel.md open questions this hasn't been confirmed
 * against a real bus scan yet -- if init fails, try 0x6B.
 */

#include <SimpleFOC.h>
#include <Adafruit_LSM6DSOX.h>

// ── Motor / driver / encoder ─────────────────────────────────────────────────
// 24N/22P GM4108H-120T -> 11 pole pairs. Pin assignment matches the
// SimpleFOC Shield v2 default PWM pinout.
BLDCMotor motor       = BLDCMotor(11);
BLDCDriver3PWM driver = BLDCDriver3PWM(9, 5, 6, 8);
MagneticSensorI2C as5600 = MagneticSensorI2C(AS5600_I2C);

// ── LSM6DSOX (tumbling FSM input) ────────────────────────────────────────────
Adafruit_LSM6DSOX lsm6dsox;
bool lsm_ok = false;
#define LSM6DSOX_ADDR 0x6A

// ── Tumbling FSM ──────────────────────────────────────────────────────────────
// Hysteresis band from the charleslabs reference firmware (docs/reaction-wheel.md
// "Control heritage"): drop into TUMBLING above 360 deg/s, only re-engage
// NOMINAL once the rate falls back below 45 deg/s. The gap avoids chatter
// right at a single threshold.
enum WheelMode { MODE_IDLE, MODE_HOLD, MODE_SLEW, MODE_DETUMBLE, MODE_FAULT };
WheelMode current_mode = MODE_IDLE;

const float TUMBLE_ENTER_DPS = 360.0f;
const float TUMBLE_EXIT_DPS  = 45.0f;
const float DETUMBLE_VEL_RAD_S = 20.0f; // conservative counter-spin target, tune on bench

bool tumbling = false;

// ── Serial command parsing ───────────────────────────────────────────────────
char serial_buf[64];
uint8_t serial_len = 0;
float target_velocity = 0.0f;
bool have_target = false;

// ── Timing ────────────────────────────────────────────────────────────────────
const unsigned long INNER_LOOP_US   = 10000UL;  // 100Hz
const unsigned long TELEMETRY_MS    = 100UL;    // 10Hz
unsigned long last_inner_us  = 0;
unsigned long last_telemetry_ms = 0;

// ── Helpers ───────────────────────────────────────────────────────────────────

// Arduino has no RTC -- emit elapsed seconds since boot as a placeholder,
// same convention as arduino/subsystem_sim/subsystem_sim.ino. RPi agent
// replaces this with wall-clock UTC before ingesting.
void print_timestamp() {
    unsigned long s = millis() / 1000UL;
    Serial.print("\"T+");
    Serial.print(s);
    Serial.print("s\"");
}

const char* mode_str(WheelMode m) {
    switch (m) {
        case MODE_HOLD:     return "hold";
        case MODE_SLEW:     return "slew";
        case MODE_DETUMBLE: return "detumble";
        case MODE_FAULT:    return "fault";
        default:            return "idle";
    }
}

// Parse {"cmd":"vel","val":<float>} without a JSON library, matching the
// project's existing preference for direct/lightweight parsing over adding
// a new dependency for a single fixed schema (see subsystem_sim.ino).
void handle_command(const char* line) {
    const char* val_key = strstr(line, "\"val\"");
    if (!val_key) return;
    const char* colon = strchr(val_key, ':');
    if (!colon) return;
    target_velocity = atof(colon + 1);
    have_target = true;
}

void poll_serial_commands() {
    while (Serial.available() > 0) {
        char c = Serial.read();
        if (c == '\n') {
            serial_buf[serial_len] = '\0';
            if (serial_len > 0) handle_command(serial_buf);
            serial_len = 0;
        } else if (serial_len < sizeof(serial_buf) - 1) {
            serial_buf[serial_len++] = c;
        }
        // else: line too long, drop silently and keep filling until newline
    }
}

void update_tumbling_fsm() {
    if (!lsm_ok) return;

    sensors_event_t accel, gyro, temp;
    lsm6dsox.getEvent(&accel, &gyro, &temp);

    // gyro.gyro.{x,y,z} from the Adafruit unified sensor event are in rad/s;
    // convert to deg/s to match the heritage hysteresis thresholds.
    float rate_dps = sqrt(gyro.gyro.x * gyro.gyro.x +
                          gyro.gyro.y * gyro.gyro.y +
                          gyro.gyro.z * gyro.gyro.z) * RAD_TO_DEG;

    if (!tumbling && rate_dps > TUMBLE_ENTER_DPS) {
        tumbling = true;
    } else if (tumbling && rate_dps < TUMBLE_EXIT_DPS) {
        tumbling = false;
    }
}

void emit_telemetry(float rpm, bool fault) {
    Serial.print("{\"ts\":");
    print_timestamp();
    Serial.print(",\"subsystem\":\"adcs\",\"sensor\":\"wheel\",\"payload\":{");
    Serial.print("\"rpm\":");
    Serial.print(rpm, 1);
    Serial.print(",\"fault\":");
    Serial.print(fault ? "true" : "false");
    Serial.print(",\"mode\":\"");
    Serial.print(mode_str(current_mode));
    Serial.println("\"}}");
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(9600);
    while (!Serial) {}

    Wire.begin();
    delay(100);

    lsm_ok = lsm6dsox.begin_I2C(LSM6DSOX_ADDR);
    if (lsm_ok) {
        lsm6dsox.setGyroDataRate(LSM6DS_RATE_104_HZ);
        lsm6dsox.setGyroRange(LSM6DS_GYRO_RANGE_500_DPS);
    }

    as5600.init();
    motor.linkSensor(&as5600);

    driver.voltage_power_supply = 12; // nominal -- actual supply is either the
                                       // bench PSU (13.8V) or the 4S LiPo
                                       // (14.8V nominal), both within the
                                       // shield's 12-24V TB_PWR range
    driver.init();
    motor.linkDriver(&driver);

    motor.controller = MotionControlType::velocity;
    motor.PID_velocity.P = 0.5;
    motor.PID_velocity.I = 10;
    motor.PID_velocity.D = 0.001;
    motor.voltage_limit  = 6;  // start conservative -- tune on the bench per
                                // docs/reaction-wheel.md build sequence step 2
                                // before mounting on the pivot frame

    motor.init();
    motor.initFOC();

    current_mode = MODE_HOLD;

    // Init status, same convention as subsystem_sim.ino's system/init packet
    Serial.print("{\"ts\":");
    print_timestamp();
    Serial.print(",\"subsystem\":\"system\",\"sensor\":\"init\",\"payload\":{");
    Serial.print("\"lsm_ok\":");
    Serial.print(lsm_ok ? "true" : "false");
    Serial.println("}}");
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    // Inner FOC loop -- must run as fast as possible, not gated to 100Hz.
    // loopFOC() handles its own internal timing; the 100Hz figure governs
    // move()/setpoint updates below, not the FOC commutation itself.
    motor.loopFOC();

    unsigned long now_us = micros();
    if (now_us - last_inner_us >= INNER_LOOP_US) {
        last_inner_us = now_us;

        poll_serial_commands();
        update_tumbling_fsm();

        if (tumbling) {
            current_mode = MODE_DETUMBLE;
            // Counter-spin against the sensed rotation -- sign/axis mapping
            // is not yet validated against the physical pivot orientation,
            // fixed positive-direction counter for now. Confirm once the
            // pivot frame + BNO055 are on the bench (build sequence step 9/10).
            motor.move(DETUMBLE_VEL_RAD_S);
        } else if (have_target) {
            current_mode = (fabs(target_velocity) > 0.01f) ? MODE_SLEW : MODE_HOLD;
            motor.move(target_velocity);
        } else {
            current_mode = MODE_HOLD;
            motor.move(0);
        }
    }

    unsigned long now_ms = millis();
    if (now_ms - last_telemetry_ms >= TELEMETRY_MS) {
        last_telemetry_ms = now_ms;
        float rpm = motor.shaft_velocity * 60.0f / (2.0f * PI);
        emit_telemetry(rpm, false);
    }
}
