/*
 * satlab — Subsystem Simulator
 *
 * Reads all sensors every SAMPLE_INTERVAL_MS and emits one newline-delimited
 * JSON packet per sensor over Serial at 9600 baud.
 *
 * 9600 baud matches realistic spacecraft UART housekeeping rates and is
 * consistent with the ≤1 kbps cross-link budget in the SBIR architecture.
 * The Wio Tracker SX1262 LoRa link (iteration 2) will operate near this
 * rate — designing to it now prevents format rework at radio integration.
 *
 * Packet format:
 *   {"ts":"<ISO8601>","subsystem":"<name>","sensor":"<name>","payload":{...}}
 *
 * Pin assignments (adjust to match your wiring):
 *   A0  — LDR light sensor (analog)
 *   A1  — Sound / microphone sensor (analog)
 *   D7  — DHT11/22 temp+humidity
 *   I2C — BMP280 air pressure (addr 0x76 or 0x77)
 *   I2C — MPU-6050 accelerometer (addr 0x68)
 *   I2C — SSD1306 OLED 128x64 (addr 0x3C)
 *
 * Required libraries (install via Arduino Library Manager):
 *   Adafruit DHT sensor library + Adafruit Unified Sensor
 *   Adafruit BMP280
 *   Adafruit MPU6050 + Adafruit Unified Sensor
 *   Adafruit SSD1306 + Adafruit GFX
 */

#include <Wire.h>
#include <DHT.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>

// ── Pin config ───────────────────────────────────────────────────────────────
#define PIN_LIGHT       A0
#define PIN_SOUND       A1
#define PIN_DHT         7
#define DHT_TYPE        DHT11    // change to DHT22 if needed

// ── Timing ───────────────────────────────────────────────────────────────────
#define SAMPLE_INTERVAL_MS  10000UL   // 10 seconds

// ── OLED ─────────────────────────────────────────────────────────────────────
#define OLED_WIDTH  128
#define OLED_HEIGHT  64
#define OLED_ADDR   0x3C

// ── Sensor objects ────────────────────────────────────────────────────────────
DHT           dht(PIN_DHT, DHT_TYPE);
Adafruit_BMP280 bmp;
Adafruit_MPU6050 mpu;
Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);

bool bmp_ok  = false;
bool mpu_ok  = false;
bool oled_ok = false;

unsigned long last_sample = 0;
uint32_t      cycle       = 0;

// ── Helpers ───────────────────────────────────────────────────────────────────

// Fake ISO-8601 timestamp; real time comes from RPi agent via WWVB/GPS.
// Arduino has no RTC — emit elapsed seconds since boot as a placeholder.
void print_timestamp() {
    unsigned long s = millis() / 1000UL;
    // Format: T+<seconds> — RPi agent replaces this with wall-clock UTC.
    Serial.print("\"T+");
    Serial.print(s);
    Serial.print("s\"");
}

void emit_packet(const char* subsystem, const char* sensor, const char* payload_json) {
    Serial.print("{\"ts\":");
    print_timestamp();
    Serial.print(",\"subsystem\":\"");
    Serial.print(subsystem);
    Serial.print("\",\"sensor\":\"");
    Serial.print(sensor);
    Serial.print("\",\"payload\":");
    Serial.print(payload_json);
    Serial.println("}");
}

void update_oled(float temp_c, float pressure_hpa, float ax, float ay, float az) {
    if (!oled_ok) return;
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);

    display.setCursor(0, 0);
    display.print("satlab  cycle:");
    display.println(cycle);

    display.print("T:");
    display.print(temp_c, 1);
    display.print("C  P:");
    display.print(pressure_hpa, 0);
    display.println("hPa");

    display.print("Ax:");
    display.print(ax, 2);
    display.print(" Ay:");
    display.println(ay, 2);

    display.print("Az:");
    display.println(az, 2);

    display.display();
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(9600);
    while (!Serial) {}

    Wire.begin();
    dht.begin();

    bmp_ok  = bmp.begin(0x76) || bmp.begin(0x77);
    mpu_ok  = mpu.begin();
    oled_ok = display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);

    if (oled_ok) {
        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(0, 0);
        display.println("satlab");
        display.println("subsystem_sim");
        display.println("ready");
        display.display();
    }

    // Emit sensor init status for RPi agent
    Serial.print("{\"ts\":");
    print_timestamp();
    Serial.print(",\"subsystem\":\"system\",\"sensor\":\"init\",\"payload\":{");
    Serial.print("\"bmp_ok\":");  Serial.print(bmp_ok  ? "true" : "false");
    Serial.print(",\"mpu_ok\":"); Serial.print(mpu_ok  ? "true" : "false");
    Serial.print(",\"oled_ok\":"); Serial.print(oled_ok ? "true" : "false");
    Serial.println("}}");
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    unsigned long now = millis();
    if (now - last_sample < SAMPLE_INTERVAL_MS) return;
    last_sample = now;
    cycle++;

    char buf[128];

    // ── EPS: light (solar panel / illumination analog) ────────────────────
    int light_raw = analogRead(PIN_LIGHT);
    float light_pct = (light_raw / 1023.0f) * 100.0f;
    snprintf(buf, sizeof(buf), "{\"raw\":%d,\"pct\":%.1f}", light_raw, light_pct);
    emit_packet("eps", "light", buf);

    // ── Structural: sound (microphone — vibration / structural health) ────
    int sound_raw = analogRead(PIN_SOUND);
    snprintf(buf, sizeof(buf), "{\"raw\":%d}", sound_raw);
    emit_packet("structural", "sound", buf);

    // ── TCS: temp + humidity ──────────────────────────────────────────────
    float humidity = dht.readHumidity();
    float temp_c   = dht.readTemperature();
    if (!isnan(humidity) && !isnan(temp_c)) {
        snprintf(buf, sizeof(buf), "{\"temp_c\":%.2f,\"humidity_pct\":%.2f}", temp_c, humidity);
        emit_packet("tcs", "dht", buf);
    }

    // ── TCS / Structural: air pressure ───────────────────────────────────
    float pressure_hpa = 1013.25f;  // fallback
    if (bmp_ok) {
        pressure_hpa = bmp.readPressure() / 100.0f;
        float bmp_temp = bmp.readTemperature();
        snprintf(buf, sizeof(buf), "{\"pressure_hpa\":%.2f,\"temp_c\":%.2f}", pressure_hpa, bmp_temp);
        emit_packet("structural", "bmp280", buf);
    }

    // ── ADCS: acceleration ────────────────────────────────────────────────
    float ax = 0, ay = 0, az = 0;
    if (mpu_ok) {
        sensors_event_t accel, gyro, temp_event;
        mpu.getEvent(&accel, &gyro, &temp_event);
        ax = accel.acceleration.x;
        ay = accel.acceleration.y;
        az = accel.acceleration.z;
        float gx = gyro.gyro.x;
        float gy = gyro.gyro.y;
        float gz = gyro.gyro.z;
        snprintf(buf, sizeof(buf),
            "{\"ax_ms2\":%.3f,\"ay_ms2\":%.3f,\"az_ms2\":%.3f"
            ",\"gx_rads\":%.3f,\"gy_rads\":%.3f,\"gz_rads\":%.3f}",
            ax, ay, az, gx, gy, gz);
        emit_packet("adcs", "mpu6050", buf);
    }

    update_oled(temp_c, pressure_hpa, ax, ay, az);
}
