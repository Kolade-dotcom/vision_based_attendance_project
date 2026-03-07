"""
Local Worker Script
Connects to the cloud app via WebSocket.
Handles camera capture, face recognition, and ESP32 hardware.
Run this on your laptop alongside the ESP32-CAM.

Usage:
    SERVER_URL=https://your-app.onrender.com WORKER_API_KEY=your-key python worker.py
"""

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import time
import base64
import logging
import signal
import threading
import cv2
import numpy as np
import face_recognition
import socketio
import requests

from camera import get_camera, reset_camera, FaceDetector
from esp32_bridge import get_esp32_bridge, reset_esp32_bridge
from face_capture import GuidedFaceCapture

try:
    import config
except ImportError:
    config = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --- Configuration ---
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:5000")
WORKER_API_KEY = os.environ.get("WORKER_API_KEY", "dev-worker-key")
FRAME_RATE = int(os.environ.get("WORKER_FRAME_RATE", "5"))
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
JPEG_QUALITY = 70

# --- State ---
sio = socketio.Client(reconnection=True, reconnection_delay=2)
camera = None
esp32 = None
detector = None
known_face_encodings = []
known_face_names = []
known_student_ids = []
active_session = None
running = False
reported_students = set()  # Track students already reported this session


def load_face_encodings():
    """Fetch enrolled student face encodings from cloud API."""
    global known_face_encodings, known_face_names, known_student_ids
    known_face_encodings = []
    known_face_names = []
    known_student_ids = []

    try:
        resp = requests.get(
            f"{SERVER_URL}/api/worker/faces",
            headers={"X-Worker-Key": WORKER_API_KEY},
            timeout=30,
        )
        resp.raise_for_status()
        students = resp.json()

        for s in students:
            encoding_bytes = base64.b64decode(s["face_encoding"])
            encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
            known_face_encodings.append(encoding)
            known_face_names.append(s["name"])
            known_student_ids.append(s["student_id"])

        logger.info(f"Loaded {len(known_face_encodings)} face encodings from server")
    except Exception as e:
        logger.error(f"Failed to load face encodings: {e}")


def fetch_camera_settings(user_id):
    """Fetch camera settings from the cloud API for this user."""
    try:
        resp = requests.get(
            f"{SERVER_URL}/api/worker/settings/{user_id}",
            headers={"X-Worker-Key": WORKER_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch camera settings: {e}, using defaults")
        return {"camera_source": "auto", "esp32_ip": "192.168.1.100"}


def start_capture(camera_source="auto", esp32_ip=None):
    """Start camera capture and face recognition loop."""
    global camera, detector, esp32, running

    reset_esp32_bridge()

    logger.info(f"Starting capture with source={camera_source}, esp32_ip={esp32_ip}")
    # Reuse pre-warmed camera if available, otherwise create new
    if camera is None or not (hasattr(camera, 'video_capture') and camera.video_capture is not None):
        reset_camera()
        camera = get_camera(source=camera_source, esp32_ip=esp32_ip)
        camera.start()
    else:
        logger.info("Reusing pre-warmed camera")

    esp32 = get_esp32_bridge(esp32_ip=esp32_ip)
    if esp32.connect():
        esp32.start_heartbeat()
        esp32.show_ready()

    detector = FaceDetector(
        model=config.FACE_DETECTION_MODEL if config else "hog",
        scale=config.FACE_DETECTION_SCALE if config else 0.5,
        skip_frames=config.FACE_DETECTION_SKIP_FRAMES if config else 1,
        smoothing_window=5,
    )

    running = True
    frame_interval = 1.0 / FRAME_RATE
    last_frame_time = 0

    # Low-light detection state (debounced)
    _last_low_light_state = None
    _MIN_BRIGHTNESS = GuidedFaceCapture.MIN_BRIGHTNESS  # 40
    _MAX_BRIGHTNESS = GuidedFaceCapture.MAX_BRIGHTNESS  # 220

    # Report actual camera source to dashboard
    from camera import _camera_source as actual_source
    sio.emit("worker:status", {"status": "capturing", "camera_source": actual_source or camera_source})
    logger.info(f"Capture started (actual source: {actual_source or camera_source})")

    while running:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        # Mirror webcam
        if hasattr(camera, "camera_index"):
            frame = cv2.flip(frame, 1)

        # Brightness check (debounced — only emit on state change)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        is_low_light = mean_brightness < _MIN_BRIGHTNESS
        is_too_bright = mean_brightness > _MAX_BRIGHTNESS

        if is_low_light or is_too_bright:
            if _last_low_light_state != "bad":
                msg = "Too dark - move to a brighter area" if is_low_light else "Too bright - reduce lighting"
                sio.emit("camera:low_light", {"is_low": True, "message": msg})
                _last_low_light_state = "bad"
            # Overlay warning on frame
            cv2.putText(
                frame,
                "LOW LIGHT" if is_low_light else "TOO BRIGHT",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                2,
            )
        else:
            if _last_low_light_state != "ok":
                sio.emit("camera:low_light", {"is_low": False, "message": ""})
                _last_low_light_state = "ok"

        # Face detection
        faces = detector.detect(frame)

        # Face recognition (only if session active and faces loaded)
        face_names = []
        if active_session and known_face_encodings and faces:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations_for_rec = []
            for x, y, w, h in faces:
                face_locations_for_rec.append((y, x + w, y + h, x))

            face_encodings = face_recognition.face_encodings(
                rgb_frame, face_locations_for_rec
            )

            tolerance = config.FACE_RECOGNITION_TOLERANCE if config else 0.5
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(
                    known_face_encodings, face_encoding, tolerance=tolerance
                )

                name = "Unknown"
                student_id = None

                if True in matches:
                    face_distances = face_recognition.face_distance(
                        known_face_encodings, face_encoding
                    )
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
                        student_id = known_student_ids[best_match_index]

                        # Report attendance to cloud (only once per student per session)
                        if student_id not in reported_students:
                            reported_students.add(student_id)
                            sio.emit(
                                "worker:attendance",
                                {
                                    "student_id": student_id,
                                    "status": "present",
                                    "course_code": active_session.get("course_code"),
                                },
                            )
                            logger.info(f"Recognized: {name} ({student_id})")

                        # ESP32 feedback (always, so student gets confirmation)
                        esp32.signal_success(name, student_id)
                else:
                    if config and config.ESP32_SIGNAL_UNKNOWN:
                        esp32.signal_error("Unknown Person")

                display_name = name
                if student_id:
                    display_name = f"{name} ({student_id})"
                face_names.append(display_name)

        # Draw face boxes on frame
        for i, (x, y, w, h) in enumerate(faces):
            label = face_names[i] if i < len(face_names) else ""
            color = (0, 255, 0) if label and "Unknown" not in label else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            if label:
                cv2.putText(
                    frame,
                    label,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                )

        # Stream frame to cloud at target FPS
        now = time.time()
        if now - last_frame_time >= frame_interval:
            small = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            _, jpeg = cv2.imencode(
                ".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            )
            frame_b64 = base64.b64encode(jpeg.tobytes()).decode("ascii")
            sio.emit("worker:frame", {"frame": frame_b64})
            last_frame_time = now

    # Cleanup
    if camera:
        camera.stop()
    if esp32:
        esp32.stop_heartbeat()
    sio.emit("worker:status", {"status": "idle"})
    logger.info("Capture stopped")


def stop_capture():
    """Stop the capture loop."""
    global running
    running = False


def _prewarm_camera():
    """Open webcam immediately so first frame is fast when session starts.

    Uses webcam directly (not "auto") to avoid a 10-second ESP32 timeout
    that blocks the worker. The actual session will use the user's configured
    source, but webcam pre-warm ensures fast startup for the common case.
    """
    global camera
    try:
        camera = get_camera(source="webcam")
        camera.start()
        logger.info("Camera pre-warmed successfully (webcam)")
    except Exception as e:
        logger.warning(f"Camera pre-warm failed (will retry on session start): {e}")


# --- SocketIO event handlers ---


@sio.on("worker:auth_ok")
def on_auth_ok():
    logger.info("Authenticated with server")
    sio.emit("worker:status", {"status": "idle"})
    # Pre-warm camera so it's ready when session starts
    _prewarm_camera()


@sio.on("worker:auth_fail")
def on_auth_fail(data):
    logger.error(f"Authentication failed: {data.get('error')}")
    sio.disconnect()


@sio.on("worker:process_faces")
def on_process_faces(data):
    """Process face frames for enrollment (relayed from cloud)."""
    frames = data.get("frames", [])
    logger.info(f"Received face processing request ({len(frames)} frames)")
    if frames:
        sample = frames[0]
        logger.info(f"  Frame 0: type={type(sample).__name__}, len={len(sample) if isinstance(sample, str) else 'N/A'}, prefix={str(sample)[:80]}...")
    try:
        from face_processor import process_multiple_face_images

        result = process_multiple_face_images(frames)
        sio.emit("worker:faces_processed", result)
        logger.info(f"Face processing complete: {result.get('status')}, {result.get('image_count', 0)} images")
    except Exception as e:
        logger.error(f"Face processing error: {e}", exc_info=True)
        sio.emit("worker:faces_processed", {"status": "error", "error": str(e)})


@sio.on("session:start")
def on_session_start(data):
    global active_session
    logger.info(f"Session start command: {data}")
    active_session = data
    reported_students.clear()

    # Load face encodings in background (don't block camera start)
    threading.Thread(target=load_face_encodings, daemon=True).start()

    # Fetch user's camera settings, then start capture
    user_id = data.get("user_id")
    settings = fetch_camera_settings(user_id) if user_id else {}
    camera_source = settings.get("camera_source", "auto")
    esp32_ip = settings.get("esp32_ip")

    t = threading.Thread(
        target=start_capture,
        args=(camera_source, esp32_ip),
        daemon=True,
    )
    t.start()


@sio.on("session:end")
def on_session_end(data):
    global active_session
    logger.info(f"Session end command: {data}")
    active_session = None
    reported_students.clear()
    stop_capture()


@sio.on("connect")
def on_connect():
    logger.info(f"Connected to {SERVER_URL}")
    sio.emit("worker:auth", {"api_key": WORKER_API_KEY})


@sio.on("disconnect")
def on_disconnect():
    global active_session
    logger.warning("Disconnected from server")
    active_session = None
    stop_capture()


# --- Main ---


def main():
    logger.info(f"Worker starting — connecting to {SERVER_URL}")

    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        stop_capture()
        sio.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        sio.connect(SERVER_URL, transports=["websocket"])
        sio.wait()
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
