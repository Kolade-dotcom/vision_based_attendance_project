# Cloud Hosting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Host the attendance app on Render with Neon PostgreSQL, using a local worker script for face recognition and ESP32 hardware, connected via WebSocket.

**Architecture:** Cloud Flask app with Flask-SocketIO relays session commands and camera frames between the dashboard and a local worker. The worker handles all camera/face-recognition/ESP32 logic. PostgreSQL replaces SQLite in production, with SQLite fallback for local dev.

**Tech Stack:** Flask-SocketIO, eventlet, psycopg2-binary, python-socketio[client], Neon PostgreSQL, Render, gunicorn

---

## Task 1: Add PostgreSQL support to db_helper.py (dual-mode connection layer)

**Files:**
- Modify: `db_helper.py:1-52` (imports, connection, init)
- Create: `database/schema_postgres.sql`

**Step 1: Create PostgreSQL schema file**

Create `database/schema_postgres.sql` — same as `schema.sql` but with PostgreSQL syntax:

```sql
-- PostgreSQL schema for Vision Attendance System

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    courses TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    level TEXT,
    courses TEXT,
    face_encoding BYTEA,
    password_hash TEXT,
    is_enrolled INTEGER DEFAULT 0,
    status TEXT DEFAULT 'approved' CHECK(status IN ('pending', 'approved', 'rejected')),
    enrolled_via_link_id INTEGER,
    created_by INTEGER,
    rejection_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (enrolled_via_link_id) REFERENCES enrollment_links(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);

CREATE TABLE IF NOT EXISTS enrollment_links (
    id SERIAL PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    created_by INTEGER NOT NULL,
    course_code TEXT,
    level TEXT,
    description TEXT,
    max_uses INTEGER DEFAULT NULL,
    current_uses INTEGER DEFAULT 0,
    expires_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_enrollment_links_token ON enrollment_links(token);
CREATE INDEX IF NOT EXISTS idx_enrollment_links_created_by ON enrollment_links(created_by);

CREATE TABLE IF NOT EXISTS class_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    course_code TEXT NOT NULL,
    scheduled_start TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_active ON class_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_course ON class_sessions(course_code);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON class_sessions(user_id);

CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    student_id TEXT NOT NULL,
    session_id INTEGER,
    timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'present' CHECK(status IN ('present', 'late', 'absent')),
    course_code TEXT,
    level TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES class_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp);
CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance(session_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT
);

INSERT INTO settings (key, value, updated_at) VALUES
    ('late_threshold_minutes', '15', NOW()::TEXT),
    ('session_start_time', '09:00', NOW()::TEXT),
    ('session_end_time', '17:00', NOW()::TEXT)
ON CONFLICT (key) DO NOTHING;
```

Note: `enrollment_links` must be created BEFORE `students` due to foreign key dependency. Reorder if needed.

**Step 2: Update db_helper.py connection layer**

Replace the top of `db_helper.py` (lines 1-52) with a dual-mode connection layer:

```python
"""
Database Helper Module
Handles all database operations for the attendance system.
Supports PostgreSQL (production via DATABASE_URL) and SQLite (local fallback).
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
import json
import secrets

logger = logging.getLogger(__name__)

try:
    import config
except ImportError:
    config = None

# --- Database mode detection ---
DATABASE_URL = os.environ.get("DATABASE_URL")
_USE_POSTGRES = DATABASE_URL is not None

if _USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    logger.info("Using PostgreSQL database")
else:
    logger.info("Using SQLite database (local mode)")

# SQLite fallback path
_DEFAULT_DATABASE_PATH = os.path.join(os.path.dirname(__file__), "database", "attendance.db")
if os.environ.get("DATABASE_PATH"):
    _DATABASE_PATH = os.environ["DATABASE_PATH"]
else:
    _DATABASE_PATH = _DEFAULT_DATABASE_PATH


def get_database_path():
    """Get the current database path (SQLite only)."""
    return _DATABASE_PATH


def set_database_path(path):
    """Set the database path. Used for test isolation (SQLite only)."""
    global _DATABASE_PATH
    _DATABASE_PATH = path


class DictRow(dict):
    """Make dict subscriptable like sqlite3.Row for compatibility."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


@contextmanager
def get_db_connection():
    """Context manager for database connection. Works with both PostgreSQL and SQLite."""
    if _USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(_DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def _placeholder():
    """Return the SQL placeholder for the current database mode."""
    return "%s" if _USE_POSTGRES else "?"
```

**Step 3: Update all SQL placeholders**

All queries in `db_helper.py` use `?` for SQLite. For PostgreSQL, it needs `%s`.

Add this helper and apply it in `get_db_connection` or create a query wrapper:

```python
def _q(sql):
    """Convert SQLite-style ? placeholders to %s for PostgreSQL."""
    if _USE_POSTGRES:
        return sql.replace("?", "%s")
    return sql
```

Then wrap every `cursor.execute(query, params)` call to use `_q(query)`:
- `cursor.execute("SELECT ... WHERE id = ?", (id,))` becomes
- `cursor.execute(_q("SELECT ... WHERE id = ?"), (id,))`

This is a search-and-replace across the entire file. Key patterns:
- `conn.execute("...?...", ...)` → `conn.execute(_q("...?..."), ...)`
- `cursor.execute("...?...", ...)` → `cursor.execute(_q("...?..."), ...)`

**Step 4: Update init_database() for PostgreSQL**

Replace the SQLite-specific `init_database()` with a dual-mode version:

```python
def init_database():
    """Initialize the database with schema and run migrations."""
    if _USE_POSTGRES:
        _init_postgres()
    else:
        _init_sqlite()


def _init_postgres():
    """Initialize PostgreSQL schema."""
    schema_path = os.path.join(os.path.dirname(__file__), "database", "schema_postgres.sql")
    with open(schema_path, "r") as f:
        schema = f.read()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(schema)
        conn.commit()
    logger.info("PostgreSQL database initialized successfully!")


def _init_sqlite():
    """Initialize SQLite schema with migrations."""
    # ... (keep existing init_database() code here, renamed to _init_sqlite)
```

**Step 5: Handle SQLite-specific patterns**

These SQLite patterns need PostgreSQL alternatives:
- `cursor.lastrowid` → use `RETURNING id` clause: `INSERT ... RETURNING id`
- `conn.executescript(sql)` → `cursor.execute(sql)` (PostgreSQL handles multi-statement)
- `"SELECT name FROM sqlite_master WHERE type='table'"` → `"SELECT tablename FROM pg_tables WHERE schemaname = 'public'"`
- `"PRAGMA table_info(table)"` → skip migrations in PostgreSQL (schema_postgres.sql has everything)
- `datetime('now')` in SQL → `NOW()` or pass Python `datetime.now().isoformat()`

For `cursor.lastrowid`, update `create_session()`:
```python
if _USE_POSTGRES:
    cursor.execute(_q("""
        INSERT INTO class_sessions (user_id, course_code, scheduled_start, start_time, is_active)
        VALUES (?, ?, ?, ?, 1) RETURNING id
    """), (user_id, course_code, start_time, start_time))
    return cursor.fetchone()["id"]
else:
    cursor.execute("""
        INSERT INTO class_sessions (user_id, course_code, scheduled_start, start_time, is_active)
        VALUES (?, ?, ?, ?, 1)
    """, (user_id, course_code, start_time, start_time))
    conn.commit()
    return cursor.lastrowid
```

Apply the same pattern to all `INSERT` statements that use `lastrowid`:
- `create_session()` (line ~159)
- `create_user()` (line ~215)
- `add_student()` (line ~411)
- `create_enrollment_link()` (line ~830 area)
- Any other INSERT that returns an ID

**Step 6: Handle BLOB vs BYTEA for face_encoding**

SQLite stores face_encoding as BLOB (bytes). PostgreSQL uses BYTEA.
- `psycopg2` handles `bytes` → `BYTEA` automatically.
- When reading, `psycopg2` returns `memoryview` for BYTEA — need `bytes()`:

```python
# In get_all_student_encodings() and anywhere face_encoding is read:
encoding_data = row["face_encoding"]
if isinstance(encoding_data, memoryview):
    encoding_data = bytes(encoding_data)
```

**Step 7: Run and verify locally (SQLite mode)**

Run: `source venv/Scripts/activate && python -c "import db_helper; db_helper.init_database(); print('OK')"`
Expected: `OK` (SQLite still works)

**Step 8: Commit**

```bash
git add db_helper.py database/schema_postgres.sql
git commit -m "feat: add PostgreSQL support with SQLite fallback"
```

---

## Task 2: Add Flask-SocketIO to the cloud app

**Files:**
- Modify: `app.py` (add SocketIO init, worker namespace)
- Modify: `requirements.txt` (add dependencies)
- Create: `api/routes/worker_routes.py` (worker API endpoints)

**Step 1: Update requirements.txt**

Add cloud and worker dependencies. Create two files:

`requirements.txt` (cloud — no dlib/face_recognition/opencv):
```
# Core Framework
flask==3.0.0
flask-socketio>=5.3.0
eventlet>=0.36.0
gunicorn>=21.2.0

# Database
psycopg2-binary>=2.9.0

# Utilities
requests>=2.31.0
python-dotenv>=1.0.0
qrcode[pil]>=7.4.0

# Security
werkzeug>=3.0.0

# Development & Testing
pytest>=7.4.0
```

Create `requirements-worker.txt` (local worker — needs everything):
```
# Worker dependencies (run locally)
python-socketio[client]>=5.10.0
requests>=2.31.0

# Computer Vision
opencv-python>=4.10.0
numpy>=2.1.0

# Face Recognition
face_recognition==1.3.0
dlib==19.24.99
setuptools<81

# Hardware
python-dotenv>=1.0.0
```

**Step 2: Add SocketIO to app.py**

At the top of `app.py`, after Flask app creation:

```python
from flask_socketio import SocketIO, emit

# ... existing app setup ...

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
```

Add worker authentication and SocketIO events at the bottom (before `if __name__`):

```python
# ============================================================================
# Worker WebSocket Events
# ============================================================================

WORKER_API_KEY = os.environ.get("WORKER_API_KEY", "dev-worker-key")
_worker_sid = None  # Track connected worker


def is_valid_worker_key(key):
    return key == WORKER_API_KEY


@socketio.on("worker:auth")
def handle_worker_auth(data):
    global _worker_sid
    if is_valid_worker_key(data.get("api_key")):
        _worker_sid = request.sid
        emit("worker:auth_ok")
        logger.info("Worker connected and authenticated")
    else:
        emit("worker:auth_fail", {"error": "Invalid API key"})
        logger.warning("Worker auth failed")


@socketio.on("worker:frame")
def handle_worker_frame(data):
    """Worker sends a JPEG frame — relay to all dashboard browsers."""
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
    """Worker sends status update (camera ready, error, etc)."""
    emit("worker:status", data, broadcast=True, include_self=False)


@socketio.on("disconnect")
def handle_disconnect():
    global _worker_sid
    if request.sid == _worker_sid:
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
```

**Step 3: Update session_controller.py to notify worker**

Modify `api/controllers/session_controller.py`:

```python
from flask import jsonify, request, session as flask_session
import db_helper

def start_session_logic():
    try:
        user_id = flask_session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json()
        course_code = data.get('course_code')

        if not course_code:
            return jsonify({'error': 'Missing course_code'}), 400

        session_id = db_helper.create_session(course_code, user_id)

        # Notify worker to start camera (instead of local camera start)
        from app import notify_worker
        worker_notified = notify_worker("session:start", {
            "session_id": session_id,
            "course_code": course_code,
            "user_id": user_id,
        })

        return jsonify({
            'message': 'Session started',
            'session_id': session_id,
            'course_code': course_code,
            'status': 'active',
            'worker_connected': worker_notified,
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def end_session_logic():
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400

        success = db_helper.end_session(session_id)
        if success:
            # Notify worker to stop camera
            from app import notify_worker
            notify_worker("session:end", {"session_id": session_id})
            return jsonify({'message': 'Session ended', 'status': 'inactive'}), 200
        else:
            return jsonify({'error': 'Session not found or already inactive'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

Keep `get_active_session_logic`, `get_history_logic`, `export_session_logic`, `delete_session_logic`, `get_session_attendance_logic` unchanged.

**Step 4: Add worker faces endpoint**

Create `api/routes/worker_routes.py`:

```python
from flask import Blueprint, jsonify, request
import db_helper
import base64
import os

worker_bp = Blueprint("worker", __name__, url_prefix="/api/worker")

WORKER_API_KEY = os.environ.get("WORKER_API_KEY", "dev-worker-key")


def _check_worker_key():
    key = request.headers.get("X-Worker-Key")
    if key != WORKER_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    return None


@worker_bp.route("/faces")
def get_faces():
    """Return all enrolled student face encodings for the worker."""
    auth_err = _check_worker_key()
    if auth_err:
        return auth_err

    students = db_helper.get_all_student_encodings()
    result = []
    for s in students:
        if s["face_encoding"]:
            encoding_data = s["face_encoding"]
            if isinstance(encoding_data, memoryview):
                encoding_data = bytes(encoding_data)
            result.append({
                "student_id": s["student_id"],
                "name": s["name"],
                "face_encoding": base64.b64encode(encoding_data).decode("ascii"),
            })
    return jsonify(result)
```

Register in `app.py`:
```python
from api.routes.worker_routes import worker_bp
app.register_blueprint(worker_bp)
```

**Step 5: Update app.py `__main__` to use socketio.run**

```python
if __name__ == "__main__":
    import sys
    use_ssl = "--ssl" in sys.argv
    # ... existing SSL logic ...
    else:
        logger.info("Starting with HTTP (use --ssl for HTTPS)")
        socketio.run(app, debug=True, host="0.0.0.0", port=5000)
```

Replace `app.run(...)` with `socketio.run(app, ...)` in both the SSL and non-SSL branches.

**Step 6: Verify app starts locally**

Run: `source venv/Scripts/activate && pip install flask-socketio eventlet && python -c "from app import app, socketio; print('OK')"`
Expected: `OK`

**Step 7: Commit**

```bash
git add app.py requirements.txt requirements-worker.txt api/routes/worker_routes.py api/controllers/session_controller.py
git commit -m "feat: add Flask-SocketIO and worker API endpoints"
```

---

## Task 3: Create the worker script

**Files:**
- Create: `worker.py`

**Step 1: Write worker.py**

```python
"""
Local Worker Script
Connects to the cloud app via WebSocket.
Handles camera capture, face recognition, and ESP32 hardware.
Run this on your laptop alongside the ESP32-CAM.
"""

import os
import sys
import time
import base64
import logging
import signal
import cv2
import numpy as np
import face_recognition
import socketio
import requests

# Local imports
from camera import get_camera, FaceDetector
from esp32_bridge import get_esp32_bridge

try:
    import config
except ImportError:
    config = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration ---
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:5000")
WORKER_API_KEY = os.environ.get("WORKER_API_KEY", "dev-worker-key")
FRAME_RATE = int(os.environ.get("WORKER_FRAME_RATE", "5"))  # FPS to send
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

        # Face recognition
        if active_session and known_face_encodings:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations_for_rec = []
            for x, y, w, h in faces:
                face_locations_for_rec.append((y, x + w, y + h, x))

            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations_for_rec)

            for face_encoding in face_encodings:
                tolerance = config.FACE_RECOGNITION_TOLERANCE if config else 0.5
                matches = face_recognition.compare_faces(
                    known_face_encodings, face_encoding, tolerance=tolerance
                )

                if True in matches:
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
                        student_id = known_student_ids[best_match_index]

                        # Report attendance to cloud
                        sio.emit("worker:attendance", {
                            "student_id": student_id,
                            "status": "present",
                            "course_code": active_session.get("course_code"),
                        })

                        # ESP32 feedback
                        esp32.signal_success(name, student_id)
                        logger.info(f"Recognized: {name} ({student_id})")

        # Draw face boxes
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Stream frame to cloud at target FPS
        now = time.time()
        if now - last_frame_time >= frame_interval:
            small = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            _, jpeg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
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

    import threading
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
    logger.info(f"Connecting to {SERVER_URL}...")

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
```

**Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('worker.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

**Step 3: Commit**

```bash
git add worker.py requirements-worker.txt
git commit -m "feat: add local worker script for camera and face recognition"
```

---

## Task 4: Update dashboard frontend for WebSocket camera feed

**Files:**
- Modify: `templates/dashboard/index.html` (replace img with canvas, add SocketIO)
- Modify: `static/js/dashboard/session.js` (SocketIO client, canvas rendering)
- Modify: `templates/dashboard/base.html` (add SocketIO client script)

**Step 1: Add SocketIO client to base template**

In `templates/dashboard/base.html`, add before closing `</body>`:

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.4/socket.io.min.js"></script>
```

**Step 2: Replace camera img with canvas in index.html**

Replace the camera feed section:

```html
<!-- Camera Feed -->
<section class="camera-card" aria-label="Camera feed">
  <div class="camera-aspect">
    <canvas
      id="camera-feed"
      style="display: none; position: absolute; inset: 0; width: 100%; height: 100%;"
    ></canvas>
    <div class="camera-empty" id="camera-empty">
      Start a session to activate the camera feed
    </div>
  </div>
</section>
```

Remove the old `<img src="" ...>` tag entirely.

**Step 3: Add worker status indicator to the session strip**

Add after the end session button in strip-active:

```html
<span class="worker-status" id="worker-status" title="Worker connection">
  <span class="worker-dot offline" id="worker-dot"></span>
</span>
```

Add CSS:

```css
.worker-status {
  display: inline-flex;
  align-items: center;
}

.worker-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: background-color 200ms;
}

.worker-dot.offline { background-color: var(--text-muted); }
.worker-dot.idle { background-color: var(--warning); }
.worker-dot.capturing { background-color: var(--brand); animation: pulse-dot 1.5s ease-in-out infinite; }
```

**Step 4: Update session.js for WebSocket**

Add SocketIO connection and canvas rendering to `session.js`:

At the top of the IIFE (after state):

```javascript
// --- SocketIO ---
var socket = typeof io !== "undefined" ? io() : null;

// Canvas feed rendering
function renderFrame(frameB64) {
  var canvas = dom.cameraFeed;
  if (!canvas || canvas.tagName !== "CANVAS") return;
  var ctx = canvas.getContext("2d");
  var img = new Image();
  img.onload = function () {
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);
  };
  img.src = "data:image/jpeg;base64," + frameB64;
}

if (socket) {
  socket.on("camera:frame", function (data) {
    if (state.activeSession) {
      renderFrame(data.frame);
    }
  });

  socket.on("worker:status", function (data) {
    var dot = document.getElementById("worker-dot");
    if (dot) {
      dot.className = "worker-dot " + (data.status || "offline");
    }
  });

  socket.on("attendance:new", function (data) {
    // Refresh attendance when worker reports new record
    loadAttendance();
    loadStats();
  });
}
```

Update `setSessionActive` — replace the img.src line with canvas show:

```javascript
// Camera — show canvas
dom.cameraFeed.style.display = "block";
dom.cameraEmpty.style.display = "none";
```

Remove the old `dom.cameraFeed.src = "/video_feed?" + Date.now();` line.

Update `setSessionInactive` — hide canvas:

```javascript
// Camera — hide canvas, clear it
dom.cameraFeed.style.display = "none";
dom.cameraEmpty.style.display = "flex";
var ctx = dom.cameraFeed.getContext && dom.cameraFeed.getContext("2d");
if (ctx) ctx.clearRect(0, 0, dom.cameraFeed.width, dom.cameraFeed.height);
```

Remove the old `dom.cameraFeed.src = "";` line.

**Step 5: Verify HTML/JS has no syntax errors**

Run: `node --check static/js/dashboard/session.js`
Expected: no output (success)

**Step 6: Commit**

```bash
git add templates/dashboard/index.html templates/dashboard/base.html static/js/dashboard/session.js
git commit -m "feat: replace MJPEG feed with WebSocket canvas streaming"
```

---

## Task 5: Deployment configuration

**Files:**
- Create: `render.yaml`
- Create: `Procfile`
- Create: `.env.example`

**Step 1: Create Procfile**

```
web: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
```

**Step 2: Create render.yaml**

```yaml
services:
  - type: web
    name: vision-attendance
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: SECRET_KEY
        generateValue: true
      - key: WORKER_API_KEY
        generateValue: true
      - key: PYTHON_VERSION
        value: 3.11.0
```

**Step 3: Create .env.example**

```bash
# Cloud app (Render)
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=your-secret-key
WORKER_API_KEY=your-worker-api-key

# Local worker
SERVER_URL=https://your-app.onrender.com
WORKER_API_KEY=same-key-as-above

# Hardware (worker only)
CAMERA_SOURCE=auto
ESP32_CAM_IP=192.168.1.100
ESP32_SIMULATION=true
```

**Step 4: Create .gitignore additions**

Add to `.gitignore`:
```
.env
*.db
venv/
__pycache__/
cert.pem
key.pem
```

**Step 5: Commit**

```bash
git add Procfile render.yaml .env.example .gitignore
git commit -m "feat: add Render deployment configuration"
```

---

## Task 6: Neon PostgreSQL setup and initial deploy

This task is manual (no code). Follow these steps:

**Step 1: Create Neon database**

1. Go to https://neon.tech and sign up (free)
2. Create a new project (any name, e.g., "vision-attendance")
3. Copy the connection string: `postgresql://user:pass@ep-xxx.region.neon.tech/neondb?sslmode=require`

**Step 2: Initialize the schema**

Run locally:
```bash
source venv/Scripts/activate
pip install psycopg2-binary
DATABASE_URL="your-neon-connection-string" python -c "import db_helper; db_helper.init_database(); print('Schema created!')"
```

**Step 3: Deploy to Render**

1. Push code to GitHub
2. Go to https://render.com, connect repo
3. Create new Web Service from repo
4. Set environment variables:
   - `DATABASE_URL` = Neon connection string
   - `SECRET_KEY` = (generate random string)
   - `WORKER_API_KEY` = (generate random string, save for worker too)
5. Deploy

**Step 4: Set up keep-alive**

1. Go to https://cron-job.org (free account)
2. Create job: URL = `https://your-app.onrender.com/api/health`, interval = every 14 minutes

**Step 5: Test the deployed app**

1. Visit `https://your-app.onrender.com/dashboard/`
2. Create account, log in
3. Verify pages load, courses show, no camera (expected — worker not connected)

**Step 6: Run the local worker**

```bash
source venv/Scripts/activate
pip install "python-socketio[client]"
SERVER_URL=https://your-app.onrender.com WORKER_API_KEY=your-key python worker.py
```

Expected: `Connected to https://your-app.onrender.com`, `Authenticated with server`

**Step 7: Test full flow**

1. Start a session on the cloud dashboard
2. Worker should log `Session start command: {...}`
3. Camera feed should appear on dashboard (via canvas)
4. Face recognition should work, attendance appears in real-time
5. End session — worker stops camera

---

## Task Order and Dependencies

```
Task 1 (DB migration) ──→ Task 2 (SocketIO + worker API) ──→ Task 3 (worker.py)
                                      │
                                      ├──→ Task 4 (dashboard frontend)
                                      │
                                      └──→ Task 5 (deploy config)
                                                    │
                                                    └──→ Task 6 (Neon + Render setup)
```

Tasks 3, 4, 5 can be done in parallel after Task 2.
Task 6 requires all others complete.
