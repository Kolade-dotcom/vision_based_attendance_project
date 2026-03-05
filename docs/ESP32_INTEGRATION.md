# ESP32-CAM Integration Guide

This document explains how the ESP32-CAM integrates with the Vision Attendance System to provide:
- Live video streaming for face recognition
- LCD display for showing recognized names
- Active buzzer for audio feedback (on/off patterns)
- LED for connection status indication

---

## Table of Contents

1. [Hardware Wiring](#1-hardware-wiring)
2. [Software Flow](#2-software-flow)
3. [Video Streaming](#3-video-streaming)
4. [Recognition Integration](#4-recognition-integration)
5. [LED States](#5-led-states)
6. [Configuration](#6-configuration)

---

## 1. Hardware Wiring

### ESP32-CAM Pinout

```
                    ESP32-CAM Board
                   ┌─────────────────┐
                   │    [CAMERA]     │
                   │                 │
            3.3V ──┤ 3V3         5V  ├── 5V (from USB programmer)
             GND ──┤ GND        GND  ├── GND
                   │                 │
   LCD SDA ────────┤ GPIO 14    IO0  ├── (Boot button - don't use)
   LCD SCL ────────┤ GPIO 15    IO2  ├── (Internal LED - reserved)
   Buzzer+ ────────┤ GPIO 12    IO4  ├── (Flash LED - reserved)
   LED+ ───────────┤ GPIO 13   IO16  ├── (PSRAM - don't use)
                   │                 │
                   │    [SD CARD]    │
                   └─────────────────┘
```

### Component Wiring Details

#### 16x2 LCD with I2C Backpack

```
LCD I2C Module          ESP32-CAM
┌──────────────┐       ┌──────────┐
│ VCC  ────────┼───────┤ 5V       │
│ GND  ────────┼───────┤ GND      │
│ SDA  ────────┼───────┤ GPIO 14  │
│ SCL  ────────┼───────┤ GPIO 15  │
└──────────────┘       └──────────┘
```

**Notes:**
- LCD VCC requires 5V for proper operation
- I2C logic works fine at 3.3V level from ESP32
- Default I2C address is usually `0x27` or `0x3F`

#### Active Buzzer

```
Buzzer                  ESP32-CAM
┌──────────────┐       ┌──────────┐
│ (+) Positive ┼───────┤ GPIO 12  │
│ (-) Negative ┼───────┤ GND      │
└──────────────┘       └──────────┘
```

**Notes:**
- Use an **active** buzzer (has built-in oscillator)
- Active buzzers beep when power is applied
- Usually has a sticker with voltage rating (3.3V or 5V)
- The firmware uses timing patterns (not frequencies) for different sounds

#### Connection Status LED

```
LED                     ESP32-CAM
┌──────────────┐       ┌──────────┐
│ (+) Anode    ┼──[220Ω]──┤ GPIO 13  │
│ (-) Cathode  ┼───────┤ GND      │
└──────────────┘       └──────────┘
```

**Notes:**
- Always use a current-limiting resistor (220Ω - 330Ω)
- LED indicates connection status to Python server
- Any color LED works (green recommended)

### Complete Wiring Diagram

```
                                    ┌─────────────────┐
                                    │   ESP32-CAM     │
                                    │                 │
┌─────────────────┐                 │                 │
│  16x2 LCD I2C   │                 │                 │
│  ┌───────────┐  │    ┌────────────┤ GPIO 14 (SDA)   │
│  │           │  │    │            │                 │
│  │  Hello!   │  │    │  ┌─────────┤ GPIO 15 (SCL)   │
│  │  John Doe │  │    │  │         │                 │
│  │           │  │    │  │    ┌────┤ GPIO 12         │
│  └───────────┘  │    │  │    │    │                 │
│   VCC GND SDA SCL    │  │    │ ┌──┤ GPIO 13         │
│    │   │   │   │     │  │    │ │  │                 │
└────┼───┼───┼───┼─────┘  │    │ │  │                 │
     │   │   │   │        │    │ │  │    5V ──────────┼─────┐
     │   │   │   └────────┘    │ │  │                 │     │
     │   │   └─────────────────┘ │  │   GND ──────────┼──┐  │
     │   │                       │  │                 │  │  │
     │   │  ┌────────────────────┘  │                 │  │  │
     │   │  │  ┌────────────────────┘                 │  │  │
     │   │  │  │                    └─────────────────┘  │  │
     │   │  │  │                                         │  │
     │   │  │  │    ┌───────────┐                        │  │
     │   │  │  │    │ ACTIVE    │                        │  │
     │   │  │  │    │ BUZZER    │                        │  │
     │   │  │  │    │ (+) (-)   │                        │  │
     │   │  │  │    └────┬───┬────┘                       │  │
     │   │  │  │        │   │                            │  │
     │   │  │  └────────┘   │                            │  │
     │   │  │               │                            │  │
     │   │  │    ┌──────────┼────────────────────────────┘  │
     │   │  │    │          │                               │
     │   │  │    │   ┌──────┴──────┐                        │
     │   │  │    │   │    LED     │                        │
     │   │  │    │   │ (+)   (-) │                        │
     │   │  │    │   └──┬─────┬──┘                        │
     │   │  │    │      │     │                            │
     │   │  └────┼──[220Ω]────┘                            │
     │   │       │      │                                  │
     │   └───────┼──────┴──────────────────────────────────┘
     │           │
     └───────────┘
```

### GPIO Pin Summary

| Component | GPIO Pin | Direction | Notes |
|-----------|----------|-----------|-------|
| LCD SDA | GPIO 14 | Bidirectional | I2C Data |
| LCD SCL | GPIO 15 | Output | I2C Clock |
| Buzzer | GPIO 12 | Output | Digital on/off (active buzzer) |
| LED | GPIO 13 | Output | Status indicator |

### Pins to Avoid on ESP32-CAM

| Pin | Reason |
|-----|--------|
| GPIO 0 | Boot mode selection |
| GPIO 2 | Connected to internal LED |
| GPIO 4 | Flash LED control |
| GPIO 16 | PSRAM (if present) |
| GPIO 1, 3 | Serial TX/RX |

---

## 2. Software Flow

### Startup Sequence

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STARTUP SEQUENCE                            │
└─────────────────────────────────────────────────────────────────────┘

  ESP32-CAM                              Python Server
  ─────────                              ─────────────
      │                                       │
      │ 1. Power on                           │
      │    Initialize hardware                │
      │    LED: OFF                           │
      │                                       │
      │ 2. Connect to WiFi                    │
      │    LED: SLOW BLINK (1s interval)      │
      │    Retry until connected...           │
      │                                       │
      │ 3. WiFi connected!                    │
      │    Start HTTP server (port 80)        │
      │    Start MJPEG stream (port 81)       │
      │    LED: FAST BLINK (200ms interval)   │
      │                                       │
      │    Waiting for Python server...       │
      │                                       │
      │                                       │ 4. User starts attendance
      │                                       │    session on dashboard
      │                                       │
      │◄──────── GET /status ─────────────────│ 5. Python checks if
      │                                       │    ESP32 is online
      │                                       │
      │────────── { "status": "ok" } ─────────►│ 6. ESP32 responds
      │                                       │
      │◄──────── GET /heartbeat ──────────────│ 7. Python sends heartbeat
      │                                       │    (every 5 seconds)
      │                                       │
      │ 8. LED: SOLID ON                      │
      │    (Connected to server!)             │
      │                                       │
      │◄════════ Heartbeat loop ══════════════│ Continues every 5s
      │                                       │
```

### Recognition Event Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FACE RECOGNITION EVENT                         │
└─────────────────────────────────────────────────────────────────────┘

  ESP32-CAM                              Python Server
  ─────────                              ─────────────
      │                                       │
      │ ═══════ MJPEG Video Stream ══════════►│ 1. Continuous video
      │         (port 81, /stream)            │    frames sent to Python
      │                                       │
      │                                       │ 2. Python processes frame:
      │                                       │    - Detect faces (HOG)
      │                                       │    - Extract face encoding
      │                                       │    - Compare with database
      │                                       │
      │                                       │ 3. MATCH FOUND!
      │                                       │    Student: "John Doe"
      │                                       │    ID: "STU001"
      │                                       │
      │                                       │ 4. Record attendance in
      │                                       │    SQLite database
      │                                       │
      │◄─── POST /lcd ────────────────────────│ 5. Send LCD command
      │     {                                 │
      │       "line1": "Welcome!",            │
      │       "line2": "John Doe"             │
      │     }                                 │
      │                                       │
      │ 6. LCD displays message               │
      │    ┌────────────────┐                 │
      │    │ Welcome!       │                 │
      │    │ John Doe       │                 │
      │    └────────────────┘                 │
      │                                       │
      │◄─── GET /buzzer/success ──────────────│ 7. Send buzzer command
      │                                       │
      │ 8. Buzzer plays success tone          │
      │    (ascending beeps)                  │
      │                                       │
      │ 9. LED flashes briefly                │
      │    (visual confirmation)              │
      │                                       │
      │────────── { "status": "ok" } ─────────►│ 10. Acknowledge
      │                                       │
```

### Error/Unknown Face Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      UNKNOWN FACE EVENT                             │
└─────────────────────────────────────────────────────────────────────┘

  ESP32-CAM                              Python Server
  ─────────                              ─────────────
      │                                       │
      │ ═══════ MJPEG Video Stream ══════════►│
      │                                       │
      │                                       │ Face detected but
      │                                       │ NO MATCH in database
      │                                       │
      │◄─── POST /lcd ────────────────────────│ (Optional - configurable)
      │     {                                 │
      │       "line1": "Not Recognized",      │
      │       "line2": "Please register"      │
      │     }                                 │
      │                                       │
      │◄─── GET /buzzer/error ────────────────│
      │                                       │
      │ Buzzer plays error tone               │
      │ (low beep)                            │
      │                                       │
```

### Late Arrival Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LATE ARRIVAL EVENT                             │
└─────────────────────────────────────────────────────────────────────┘

  ESP32-CAM                              Python Server
  ─────────                              ─────────────
      │                                       │
      │                                       │ Session started at 9:00 AM
      │                                       │ Grace period: 15 minutes
      │                                       │
      │                                       │ Current time: 9:20 AM
      │                                       │ Student "Jane Smith" detected
      │                                       │
      │                                       │ → Mark as LATE (not present)
      │                                       │
      │◄─── POST /lcd ────────────────────────│
      │     {                                 │
      │       "line1": "Late Arrival",        │
      │       "line2": "Jane Smith"           │
      │     }                                 │
      │                                       │
      │◄─── GET /buzzer/success ──────────────│ Still success tone
      │                                       │ (attendance recorded)
      │                                       │
```

---

## 3. Video Streaming

### How MJPEG Streaming Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MJPEG STREAMING PROTOCOL                         │
└─────────────────────────────────────────────────────────────────────┘

ESP32-CAM captures frames from OV2640 camera sensor
                    │
                    ▼
            ┌───────────────┐
            │ JPEG Encode   │  Each frame compressed to JPEG
            │ (Hardware)    │  ~10-50KB per frame
            └───────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ HTTP Response │  Multipart response with boundary
            │ (Port 81)     │
            └───────────────┘
                    │
                    ▼
    HTTP Response (continuous stream):
    ─────────────────────────────────
    HTTP/1.1 200 OK
    Content-Type: multipart/x-mixed-replace; boundary=frame

    --frame
    Content-Type: image/jpeg
    Content-Length: 12345

    [JPEG BINARY DATA FOR FRAME 1]

    --frame
    Content-Type: image/jpeg
    Content-Length: 12456

    [JPEG BINARY DATA FOR FRAME 2]

    --frame
    ...continues indefinitely...
```

### ESP32-CAM HTTP Endpoints

| Port | Endpoint | Method | Description |
|------|----------|--------|-------------|
| 80 | `/status` | GET | Health check, returns device info |
| 80 | `/capture` | GET | Single JPEG frame snapshot |
| 80 | `/lcd` | POST | Display message on LCD |
| 80 | `/lcd/clear` | GET | Clear LCD display |
| 80 | `/buzzer/success` | GET | Play success tone |
| 80 | `/buzzer/error` | GET | Play error tone |
| 80 | `/heartbeat` | GET | Keep connection LED solid |
| 81 | `/stream` | GET | MJPEG video stream |

### Python Consuming the Stream

```python
# How Python reads the ESP32-CAM stream
import cv2

# OpenCV can directly read MJPEG streams!
stream_url = "http://192.168.1.100:81/stream"
cap = cv2.VideoCapture(stream_url)

while True:
    ret, frame = cap.read()  # Returns decoded BGR numpy array
    if ret:
        # Process frame with face_recognition
        faces = detect_faces(frame)
        # ... rest of recognition logic
```

### Stream Resolution Options

The ESP32-CAM firmware can be configured for different resolutions:

| Resolution | Size | FPS | Use Case |
|------------|------|-----|----------|
| QQVGA | 160x120 | 25+ | Testing only |
| QVGA | 320x240 | 20+ | Fast, low accuracy |
| CIF | 400x296 | 15+ | Balanced |
| VGA | 640x480 | 10-12 | **Recommended** |
| SVGA | 800x600 | 8-10 | Higher accuracy |
| XGA | 1024x768 | 5-7 | Maximum quality |

**Recommended: VGA (640x480)** - Good balance of face recognition accuracy and frame rate.

---

## 4. Recognition Integration

### Where Recognition Happens

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RECOGNITION PIPELINE                            │
└─────────────────────────────────────────────────────────────────────┘

                         Python Server (app.py)
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │ ESP32Camera │───►│ FaceDetector│───►│ face_recognition.       │ │
│  │ (stream)    │    │ (HOG model) │    │ compare_faces()         │ │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘ │
│         │                  │                       │               │
│         │                  │                       ▼               │
│         │                  │           ┌─────────────────────────┐ │
│         │                  │           │ Database Lookup         │ │
│         │                  │           │ - Load student encodings│ │
│         │                  │           │ - Find best match       │ │
│         │                  │           │ - Record attendance     │ │
│         │                  │           └─────────────────────────┘ │
│         │                  │                       │               │
│         │                  │                       ▼               │
│         │                  │           ┌─────────────────────────┐ │
│         │                  │           │ ESP32Bridge             │ │
│         │                  │           │ - signal_success(name)  │ │
│         │                  │           │ - signal_late(name)     │ │
│         │                  │           │ - signal_error()        │ │
│         │                  │           └─────────────────────────┘ │
│         │                  │                       │               │
└─────────┼──────────────────┼───────────────────────┼───────────────┘
          │                  │                       │
          │ Video frames     │ Face locations        │ HTTP commands
          │                  │                       │
          ▼                  ▼                       ▼
    ┌───────────────────────────────────────────────────────────────┐
    │                        ESP32-CAM                              │
    │  Camera ──────────────────────────────► LCD / Buzzer / LED    │
    └───────────────────────────────────────────────────────────────┘
```

### Code Flow in app.py (gen_frames function)

```python
def gen_frames(user_id):
    # 1. Initialize camera (ESP32 stream or local webcam)
    camera = get_camera()  # Returns ESP32Camera or Camera based on config
    
    # 2. Initialize ESP32 bridge for hardware control
    esp32 = ESP32Bridge(esp32_ip="192.168.1.100", simulation=False)
    esp32.connect()
    
    # 3. Load known faces from database (once per session)
    known_encodings, known_names, known_ids = load_student_encodings()
    
    while True:
        # 4. Get frame from ESP32-CAM stream
        frame = camera.get_frame()
        
        # 5. Detect faces using HOG model
        faces = detector.detect(frame)
        
        # 6. For each detected face, try to recognize
        for face_location in faces:
            encoding = face_recognition.face_encodings(frame, [face_location])
            
            # 7. Compare against known faces
            matches = face_recognition.compare_faces(known_encodings, encoding)
            
            if True in matches:
                # 8. Found a match!
                name = known_names[best_match_index]
                student_id = known_ids[best_match_index]
                
                # 9. Record attendance in database
                result = db_helper.record_attendance(student_id, 'present')
                
                if result:  # New attendance (not duplicate)
                    # 10. Signal ESP32 hardware!
                    if result['status'] == 'late':
                        esp32.signal_late(name)
                    else:
                        esp32.signal_success(name)
        
        # 11. Yield frame for web display
        yield encode_frame(frame)
```

### Timing and Debouncing

To avoid repeatedly signaling the same person:

```python
# In db_helper.record_attendance():
# - Only records if student hasn't been recorded in current session
# - Returns None if already recorded (duplicate detection)

# This means:
# - First detection: Records attendance, signals ESP32
# - Subsequent detections: No action (already recorded)
```

---

## 5. LED States

### LED Behavior Summary

| State | LED Pattern | Meaning |
|-------|-------------|---------|
| **OFF** | Solid OFF | ESP32 not powered / initializing |
| **SLOW BLINK** | 1s ON, 1s OFF | Connecting to WiFi |
| **FAST BLINK** | 200ms ON, 200ms OFF | WiFi connected, waiting for server |
| **SOLID ON** | Continuous ON | Connected to Python server |
| **BRIEF FLASH** | Quick OFF then ON | Recognition event occurred |

### LED State Diagram

```
                    ┌─────────────────┐
                    │   POWER ON      │
                    │   LED: OFF      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ CONNECTING WIFI │◄────────┐
                    │ LED: SLOW BLINK │         │
                    │ (1s interval)   │         │ WiFi lost
                    └────────┬────────┘         │
                             │                  │
                             │ WiFi connected   │
                             ▼                  │
                    ┌─────────────────┐         │
                    │ WAITING SERVER  │─────────┘
                    │ LED: FAST BLINK │
                    │ (200ms interval)│◄────────┐
                    └────────┬────────┘         │
                             │                  │
                             │ Heartbeat        │ Heartbeat
                             │ received         │ timeout (10s)
                             ▼                  │
                    ┌─────────────────┐         │
              ┌────►│ CONNECTED       │─────────┘
              │     │ LED: SOLID ON   │
              │     └────────┬────────┘
              │              │
              │              │ Recognition event
              │              ▼
              │     ┌─────────────────┐
              │     │ EVENT FLASH     │
              └─────│ LED: OFF 100ms  │
                    │ then back ON    │
                    └─────────────────┘
```

### Implementation in Arduino

```cpp
// LED States
enum LEDState {
    LED_OFF,
    LED_SLOW_BLINK,
    LED_FAST_BLINK,
    LED_SOLID,
    LED_FLASH
};

LEDState currentLEDState = LED_OFF;
unsigned long lastHeartbeat = 0;
const unsigned long HEARTBEAT_TIMEOUT = 10000;  // 10 seconds

void updateLED() {
    unsigned long now = millis();
    
    // Check heartbeat timeout
    if (currentLEDState == LED_SOLID && 
        now - lastHeartbeat > HEARTBEAT_TIMEOUT) {
        currentLEDState = LED_FAST_BLINK;  // Lost connection
    }
    
    switch (currentLEDState) {
        case LED_OFF:
            digitalWrite(LED_PIN, LOW);
            break;
            
        case LED_SLOW_BLINK:
            digitalWrite(LED_PIN, (now / 1000) % 2);  // 1s toggle
            break;
            
        case LED_FAST_BLINK:
            digitalWrite(LED_PIN, (now / 200) % 2);   // 200ms toggle
            break;
            
        case LED_SOLID:
            digitalWrite(LED_PIN, HIGH);
            break;
            
        case LED_FLASH:
            // Brief off then back to solid
            digitalWrite(LED_PIN, LOW);
            delay(100);
            digitalWrite(LED_PIN, HIGH);
            currentLEDState = LED_SOLID;
            break;
    }
}

// Called when /heartbeat endpoint is hit
void onHeartbeat() {
    lastHeartbeat = millis();
    currentLEDState = LED_SOLID;
}

// Called when recognition event occurs
void onRecognitionEvent() {
    currentLEDState = LED_FLASH;
}
```

---

## 6. Configuration

### Python Configuration (config.py or environment variables)

```python
# ESP32-CAM Configuration
ESP32_CAM_IP = "192.168.1.100"      # IP address of ESP32-CAM
ESP32_CAM_STREAM_PORT = 81           # MJPEG stream port
ESP32_CAM_CONTROL_PORT = 80          # HTTP control port

# Camera Source
CAMERA_SOURCE = "esp32"              # Options: "esp32", "webcam", "auto"
WEBCAM_INDEX = 0                     # Local webcam index (fallback)

# ESP32 Hardware Control
ESP32_SIMULATION = False             # True for development without hardware
HEARTBEAT_INTERVAL = 5               # Seconds between heartbeats

# Recognition Settings
FACE_RECOGNITION_TOLERANCE = 0.5     # Lower = stricter matching
LATE_THRESHOLD_MINUTES = 15          # Minutes after session start = late
```

### ESP32 Configuration (in Arduino code)

```cpp
// WiFi Configuration
const char* WIFI_SSID = "YourNetworkName";
const char* WIFI_PASSWORD = "YourPassword";

// Static IP Configuration
IPAddress staticIP(192, 168, 1, 100);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(8, 8, 8, 8);

// Hardware Pins
#define LCD_SDA_PIN 14
#define LCD_SCL_PIN 15
#define BUZZER_PIN 12
#define LED_PIN 13

// LCD I2C Address (try 0x27 or 0x3F)
#define LCD_ADDRESS 0x27

// Camera Settings
#define CAMERA_RESOLUTION FRAMESIZE_VGA  // 640x480
#define JPEG_QUALITY 12                   // 0-63 (lower = better quality)
```

### Network Setup Checklist

1. **Router Configuration:**
   - Reserve IP `192.168.1.100` for ESP32-CAM MAC address (optional but recommended)
   - Ensure devices are on same subnet

2. **Firewall:**
   - Allow incoming connections on ports 80 and 81
   - Python server must be able to reach ESP32 IP

3. **Testing Connection:**
   ```bash
   # From computer running Python:
   ping 192.168.1.100
   
   # Test stream in browser:
   # http://192.168.1.100:81/stream
   
   # Test control endpoint:
   curl http://192.168.1.100/status
   ```

---

## Quick Reference

### Communication Summary

| From | To | Protocol | Purpose |
|------|-----|----------|---------|
| ESP32-CAM | Python | HTTP (MJPEG) | Video stream |
| Python | ESP32-CAM | HTTP (REST) | LCD/Buzzer commands |
| Python | ESP32-CAM | HTTP (REST) | Heartbeat (connection keep-alive) |

### File Changes Required

| File | Changes |
|------|---------|
| `esp32_bridge.py` | Add heartbeat, LED control, merge camera+peripherals |
| `camera.py` | Add `ESP32Camera` class for stream consumption |
| `app.py` | Integrate ESP32 signals in recognition loop |
| `config.py` (new) | Centralized configuration |
| `esp32_cam_firmware/` (new) | Arduino code for ESP32-CAM |
