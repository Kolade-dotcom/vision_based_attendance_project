from flask import Flask, render_template, jsonify, Response, session
import cv2
import logging
import os
import time
import db_helper
from api.routes.student_routes import student_bp
from api.routes.attendance_routes import attendance_bp
from api.routes.auth_routes import auth_bp
from api.routes.session_routes import session_bp
from api.routes.face_capture_routes import face_capture_bp
from api.routes.enrollment_link_routes import enrollment_link_bp
from api.routes.public_enrollment_routes import public_enrollment_bp
from api.controllers.auth_controller import login_required
from api.controllers.face_capture_controller import get_user_capture_session
from camera import get_camera, draw_face_boxes, FaceDetector
from esp32_bridge import get_esp32_bridge
import face_recognition
import numpy as np

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

# Register Blueprints
app.register_blueprint(student_bp, url_prefix="/api")
app.register_blueprint(attendance_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/api")
app.register_blueprint(session_bp, url_prefix="/api")
app.register_blueprint(face_capture_bp, url_prefix="/api")
app.register_blueprint(enrollment_link_bp, url_prefix="/api")
app.register_blueprint(public_enrollment_bp, url_prefix="/api")


@app.route("/")
@login_required
def index():
    """Render the main dashboard page."""
    return render_template("index.html")


@app.route("/enroll")
@login_required
def enroll():
    """Render the enrollment page for new students."""
    return render_template("enroll.html")


@app.route("/login")
def login():
    """Render the login page."""
    return render_template("login.html")


@app.route("/enroll/<token>")
def public_enroll(token):
    """Public enrollment page for students (token-validated, no login required)."""
    return render_template("public_enroll.html", token=token)


@app.route("/enrollment-success")
def enrollment_success():
    """Confirmation page after student submits enrollment."""
    return render_template("enrollment_success.html")


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
            app.run(
                debug=True, host="0.0.0.0", port=5000, ssl_context=(cert_file, key_file)
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
        app.run(debug=True, host="0.0.0.0", port=5000)
