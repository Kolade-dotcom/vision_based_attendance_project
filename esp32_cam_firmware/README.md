# ESP32-CAM Firmware Setup Guide

This folder contains the Arduino firmware for the ESP32-CAM module used in the Vision Attendance System.

## Prerequisites

### 1. Install Arduino IDE

Download and install [Arduino IDE](https://www.arduino.cc/en/software) (version 2.x recommended).

### 2. Add ESP32 Board Support

1. Open Arduino IDE
2. Go to **File > Preferences**
3. In "Additional Board Manager URLs", add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Go to **Tools > Board > Boards Manager**
5. Search for "esp32" and install **esp32 by Espressif Systems**

### 3. Install Required Libraries

Go to **Tools > Manage Libraries** and install:

| Library | Author | Version |
|---------|--------|---------|
| LiquidCrystal I2C | Frank de Brabander | 1.1.2+ |
| ArduinoJson | Benoit Blanchon | 6.x |

The camera and WiFi libraries are included with the ESP32 board package.

## Hardware Setup

### Components Needed

- ESP32-CAM (AI-Thinker module)
- USB-to-Serial programmer (FTDI or similar)
- 16x2 LCD with I2C backpack
- **Active buzzer** (3.3V or 5V)
- LED (any color) + 220Ω resistor
- Jumper wires

**Note on Buzzers:**
- **Active buzzer**: Recommended. Has built-in oscillator, beeps when power applied. Usually has a sticker with voltage rating.
- **Passive buzzer**: Not supported by this firmware. Requires PWM frequency control.

### Wiring

| Component | ESP32-CAM Pin |
|-----------|---------------|
| LCD SDA | GPIO 14 |
| LCD SCL | GPIO 15 |
| LCD VCC | 5V |
| LCD GND | GND |
| Buzzer + (active) | GPIO 12 |
| Buzzer - | GND |
| LED + (through 220Ω) | GPIO 13 |
| LED - | GND |

### Programmer Connection (for uploading)

| FTDI | ESP32-CAM |
|------|-----------|
| 5V | 5V |
| GND | GND |
| TX | U0R |
| RX | U0T |
| - | IO0 → GND (boot mode) |

**Important:** Connect GPIO 0 to GND only during upload, then disconnect for normal operation.

## Configuration

Before uploading, edit these values in `esp32_cam_firmware.ino`:

```cpp
// WiFi Credentials (REQUIRED - change these!)
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Static IP (optional but recommended)
IPAddress staticIP(192, 168, 1, 100);  // Pick an unused IP
IPAddress gateway(192, 168, 1, 1);      // Your router's IP
IPAddress subnet(255, 255, 255, 0);

// LCD I2C Address (try 0x27 first, if not working try 0x3F)
#define LCD_ADDRESS 0x27
```

### Finding Your LCD I2C Address

If the LCD doesn't work, run this I2C scanner sketch to find the address:

```cpp
#include <Wire.h>

void setup() {
    Wire.begin(14, 15);  // SDA=14, SCL=15
    Serial.begin(115200);
    Serial.println("I2C Scanner");
}

void loop() {
    for (byte addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.print("Found: 0x");
            Serial.println(addr, HEX);
        }
    }
    delay(5000);
}
```

## Upload Instructions

1. Connect ESP32-CAM to programmer (with GPIO 0 connected to GND)
2. Open `esp32_cam_firmware.ino` in Arduino IDE
3. Select board: **Tools > Board > ESP32 Arduino > AI Thinker ESP32-CAM**
4. Select port: **Tools > Port > (your COM port)**
5. Click **Upload** button
6. Wait for "Connecting..." then press the RESET button on ESP32-CAM
7. Wait for upload to complete
8. **Disconnect GPIO 0 from GND**
9. Press RESET button again

## Testing

### 1. Open Serial Monitor

- **Tools > Serial Monitor**
- Set baud rate to **115200**
- You should see:

```
================================
ESP32-CAM Attendance System
================================
LED initialized
Buzzer initialized
LCD initialized
Camera initialized successfully
Connecting to WiFi: YourNetwork
.....
Connected! IP: 192.168.1.100
Control server started on port 80
Stream server started on port 81
System ready!
```

### 2. Test in Browser

Open these URLs in your browser:

| URL | Expected Result |
|-----|-----------------|
| `http://192.168.1.100/` | Web interface with links |
| `http://192.168.1.100/status` | JSON status response |
| `http://192.168.1.100:81/stream` | Live video stream |

### 3. Test LCD and Buzzer

Using curl (or Postman):

```bash
# Test LCD
curl -X POST http://192.168.1.100/lcd \
  -H "Content-Type: application/json" \
  -d '{"line1":"Hello","line2":"World"}'

# Clear LCD
curl http://192.168.1.100/lcd/clear

# Test buzzer
curl http://192.168.1.100/buzzer/success
curl http://192.168.1.100/buzzer/error

# Test heartbeat (LED should go solid)
curl http://192.168.1.100/heartbeat
```

## LED States

| State | Pattern | Meaning |
|-------|---------|---------|
| OFF | - | Not powered |
| SLOW BLINK | 1s on/off | Connecting to WiFi |
| FAST BLINK | 200ms on/off | WiFi connected, no server |
| SOLID | Always on | Connected to Python server |
| FLASH | Brief off | Recognition event |

## Troubleshooting

### Camera not initializing
- Check camera ribbon cable connection
- Ensure camera is seated properly
- Try power cycling

### LCD not working
- Run I2C scanner to find correct address
- Check wiring (SDA to GPIO 14, SCL to GPIO 15)
- Ensure LCD is powered with 5V

### WiFi not connecting
- Verify SSID and password
- Check if ESP32 is within WiFi range
- Try disabling static IP (set `USE_STATIC_IP false`)

### Upload fails
- Ensure GPIO 0 is connected to GND
- Press RESET when "Connecting..." appears
- Try a different USB cable
- Check COM port selection

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/status` | GET | Device status JSON |
| `/heartbeat` | GET | Keep-alive signal |
| `/lcd` | POST | Display message `{"line1":"...", "line2":"..."}` |
| `/lcd/clear` | GET | Clear LCD |
| `/buzzer/success` | GET | Play success tone |
| `/buzzer/error` | GET | Play error tone |
| `/buzzer/late` | GET | Play late arrival tone |
| `/capture` | GET | Single JPEG frame |
| `:81/stream` | GET | MJPEG video stream |
