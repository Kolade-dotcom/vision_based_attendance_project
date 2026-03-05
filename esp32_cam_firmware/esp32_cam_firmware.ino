/*
 * ESP32-CAM Attendance System Firmware
 *
 * Features:
 * - MJPEG video streaming on port 81
 * - HTTP control server on port 80
 * - 16x2 LCD display (I2C)
 * - Active buzzer for audio feedback (on/off only, no frequency control)
 * - Status LED for connection indication
 *
 * Hardware Connections:
 * - LCD SDA: GPIO 14
 * - LCD SCL: GPIO 15
 * - Buzzer: GPIO 12 (active buzzer - connects to VCC via transistor if needed)
 * - LED: GPIO 13
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ArduinoJson.h>

// =============================================================================
// CONFIGURATION - Edit these values for your setup
// =============================================================================

// WiFi Credentials
const char *WIFI_SSID = "Redmi 10A";
const char *WIFI_PASSWORD = "hotsc06e";

// Static IP Configuration (recommended)
// Set USE_STATIC_IP to false to use DHCP instead
#define USE_STATIC_IP true
IPAddress staticIP(192, 168, 1, 100);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(8, 8, 8, 8);

// Hardware Pin Definitions
#define LCD_SDA_PIN 14
#define LCD_SCL_PIN 15
#define BUZZER_PIN 12
#define LED_PIN 13

// LCD I2C Address (common addresses: 0x27 or 0x3F)
#define LCD_ADDRESS 0x27
#define LCD_COLS 16
#define LCD_ROWS 2

// Camera Settings
#define CAMERA_MODEL_AI_THINKER // Most common ESP32-CAM module

// Timing Constants
#define HEARTBEAT_TIMEOUT 10000    // 10 seconds without heartbeat = disconnected
#define WIFI_CONNECT_TIMEOUT 20000 // 20 seconds to connect to WiFi

// =============================================================================
// CAMERA PIN DEFINITIONS (AI-Thinker ESP32-CAM)
// =============================================================================

#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

// =============================================================================
// GLOBAL OBJECTS
// =============================================================================

WebServer server(80);
WebServer streamServer(81);
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// LED State Machine
enum LEDState
{
    LED_OFF,
    LED_SLOW_BLINK,
    LED_FAST_BLINK,
    LED_SOLID,
    LED_FLASH
};

LEDState currentLEDState = LED_OFF;
unsigned long lastHeartbeat = 0;
unsigned long lastLEDUpdate = 0;
unsigned long ledFlashStart = 0;
bool ledOn = false;

// Stream client tracking
WiFiClient streamClient;

// =============================================================================
// CAMERA INITIALIZATION
// =============================================================================

bool initCamera()
{
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    // Frame size and quality based on PSRAM availability
    if (psramFound())
    {
        config.frame_size = FRAMESIZE_VGA; // 640x480 - good for face recognition
        config.jpeg_quality = 12;          // 0-63, lower = better quality
        config.fb_count = 2;               // Double buffer for smoother streaming
    }
    else
    {
        config.frame_size = FRAMESIZE_CIF; // 400x296 - fallback without PSRAM
        config.jpeg_quality = 15;
        config.fb_count = 1;
    }

    // Initialize camera
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK)
    {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        return false;
    }

    // Camera settings for better face detection
    sensor_t *s = esp_camera_sensor_get();
    if (s)
    {
        s->set_brightness(s, 0);                 // -2 to 2
        s->set_contrast(s, 0);                   // -2 to 2
        s->set_saturation(s, 0);                 // -2 to 2
        s->set_whitebal(s, 1);                   // 0 = disable, 1 = enable
        s->set_awb_gain(s, 1);                   // 0 = disable, 1 = enable
        s->set_wb_mode(s, 0);                    // 0 to 4
        s->set_exposure_ctrl(s, 1);              // 0 = disable, 1 = enable
        s->set_aec2(s, 0);                       // 0 = disable, 1 = enable
        s->set_gain_ctrl(s, 1);                  // 0 = disable, 1 = enable
        s->set_agc_gain(s, 0);                   // 0 to 30
        s->set_gainceiling(s, (gainceiling_t)0); // 0 to 6
        s->set_bpc(s, 0);                        // 0 = disable, 1 = enable
        s->set_wpc(s, 1);                        // 0 = disable, 1 = enable
        s->set_raw_gma(s, 1);                    // 0 = disable, 1 = enable
        s->set_lenc(s, 1);                       // 0 = disable, 1 = enable
        s->set_hmirror(s, 0);                    // 0 = disable, 1 = enable
        s->set_vflip(s, 0);                      // 0 = disable, 1 = enable
    }

    Serial.println("Camera initialized successfully");
    return true;
}

// =============================================================================
// LCD FUNCTIONS
// =============================================================================

void initLCD()
{
    // Initialize I2C with custom pins
    Wire.begin(LCD_SDA_PIN, LCD_SCL_PIN);

    lcd.init();
    lcd.backlight();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Attendance Sys");
    lcd.setCursor(0, 1);
    lcd.print("Initializing...");

    Serial.println("LCD initialized");
}

void displayMessage(const char *line1, const char *line2)
{
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(line1);
    lcd.setCursor(0, 1);
    lcd.print(line2);

    Serial.printf("LCD: %s | %s\n", line1, line2);
}

void clearLCD()
{
    lcd.clear();
    Serial.println("LCD cleared");
}

// =============================================================================
// BUZZER FUNCTIONS (Active Buzzer - on/off only, no frequency control)
// Note: Many active buzzers are "active LOW" - they beep when pin is LOW
// =============================================================================

void initBuzzer()
{
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, HIGH);  // HIGH = OFF for active-low buzzers
    Serial.println("Buzzer initialized");
}

// For active buzzer: simple beep with duration control
void beep(int duration)
{
    digitalWrite(BUZZER_PIN, LOW);   // LOW = ON for active-low buzzers
    delay(duration);
    digitalWrite(BUZZER_PIN, HIGH);  // HIGH = OFF
}

void playSuccessTone()
{
    // Three quick ascending-style beeps (shorter pauses = upbeat feel)
    beep(100);
    delay(50);
    beep(100);
    delay(50);
    beep(150);

    Serial.println("Success tone played");
}

void playErrorTone()
{
    // Two long slow beeps (warning feel)
    beep(300);
    delay(200);
    beep(300);

    Serial.println("Error tone played");
}

void playLateTone()
{
    // Two medium beeps (attention feel)
    beep(150);
    delay(100);
    beep(150);

    Serial.println("Late tone played");
}

// =============================================================================
// LED FUNCTIONS
// =============================================================================

void initLED()
{
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    currentLEDState = LED_OFF;
    Serial.println("LED initialized");
}

void updateLED()
{
    unsigned long now = millis();

    // Check heartbeat timeout
    if (currentLEDState == LED_SOLID)
    {
        if (now - lastHeartbeat > HEARTBEAT_TIMEOUT)
        {
            currentLEDState = LED_FAST_BLINK;
            Serial.println("Heartbeat timeout - lost connection");
        }
    }

    switch (currentLEDState)
    {
    case LED_OFF:
        digitalWrite(LED_PIN, LOW);
        break;

    case LED_SLOW_BLINK:
        // 1 second on, 1 second off
        if (now - lastLEDUpdate >= 1000)
        {
            ledOn = !ledOn;
            digitalWrite(LED_PIN, ledOn ? HIGH : LOW);
            lastLEDUpdate = now;
        }
        break;

    case LED_FAST_BLINK:
        // 200ms on, 200ms off
        if (now - lastLEDUpdate >= 200)
        {
            ledOn = !ledOn;
            digitalWrite(LED_PIN, ledOn ? HIGH : LOW);
            lastLEDUpdate = now;
        }
        break;

    case LED_SOLID:
        digitalWrite(LED_PIN, HIGH);
        break;

    case LED_FLASH:
        // Brief off (100ms) then back to solid
        if (ledFlashStart == 0)
        {
            ledFlashStart = now;
            digitalWrite(LED_PIN, LOW);
        }
        else if (now - ledFlashStart >= 100)
        {
            digitalWrite(LED_PIN, HIGH);
            currentLEDState = LED_SOLID;
            ledFlashStart = 0;
        }
        break;
    }
}

void flashLED()
{
    currentLEDState = LED_FLASH;
    ledFlashStart = 0;
}

// =============================================================================
// HTTP HANDLERS - Control Server (Port 80)
// =============================================================================

void handleRoot()
{
    String html = "<!DOCTYPE html><html><head><title>ESP32-CAM Attendance</title>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
    html += "<style>body{font-family:Arial;text-align:center;padding:20px;}";
    html += "h1{color:#333;}a{display:inline-block;margin:10px;padding:15px 30px;";
    html += "background:#007bff;color:white;text-decoration:none;border-radius:5px;}";
    html += "a:hover{background:#0056b3;}</style></head><body>";
    html += "<h1>ESP32-CAM Attendance System</h1>";
    html += "<p>IP Address: " + WiFi.localIP().toString() + "</p>";
    html += "<p><a href='http://" + WiFi.localIP().toString() + ":81/stream'>View Stream</a></p>";
    html += "<p><a href='/status'>Check Status</a></p>";
    html += "</body></html>";

    server.send(200, "text/html", html);
}

void handleStatus()
{
    StaticJsonDocument<256> doc;
    doc["status"] = "ok";
    doc["device"] = "ESP32-CAM";
    doc["ip"] = WiFi.localIP().toString();
    doc["rssi"] = WiFi.RSSI();
    doc["uptime"] = millis() / 1000;
    doc["psram"] = psramFound();
    doc["heap_free"] = ESP.getFreeHeap();

    String response;
    serializeJson(doc, response);

    server.send(200, "application/json", response);
}

void handleHeartbeat()
{
    lastHeartbeat = millis();
    currentLEDState = LED_SOLID;

    StaticJsonDocument<64> doc;
    doc["status"] = "ok";
    doc["timestamp"] = lastHeartbeat;

    String response;
    serializeJson(doc, response);

    server.send(200, "application/json", response);
}

void handleLCD()
{
    if (server.method() != HTTP_POST)
    {
        server.send(405, "application/json", "{\"error\":\"Method not allowed\"}");
        return;
    }

    String body = server.arg("plain");
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, body);

    if (error)
    {
        server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
        return;
    }

    const char *line1 = doc["line1"] | "";
    const char *line2 = doc["line2"] | "";

    displayMessage(line1, line2);

    // Flash LED on display update
    flashLED();

    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"LCD updated\"}");
}

void handleLCDClear()
{
    clearLCD();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"LCD cleared\"}");
}

void handleBuzzerSuccess()
{
    playSuccessTone();
    flashLED();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Success tone played\"}");
}

void handleBuzzerError()
{
    playErrorTone();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Error tone played\"}");
}

void handleBuzzerLate()
{
    playLateTone();
    flashLED();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Late tone played\"}");
}

void handleCapture()
{
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb)
    {
        server.send(500, "text/plain", "Camera capture failed");
        return;
    }

    server.sendHeader("Content-Disposition", "inline; filename=capture.jpg");
    server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);

    esp_camera_fb_return(fb);
}

void handleNotFound()
{
    server.send(404, "application/json", "{\"error\":\"Not found\"}");
}

// =============================================================================
// HTTP HANDLERS - Stream Server (Port 81)
// =============================================================================

void handleStream()
{
    WiFiClient client = streamServer.client();

    String response = "HTTP/1.1 200 OK\r\n";
    response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n";
    response += "Access-Control-Allow-Origin: *\r\n";
    response += "\r\n";
    client.print(response);

    while (client.connected())
    {
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb)
        {
            Serial.println("Camera capture failed");
            break;
        }

        String header = "--frame\r\n";
        header += "Content-Type: image/jpeg\r\n";
        header += "Content-Length: " + String(fb->len) + "\r\n";
        header += "\r\n";

        client.print(header);
        client.write(fb->buf, fb->len);
        client.print("\r\n");

        esp_camera_fb_return(fb);

        // Small delay to control frame rate
        delay(10);
    }
}

// =============================================================================
// WIFI CONNECTION
// =============================================================================

bool connectWiFi()
{
    Serial.println();
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);

    currentLEDState = LED_SLOW_BLINK;
    displayMessage("Connecting to", "WiFi...");

    WiFi.mode(WIFI_STA);

    if (USE_STATIC_IP)
    {
        if (!WiFi.config(staticIP, gateway, subnet, dns))
        {
            Serial.println("Static IP configuration failed");
        }
    }

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long startTime = millis();
    while (WiFi.status() != WL_CONNECTED)
    {
        updateLED();
        delay(100);

        if (millis() - startTime > WIFI_CONNECT_TIMEOUT)
        {
            Serial.println("\nWiFi connection timeout!");
            displayMessage("WiFi Failed!", "Check settings");
            return false;
        }

        if ((millis() - startTime) % 1000 < 100)
        {
            Serial.print(".");
        }
    }

    Serial.println();
    Serial.print("Connected! IP: ");
    Serial.println(WiFi.localIP());

    currentLEDState = LED_FAST_BLINK;

    char ipStr[16];
    WiFi.localIP().toString().toCharArray(ipStr, 16);
    displayMessage("WiFi Connected!", ipStr);

    return true;
}

// =============================================================================
// SERVER SETUP
// =============================================================================

void setupServers()
{
    // Control server routes (port 80)
    server.on("/", handleRoot);
    server.on("/status", HTTP_GET, handleStatus);
    server.on("/heartbeat", HTTP_GET, handleHeartbeat);
    server.on("/lcd", HTTP_POST, handleLCD);
    server.on("/lcd/clear", HTTP_GET, handleLCDClear);
    server.on("/buzzer/success", HTTP_GET, handleBuzzerSuccess);
    server.on("/buzzer/error", HTTP_GET, handleBuzzerError);
    server.on("/buzzer/late", HTTP_GET, handleBuzzerLate);
    server.on("/capture", HTTP_GET, handleCapture);
    server.onNotFound(handleNotFound);

    // Enable CORS
    server.enableCORS(true);

    server.begin();
    Serial.println("Control server started on port 80");

    // Stream server routes (port 81)
    streamServer.on("/stream", HTTP_GET, handleStream);
    streamServer.on("/", HTTP_GET, []()
                    {
        streamServer.sendHeader("Location", "/stream");
        streamServer.send(302); });

    streamServer.begin();
    Serial.println("Stream server started on port 81");
}

// =============================================================================
// SETUP
// =============================================================================

void setup()
{
    Serial.begin(115200);
    Serial.println();
    Serial.println("================================");
    Serial.println("ESP32-CAM Attendance System");
    Serial.println("================================");

    // Initialize hardware
    initLED();
    initBuzzer();
    initLCD();

    // Play startup beep
    beep(100);

    // Initialize camera
    if (!initCamera())
    {
        displayMessage("Camera Error!", "Check wiring");
        while (1)
        {
            updateLED();
            delay(100);
        }
    }

    // Connect to WiFi
    if (!connectWiFi())
    {
        while (1)
        {
            updateLED();
            delay(100);
        }
    }

    // Setup HTTP servers
    setupServers();

    // Ready!
    displayMessage("System Ready", "Waiting...");
    Serial.println();
    Serial.println("System ready!");
    Serial.print("Control: http://");
    Serial.print(WiFi.localIP());
    Serial.println("/");
    Serial.print("Stream:  http://");
    Serial.print(WiFi.localIP());
    Serial.println(":81/stream");
    Serial.println();

    // Success startup tone
    playSuccessTone();
}

// =============================================================================
// MAIN LOOP
// =============================================================================

void loop()
{
    // Handle HTTP requests
    server.handleClient();
    streamServer.handleClient();

    // Update LED state
    updateLED();

    // Small delay to prevent watchdog issues
    delay(1);
}
