"""
Local Worker Script
Connects to the cloud app via WebSocket.
Handles camera capture, face recognition, and ESP32 hardware.
Run this on your laptop alongside the ESP32-CAM.

Usage:
    SERVER_URL=https://your-app.onrender.com WORKER_API_KEY=your-key python worker.py
"""

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

from camera import get_camera, FaceDetector
from esp32_bridge import get_esp32_bridge

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


def start_capture():
    """Start camera capture and face recognition loop."""
    global camera, detector, esp32, running

    camera = get_camera()
    camera.start()

    esp32 = get_esp32_bridge()
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

    sio.emit("worker:status", {"status": "capturing"})
    logger.info("Capture started")

    while running:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        # Mirror webcam
        if hasattr(camera, "camera_index"):
            frame = cv2.flip(frame, 1)

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

                        # Report attendance to cloud
                        sio.emit(
                            "worker:attendance",
                            {
                                "student_id": student_id,
                                "status": "present",
                                "course_code": active_session.get("course_code"),
                            },
                        )

                        # ESP32 feedback
                        esp32.signal_success(name, student_id)
                        logger.info(f"Recognized: {name} ({student_id})")
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


# --- SocketIO event handlers ---


@sio.on("worker:auth_ok")
def on_auth_ok():
    logger.info("Authenticated with server")
    sio.emit("worker:status", {"status": "idle"})


@sio.on("worker:auth_fail")
def on_auth_fail(data):
    logger.error(f"Authentication failed: {data.get('error')}")
    sio.disconnect()


@sio.on("session:start")
def on_session_start(data):
    global active_session
    logger.info(f"Session start command: {data}")
    active_session = data
    load_face_encodings()

    t = threading.Thread(target=start_capture, daemon=True)
    t.start()


@sio.on("session:end")
def on_session_end(data):
    global active_session
    logger.info(f"Session end command: {data}")
    active_session = None
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
