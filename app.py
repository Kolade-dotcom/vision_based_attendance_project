from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, Response, session, redirect
from flask import request as flask_request
from flask_socketio import SocketIO, emit
import logging
import os
import time
import db_helper
from api.routes.student_routes import student_bp
from api.routes.attendance_routes import attendance_bp
from api.routes.auth_routes import auth_bp
from api.routes.session_routes import session_bp
from api.routes.dashboard_routes import dashboard_bp
from api.routes.portal_routes import portal_bp
from api.routes.portal_api_routes import portal_api_bp
from api.routes.dashboard_api_routes import dashboard_api_bp
from api.controllers.auth_controller import login_required

# Camera/face recognition imports — only available when running locally
_HAS_CAMERA = False
try:
    import cv2
    import numpy as np
    import face_recognition
    from camera import get_camera, draw_face_boxes, FaceDetector
    from esp32_bridge import get_esp32_bridge
    from api.routes.face_capture_routes import face_capture_bp
    from api.controllers.face_capture_controller import get_user_capture_session
    _HAS_CAMERA = True
except ImportError:
    pass

# Import configuration
try:
    import config
except ImportError:
    config = None


# Initialize Flask app
logger = logging.getLogger(__name__)

app = Flask(__name__)

secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    logger.warning("SECRET_KEY not set! Using generated key. Sessions will not persist across restarts.")
    secret_key = os.urandom(24).hex()
app.config["SECRET_KEY"] = secret_key
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max request size

# Ensure database is initialized
db_helper.init_database()

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet", max_http_buffer_size=10 * 1024 * 1024)

# Register Blueprints
app.register_blueprint(student_bp, url_prefix="/api")
app.register_blueprint(attendance_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/api")
app.register_blueprint(session_bp, url_prefix="/api")
app.register_blueprint(dashboard_bp)
app.register_blueprint(portal_bp)
app.register_blueprint(portal_api_bp)
app.register_blueprint(dashboard_api_bp)

from api.routes.worker_routes import worker_bp
app.register_blueprint(worker_bp)

if _HAS_CAMERA:
    app.register_blueprint(face_capture_bp, url_prefix="/api")


@app.route("/")
def root():
    """Redirect root to dashboard."""
    return redirect("/dashboard/")


@app.route("/api/health")
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "message": "Attendance system modular API is running",
        }
    )


def gen_frames(user_id):
    """Video streaming generator function with face recognition and ESP32 integration."""
    # Get camera and ESP32 bridge instances
    camera = get_camera()
    esp32 = get_esp32_bridge()

    # Connect to ESP32 and start heartbeat
    if esp32.connect():
        esp32.start_heartbeat()
        esp32.show_ready()

    # Tuned for responsiveness (skip_frames=1) and stability (smoothing_window=5)
    detector = FaceDetector(
        model=config.FACE_DETECTION_MODEL if config else "hog",
        scale=config.FACE_DETECTION_SCALE if config else 0.5,
        skip_frames=config.FACE_DETECTION_SKIP_FRAMES if config else 1,
        smoothing_window=5,
    )

    # Load known faces from DB once per stream connection
    known_face_encodings = []
    known_face_names = []
    known_student_ids = []

    try:
        students = db_helper.get_all_student_encodings()
        for student in students:
            if student["face_encoding"]:
                try:
                    # Deserialize bytes to numpy array
                    encoding = np.frombuffer(student["face_encoding"], dtype=np.float64)
                    known_face_encodings.append(encoding)
                    known_face_names.append(student["name"])
                    known_student_ids.append(student["student_id"])
                except Exception as e:
                    logger.error(f"Error loading encoding for {student['student_id']}: {e}")
    except Exception as e:
        logger.error(f"Error fetching student encodings: {e}")

    logger.debug(f"Loaded {len(known_face_encodings)} face encodings for recognition.")
    logger.debug(f"Known students: {known_student_ids}")

    # Ensure camera is started
    camera.start()

    while True:
        frame = camera.get_frame()
        if frame is None:
            break

        # Flip frame horizontally for mirror effect if it's a webcam
        # (ESP32-CAM usually doesn't need mirror unless specified)
        if hasattr(camera, "camera_index"):
            frame = cv2.flip(frame, 1)

        # Detect faces using advanced HOG-based detector with tracking
        faces = detector.detect(frame)

        # Debug: log face detection (only occasionally to avoid spam)
        if detector.frame_count % 30 == 0:  # Log every 30 frames
            logger.debug(f"Frame {detector.frame_count}: Detected {len(faces)} face(s)")

        # Recognition
        face_names = []
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Get active session for this user to mark attendance
        active_session = db_helper.get_active_session(user_id)

        if not active_session:
            logger.debug(f"No active session found for user_id={user_id}")
        elif not known_face_encodings:
            logger.debug("No known face encodings loaded")

        if active_session and known_face_encodings:
            face_locations_for_rec = []
            for x, y, w, h in faces:
                # Convert (x, y, w, h) to (top, right, bottom, left) format
                rec_loc = (y, x + w, y + h, x)
                face_locations_for_rec.append(rec_loc)

            if face_locations_for_rec and detector.frame_count % 30 == 0:
                logger.debug(f"Processing {len(face_locations_for_rec)} face(s) for recognition")
                logger.debug(f"Face boxes (x,y,w,h): {faces}")
                logger.debug(f"Converted to (top,right,bottom,left): {face_locations_for_rec}")

            face_encodings = face_recognition.face_encodings(
                rgb_frame, face_locations_for_rec
            )

            logger.debug(f"Generated {len(face_encodings)} face encoding(s)")

            for face_encoding in face_encodings:
                tolerance = config.FACE_RECOGNITION_TOLERANCE if config else 0.5
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

                        logger.debug(
                            f"Match found at index {best_match_index}: {name} ({student_id}) distance: {face_distances[best_match_index]:.4f}"
                        )
                        result = db_helper.record_attendance(
                            student_id,
                            status="present",
                            course_code=active_session["course_code"],
                        )

                        # Signal ESP32 on successful recognition (not duplicate)
                        if result:
                            logger.info(f"Attendance recorded for {name} ({student_id})")
                            if result.get("status") == "late":
                                esp32.signal_late(name, student_id)
                            else:
                                esp32.signal_success(name, student_id)
                else:
                    # Optional: Signal unknown face
                    if config and config.ESP32_SIGNAL_UNKNOWN:
                        esp32.signal_error("Unknown Person")

                # Append formatted name (with ID) for visual feedback
                display_name = name
                if student_id:
                    display_name = f"{name} ({student_id})"
                face_names.append(display_name)

        # Draw boxes and names
        for (x, y, w, h), name in zip(
            faces, face_names if active_session else [""] * len(faces)
        ):
            color = (0, 255, 0) if name and name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            if name:
                cv2.putText(
                    frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1
                )

        # If no recognition (no session), just draw boxes (fallback)
        if not active_session:
            frame = draw_face_boxes(frame, faces)

        # Encode frame
        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

    # Cleanup when stream ends
    esp32.stop_heartbeat()


@app.route("/video_feed")
@login_required
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    user_id = session.get("user_id")
    return Response(
        gen_frames(user_id), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# ============================================================================
# Enrollment Face Capture Video Feed
# ============================================================================


def gen_enrollment_frames(capture_session):
    """Video streaming generator with guided face capture overlay."""
    camera = get_camera()

    # Ensure camera is started
    camera.start()

    while True:
        frame = camera.get_frame()
        if frame is None:
            # Camera might not be ready yet, yield placeholder or retry
            time.sleep(0.1)
            continue

        # Flip frame horizontally for mirror effect if it's a webcam
        if hasattr(camera, "camera_index"):
            frame = cv2.flip(frame, 1)

        # Process frame with guided capture
        annotated_frame, status = capture_session.process_frame(frame)

        # Add instruction overlay
        instruction = status.get("instruction", "")
        feedback = status.get("feedback", "")
        progress = status.get("progress", "0/21")

        # Draw semi-transparent overlay at top
        overlay = annotated_frame.copy()
        cv2.rectangle(overlay, (0, 0), (annotated_frame.shape[1], 80), (0, 0, 0), -1)
        annotated_frame = cv2.addWeighted(overlay, 0.5, annotated_frame, 0.5, 0)

        # Draw text
        cv2.putText(
            annotated_frame,
            instruction,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            annotated_frame,
            feedback,
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            1,
        )
        cv2.putText(
            annotated_frame,
            f"Progress: {progress}",
            (10, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )

        # Encode frame
        ret, buffer = cv2.imencode(".jpg", annotated_frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

        # Stop if capture is complete
        if status.get("is_complete"):
            camera.stop()
            break


@app.route("/enrollment_video_feed")
@login_required
def enrollment_video_feed():
    """Video streaming route for enrollment with guided face capture."""
    # Get capture session BEFORE entering generator (to access Flask session context)
    capture_session = get_user_capture_session()
    return Response(
        gen_enrollment_frames(capture_session),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ============================================================================
# Worker WebSocket Events
# ============================================================================

WORKER_API_KEY = os.environ.get("WORKER_API_KEY", "dev-worker-key")
_worker_sid = None


@socketio.on("worker:auth")
def handle_worker_auth(data):
    global _worker_sid
    if data.get("api_key") == WORKER_API_KEY:
        _worker_sid = flask_request.sid
        emit("worker:auth_ok")
        logger.info("Worker connected and authenticated")
    else:
        emit("worker:auth_fail", {"error": "Invalid API key"})
        logger.warning("Worker auth failed")


@socketio.on("worker:frame")
def handle_worker_frame(data):
    """Relay JPEG frame from worker to all dashboard browsers."""
    emit("camera:frame", data, broadcast=True, include_self=False)


@socketio.on("worker:attendance")
def handle_worker_attendance(data):
    """Worker reports a recognized student."""
    try:
        result = db_helper.record_attendance(
            student_id=data["student_id"],
            status=data.get("status", "present"),
            course_code=data.get("course_code"),
        )
        if result:
            emit("attendance:new", result, broadcast=True, include_self=False)
    except Exception as e:
        logger.error(f"Worker attendance error: {e}")


@socketio.on("worker:status")
def handle_worker_status(data):
    """Relay worker status to all dashboard browsers."""
    emit("worker:status", data, broadcast=True, include_self=False)


@socketio.on("disconnect")
def handle_disconnect():
    global _worker_sid
    if flask_request.sid == _worker_sid:
        _worker_sid = None
        emit("worker:status", {"status": "offline"}, broadcast=True)
        logger.info("Worker disconnected")


def notify_worker(event, data):
    """Send a command to the connected worker."""
    global _worker_sid
    if _worker_sid:
        socketio.emit(event, data, to=_worker_sid)
        return True
    return False


# --- Face processing relay (cloud → worker → cloud) ---
import threading

_face_processing_result = {}
_face_processing_event = threading.Event()


@socketio.on("worker:faces_processed")
def handle_faces_processed(data):
    """Worker sends back processed face encoding."""
    _face_processing_result.clear()
    _face_processing_result.update(data)
    _face_processing_event.set()
    logger.info("Received face processing result from worker")


def relay_face_processing(frames):
    """Send frames to worker for processing and wait for result."""
    global _worker_sid
    if not _worker_sid:
        return None

    _face_processing_event.clear()
    _face_processing_result.clear()

    socketio.emit("worker:process_faces", {"frames": frames}, to=_worker_sid)

    if not _face_processing_event.wait(timeout=120):
        return {"status": "timeout"}

    return dict(_face_processing_result)


if __name__ == "__main__":
    import sys

    # Default to HTTP (works for desktop)
    # Use --ssl flag for HTTPS (needed for mobile camera access)
    use_ssl = "--ssl" in sys.argv

    cert_file = "cert.pem"
    key_file = "key.pem"

    if use_ssl:
        if os.path.exists(cert_file) and os.path.exists(key_file):
            logger.info("Starting with HTTPS (SSL enabled)")
            logger.info("Mobile camera access will work")
            logger.info(
                "You may need to accept the self-signed certificate warning in your browser"
            )
            socketio.run(
                app, debug=True, host="0.0.0.0", port=5000, ssl_context=(cert_file, key_file)
            )
        else:
            logger.error("SSL requested but certificate files not found!")
            logger.info(
                "Generate certificates: openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365"
            )
            sys.exit(1)
    else:
        logger.info("Starting with HTTP (use --ssl for HTTPS)")
        logger.info("For mobile camera access, use ngrok: ngrok http 5000")
        socketio.run(app, debug=True, host="0.0.0.0", port=5000)
