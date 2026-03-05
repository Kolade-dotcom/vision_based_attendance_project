"""
Configuration Module for Vision Attendance System

Centralized configuration for ESP32-CAM integration and system settings.
"""

import os
from typing import Literal


# =============================================================================
# ESP32-CAM CONFIGURATION
# =============================================================================

# ESP32-CAM Network Settings
ESP32_CAM_IP: str = os.environ.get("ESP32_CAM_IP", "192.168.1.100")
ESP32_CAM_CONTROL_PORT: int = int(os.environ.get("ESP32_CAM_CONTROL_PORT", "80"))
ESP32_CAM_STREAM_PORT: int = int(os.environ.get("ESP32_CAM_STREAM_PORT", "81"))

# Computed URLs
ESP32_CAM_BASE_URL: str = f"http://{ESP32_CAM_IP}:{ESP32_CAM_CONTROL_PORT}"
ESP32_CAM_STREAM_URL: str = f"http://{ESP32_CAM_IP}:{ESP32_CAM_STREAM_PORT}/stream"
ESP32_CAM_SNAPSHOT_URL: str = f"http://{ESP32_CAM_IP}:{ESP32_CAM_CONTROL_PORT}/capture"


# =============================================================================
# CAMERA SOURCE CONFIGURATION
# =============================================================================

# Camera source options:
# - "esp32": Use ESP32-CAM stream
# - "webcam": Use local webcam
# - "auto": Try ESP32-CAM first, fallback to webcam
CameraSource = Literal["esp32", "webcam", "auto"]
CAMERA_SOURCE: CameraSource = os.environ.get("CAMERA_SOURCE", "auto")  # type: ignore

# Local webcam index (used when CAMERA_SOURCE is "webcam" or "auto" fallback)
WEBCAM_INDEX: int = int(os.environ.get("WEBCAM_INDEX", "0"))


# =============================================================================
# ESP32 HARDWARE CONTROL
# =============================================================================

# Enable/disable hardware simulation mode
# When True: ESP32Bridge logs commands but doesn't send HTTP requests
# When False: ESP32Bridge sends real HTTP requests to ESP32
ESP32_SIMULATION: bool = os.environ.get("ESP32_SIMULATION", "true").lower() == "true"

# Heartbeat interval in seconds (keeps ESP32 LED solid)
ESP32_HEARTBEAT_INTERVAL: int = int(os.environ.get("ESP32_HEARTBEAT_INTERVAL", "5"))

# HTTP request timeout for ESP32 commands
ESP32_TIMEOUT: int = int(os.environ.get("ESP32_TIMEOUT", "5"))

# Enable/disable ESP32 feedback (LCD, buzzer) on recognition
ESP32_FEEDBACK_ENABLED: bool = os.environ.get("ESP32_FEEDBACK_ENABLED", "true").lower() == "true"

# Signal unknown faces (play error tone and show "Not Recognized")
ESP32_SIGNAL_UNKNOWN: bool = os.environ.get("ESP32_SIGNAL_UNKNOWN", "false").lower() == "true"


# =============================================================================
# FACE RECOGNITION SETTINGS
# =============================================================================

# Face recognition tolerance (0.0 - 1.0)
# Lower = stricter matching, Higher = more lenient
# Default 0.5 is a good balance
FACE_RECOGNITION_TOLERANCE: float = float(os.environ.get("FACE_RECOGNITION_TOLERANCE", "0.5"))

# Detection model: "hog" (fast, CPU) or "cnn" (accurate, GPU)
FACE_DETECTION_MODEL: str = os.environ.get("FACE_DETECTION_MODEL", "hog")

# Frame processing scale (0.1 - 1.0)
# Lower = faster but less accurate
FACE_DETECTION_SCALE: float = float(os.environ.get("FACE_DETECTION_SCALE", "0.5"))

# Skip frames for detection optimization
# Higher = faster but may miss quick movements
FACE_DETECTION_SKIP_FRAMES: int = int(os.environ.get("FACE_DETECTION_SKIP_FRAMES", "1"))


# =============================================================================
# ATTENDANCE SETTINGS
# =============================================================================

# Late threshold in minutes
# Students arriving after this many minutes from session start are marked "late"
LATE_THRESHOLD_MINUTES: int = int(os.environ.get("LATE_THRESHOLD_MINUTES", "15"))

# Cooldown period in seconds before recognizing same person again
# Prevents duplicate LCD/buzzer signals for same person
RECOGNITION_COOLDOWN: int = int(os.environ.get("RECOGNITION_COOLDOWN", "5"))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_camera_config() -> dict:
    """Get camera configuration as a dictionary."""
    return {
        "source": CAMERA_SOURCE,
        "esp32_ip": ESP32_CAM_IP,
        "esp32_stream_url": ESP32_CAM_STREAM_URL,
        "webcam_index": WEBCAM_INDEX,
    }


def get_esp32_config() -> dict:
    """Get ESP32 configuration as a dictionary."""
    return {
        "ip": ESP32_CAM_IP,
        "control_port": ESP32_CAM_CONTROL_PORT,
        "stream_port": ESP32_CAM_STREAM_PORT,
        "base_url": ESP32_CAM_BASE_URL,
        "stream_url": ESP32_CAM_STREAM_URL,
        "simulation": ESP32_SIMULATION,
        "heartbeat_interval": ESP32_HEARTBEAT_INTERVAL,
        "timeout": ESP32_TIMEOUT,
        "feedback_enabled": ESP32_FEEDBACK_ENABLED,
    }


def print_config():
    """Print current configuration (useful for debugging)."""
    print("=" * 50)
    print("Vision Attendance System Configuration")
    print("=" * 50)
    print(f"Camera Source: {CAMERA_SOURCE}")
    print(f"ESP32-CAM IP: {ESP32_CAM_IP}")
    print(f"ESP32 Stream URL: {ESP32_CAM_STREAM_URL}")
    print(f"ESP32 Simulation: {ESP32_SIMULATION}")
    print(f"Webcam Index: {WEBCAM_INDEX}")
    print(f"Face Detection Model: {FACE_DETECTION_MODEL}")
    print(f"Recognition Tolerance: {FACE_RECOGNITION_TOLERANCE}")
    print(f"Late Threshold: {LATE_THRESHOLD_MINUTES} minutes")
    print("=" * 50)


if __name__ == "__main__":
    print_config()
