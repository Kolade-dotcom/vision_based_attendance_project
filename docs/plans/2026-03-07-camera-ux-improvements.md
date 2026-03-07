# Camera UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 3 UX issues: add low-light warnings, speed up camera startup on worker, and fix attendance marking speed + enrollment flexibility.

**Architecture:** Backend changes in worker.py, app.py, db_helper.py for brightness detection, pre-warm camera, and flexible enrollment. Frontend changes in session.js and dashboard HTML for loading states, warnings, and approve/dismiss UI. Database migration adds `equivalent_courses` and updates attendance status CHECK constraint.

**Tech Stack:** Python/Flask, SocketIO, OpenCV, vanilla JS, SQLite/PostgreSQL

---

### Task 1: Database Migration — Add `equivalent_courses` Column and Update Attendance Status

**Files:**
- Modify: `database/schema.sql:61-71` (class_sessions table)
- Modify: `database/schema_postgres.sql:58-69` (class_sessions table)
- Modify: `database/schema.sql:84` (attendance status CHECK)
- Modify: `database/schema_postgres.sql` (attendance status CHECK)
- Modify: `db_helper.py:92-116` (_init_sqlite migrations)

**Step 1: Update SQLite schema to add `equivalent_courses` column and `not_enrolled` status**

In `database/schema.sql`, update the `class_sessions` CREATE TABLE to add:
```sql
    equivalent_courses TEXT,        -- JSON array of equivalent course codes, e.g. '["MTE401","MEE301"]'
```
after line 68 (`is_active` column).

Update the attendance table CHECK constraint at line 84 from:
```sql
    status TEXT DEFAULT 'present' CHECK(status IN ('present', 'late', 'absent')),
```
to:
```sql
    status TEXT DEFAULT 'present' CHECK(status IN ('present', 'late', 'absent', 'not_enrolled')),
```

**Step 2: Update PostgreSQL schema identically**

Same changes in `database/schema_postgres.sql`.

**Step 3: Add SQLite migration in `db_helper.py:_init_sqlite()`**

After the existing `user_id` migration block (around line 116), add migration for `equivalent_courses`:
```python
            if "equivalent_courses" not in columns:
                conn.execute(
                    "ALTER TABLE class_sessions ADD COLUMN equivalent_courses TEXT"
                )
                logger.info("Migration: Added equivalent_courses column to class_sessions")
```

Also add migration for the attendance `not_enrolled` status. Since SQLite can't ALTER CHECK constraints, we don't need to migrate existing rows — the CHECK is only enforced on schema creation, and existing DBs won't have it. New DBs get the updated schema. No migration needed for the CHECK.

**Step 4: Commit**

```bash
git add database/schema.sql database/schema_postgres.sql db_helper.py
git commit -m "feat: add equivalent_courses column and not_enrolled attendance status"
```

---

### Task 2: Update `db_helper.py` — Equivalent Courses + Non-enrolled Handling

**Files:**
- Modify: `db_helper.py:185-224` (create_session — accept equivalent_courses param)
- Modify: `db_helper.py:639-774` (record_attendance — check equivalent courses, use not_enrolled status)
- Modify: `db_helper.py:250-260` (get_active_session — return equivalent_courses)

**Step 1: Update `create_session()` to accept and store `equivalent_courses`**

In `db_helper.py`, modify `create_session()` (starts at line 185):

Change the function signature from:
```python
def create_session(course_code, user_id):
```
to:
```python
def create_session(course_code, user_id, equivalent_courses=None):
```

Update the INSERT statements (both Postgres and SQLite) to include `equivalent_courses`:
```python
        equiv_json = json.dumps(equivalent_courses) if equivalent_courses else None

        if _USE_POSTGRES:
            cursor.execute(
                _q("""
                INSERT INTO class_sessions (user_id, course_code, scheduled_start, start_time, is_active, equivalent_courses)
                VALUES (?, ?, ?, ?, 1, ?) RETURNING id
                """),
                (user_id, course_code, start_time, start_time, equiv_json),
            )
            # ... rest unchanged
        else:
            cursor.execute(
                """
                INSERT INTO class_sessions (user_id, course_code, scheduled_start, start_time, is_active, equivalent_courses)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (user_id, course_code, start_time, start_time, equiv_json),
            )
            # ... rest unchanged
```

**Step 2: Update `record_attendance()` enrollment check**

In `db_helper.py:record_attendance()`, replace lines 701-713 (the enrollment check block):

```python
        # Check if student is enrolled in this course (or equivalent courses)
        is_enrolled = True
        if course_code and student["courses"]:
            try:
                enrolled_courses = json.loads(student["courses"])
                # Build set of accepted courses: session course + equivalents
                accepted_courses = {course_code}
                if session_id:
                    cursor.execute(
                        _q("SELECT equivalent_courses FROM class_sessions WHERE id = ?"),
                        (session_id,),
                    )
                    session_row_eq = cursor.fetchone()
                    if session_row_eq and session_row_eq["equivalent_courses"]:
                        try:
                            equiv = json.loads(session_row_eq["equivalent_courses"])
                            accepted_courses.update(equiv)
                        except (json.JSONDecodeError, TypeError):
                            pass

                if not any(c in accepted_courses for c in enrolled_courses):
                    is_enrolled = False
                    logger.info(
                        f"Student {student_id} not enrolled in {course_code} or equivalents {accepted_courses}. "
                        f"Courses: {enrolled_courses}. Recording as not_enrolled."
                    )
                    status = "not_enrolled"
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid courses JSON for student {student_id}")
```

**Step 3: Update `get_active_session()` to return `equivalent_courses`**

This should already work since it does `SELECT *`, but verify the dict includes `equivalent_courses`. No code change needed if using `SELECT *`.

**Step 4: Add `update_attendance_status()` and `delete_attendance()` helper functions**

Add after `record_attendance()` (around line 775):

```python
def update_attendance_status(attendance_id, new_status):
    """Update the status of an attendance record (e.g., approve not_enrolled -> present)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("UPDATE attendance SET status = ? WHERE id = ?"),
            (new_status, attendance_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_attendance(attendance_id):
    """Delete an attendance record (e.g., dismiss not_enrolled student)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("DELETE FROM attendance WHERE id = ?"),
            (attendance_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
```

**Step 5: Commit**

```bash
git add db_helper.py
git commit -m "feat: support equivalent courses and not_enrolled attendance status"
```

---

### Task 3: API Endpoints — Equivalent Courses, Approve/Dismiss

**Files:**
- Modify: `api/controllers/session_controller.py:4-31` (pass equivalent_courses on start)
- Modify: `api/routes/attendance_routes.py` (add PATCH and DELETE routes)
- Modify: `api/controllers/attendance_controller.py` (add approve/dismiss logic)

**Step 1: Update `start_session_logic()` to accept equivalent_courses**

In `api/controllers/session_controller.py`, update `start_session_logic()`:

```python
def start_session_logic():
    try:
        user_id = flask_session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json()
        course_code = data.get('course_code')

        if not course_code:
            return jsonify({'error': 'Missing course_code'}), 400

        # Parse optional equivalent courses
        equivalent_courses = data.get('equivalent_courses')
        if equivalent_courses and isinstance(equivalent_courses, str):
            # Accept comma-separated string from frontend
            equivalent_courses = [c.strip().upper() for c in equivalent_courses.split(',') if c.strip()]
        if not equivalent_courses:
            equivalent_courses = None

        session_id = db_helper.create_session(course_code, user_id, equivalent_courses=equivalent_courses)

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
```

**Step 2: Add approve/dismiss controller functions**

In `api/controllers/attendance_controller.py`, add:

```python
def approve_attendance_logic(attendance_id):
    """Approve a not_enrolled attendance record (change to present)."""
    try:
        user_id = flask_session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        success = db_helper.update_attendance_status(attendance_id, 'present')
        if success:
            return jsonify({'message': 'Attendance approved'}), 200
        return jsonify({'error': 'Record not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def dismiss_attendance_logic(attendance_id):
    """Dismiss (delete) a not_enrolled attendance record."""
    try:
        user_id = flask_session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        success = db_helper.delete_attendance(attendance_id)
        if success:
            return jsonify({'message': 'Attendance dismissed'}), 200
        return jsonify({'error': 'Record not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Step 3: Add routes**

In `api/routes/attendance_routes.py`:

```python
from api.controllers.attendance_controller import (
    get_attendance_logic, get_statistics_logic,
    approve_attendance_logic, dismiss_attendance_logic,
)

@attendance_bp.route('/attendance/<int:attendance_id>/approve', methods=['PATCH'])
def approve_attendance(attendance_id):
    return approve_attendance_logic(attendance_id)

@attendance_bp.route('/attendance/<int:attendance_id>', methods=['DELETE'])
def dismiss_attendance(attendance_id):
    return dismiss_attendance_logic(attendance_id)
```

**Step 4: Commit**

```bash
git add api/controllers/session_controller.py api/controllers/attendance_controller.py api/routes/attendance_routes.py
git commit -m "feat: add equivalent courses param and attendance approve/dismiss endpoints"
```

---

### Task 4: Low-light Detection in Worker

**Files:**
- Modify: `worker.py:136-226` (add brightness check in capture loop)

**Step 1: Add brightness analysis to `start_capture()` in worker.py**

Add imports at the top of worker.py (after existing imports around line 27):
```python
from face_capture import GuidedFaceCapture
```

Inside `start_capture()`, before the `while running:` loop (after line 127), add:
```python
    # Low-light detection state (debounced)
    _last_low_light_state = None
    MIN_BRIGHTNESS = GuidedFaceCapture.MIN_BRIGHTNESS  # 40
    MAX_BRIGHTNESS = GuidedFaceCapture.MAX_BRIGHTNESS  # 220
```

Inside the main loop, after getting the frame and before face detection (after line 144, the mirror webcam block), add:
```python
        # Brightness check (debounced — only emit on state change)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        is_low_light = mean_brightness < MIN_BRIGHTNESS
        is_too_bright = mean_brightness > MAX_BRIGHTNESS

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
```

**Step 2: Commit**

```bash
git add worker.py
git commit -m "feat: add low-light detection with debounced SocketIO warnings in worker"
```

---

### Task 5: Low-light Detection in `app.py:gen_frames()`

**Files:**
- Modify: `app.py` (the `gen_frames()` function — add brightness overlay)

**Step 1: Add brightness overlay to `gen_frames()`**

Find the `gen_frames()` function in `app.py`. After getting the frame and before face detection, add the same brightness check logic. Since `gen_frames()` is an HTTP streaming generator (not SocketIO-based), we only overlay text on the frame — no SocketIO emit needed (that's handled by the worker path).

```python
        # Brightness warning overlay
        gray_check = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if np.mean(gray_check) < 40:
            cv2.putText(frame, "LOW LIGHT - improve lighting", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        elif np.mean(gray_check) > 220:
            cv2.putText(frame, "TOO BRIGHT - reduce lighting", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
```

**Step 2: Commit**

```bash
git add app.py
git commit -m "feat: add low-light warning overlay in gen_frames()"
```

---

### Task 6: Pre-warm Camera in Worker

**Files:**
- Modify: `worker.py:277-295` (on_session_start) and `worker.py:104-134` (start_capture)
- Modify: `worker.py:306-309` (on_connect)

**Step 1: Pre-warm camera on worker auth success**

In `worker.py`, update `on_auth_ok()` (line 246-249) to pre-warm the camera:

```python
@sio.on("worker:auth_ok")
def on_auth_ok():
    logger.info("Authenticated with server")
    sio.emit("worker:status", {"status": "idle"})
    # Pre-warm camera so it's ready when session starts
    _prewarm_camera()


def _prewarm_camera():
    """Open camera immediately so first frame is fast when session starts."""
    global camera
    try:
        # Fetch settings for default user (will be overridden on session start if different)
        settings = fetch_camera_settings(None) if not active_session else {}
        camera_source = settings.get("camera_source", "auto")
        esp32_ip = settings.get("esp32_ip")
        camera = get_camera(source=camera_source, esp32_ip=esp32_ip)
        camera.start()
        logger.info("Camera pre-warmed successfully")
    except Exception as e:
        logger.warning(f"Camera pre-warm failed (will retry on session start): {e}")
```

**Step 2: Update `start_capture()` to reuse pre-warmed camera**

In `start_capture()`, change lines 108-113 from:
```python
    reset_camera()
    reset_esp32_bridge()

    logger.info(f"Starting capture with source={camera_source}, esp32_ip={esp32_ip}")
    camera = get_camera(source=camera_source, esp32_ip=esp32_ip)
    camera.start()
```
to:
```python
    reset_esp32_bridge()

    logger.info(f"Starting capture with source={camera_source}, esp32_ip={esp32_ip}")
    # Reuse pre-warmed camera if source matches, otherwise create new
    if camera is None or not (hasattr(camera, 'video_capture') and camera.video_capture is not None):
        reset_camera()
        camera = get_camera(source=camera_source, esp32_ip=esp32_ip)
        camera.start()
    else:
        logger.info("Reusing pre-warmed camera")
```

**Step 3: Commit**

```bash
git add worker.py
git commit -m "feat: pre-warm camera on worker connect for faster session start"
```

---

### Task 7: Frontend — Loading State + Camera Timeout

**Files:**
- Modify: `templates/dashboard/index.html:422-431` (add loading spinner markup)
- Modify: `static/js/dashboard/session.js:377-403` (setSessionActive — show loading, set timeout)
- Modify: `static/js/dashboard/session.js:65-70` (camera:frame handler — clear loading)

**Step 1: Add loading spinner HTML**

In `templates/dashboard/index.html`, after the canvas element (line 427) and before the camera-empty div (line 428), add:

```html
        <div class="camera-loading" id="camera-loading" style="display: none;">
          <div class="spinner"></div>
          <p>Connecting to camera...</p>
        </div>
```

Add CSS for the spinner (in the `<style>` section):
```css
.camera-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 0.95rem;
}
.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.camera-loading.error p {
  color: var(--danger, #ef4444);
}
```

**Step 2: Update JS — show loading on session start, clear on first frame**

In `static/js/dashboard/session.js`, add DOM ref:
```javascript
    cameraLoading: document.getElementById("camera-loading"),
```

Update `setSessionActive()` (line 377) — show loading instead of canvas initially:
```javascript
    // Camera — show loading state (canvas hidden until first frame)
    dom.cameraFeed.style.display = "none";
    dom.cameraLoading.style.display = "flex";
    dom.cameraEmpty.style.display = "none";

    // Timeout — if no frame in 10s, show error
    state.cameraTimeout = setTimeout(function () {
      if (dom.cameraLoading.style.display !== "none") {
        dom.cameraLoading.classList.add("error");
        dom.cameraLoading.querySelector("p").textContent =
          "Camera not responding. Check your worker connection.";
      }
    }, 10000);
```

Update the `camera:frame` handler (line 66) to clear loading on first frame:
```javascript
    socket.on("camera:frame", function (data) {
      if (state.activeSession) {
        // Hide loading, show canvas on first frame
        if (dom.cameraLoading && dom.cameraLoading.style.display !== "none") {
          dom.cameraLoading.style.display = "none";
          dom.cameraFeed.style.display = "block";
          if (state.cameraTimeout) {
            clearTimeout(state.cameraTimeout);
            state.cameraTimeout = null;
          }
        }
        renderFrame(data.frame);
      }
    });
```

Update `setSessionInactive()` to reset loading state:
```javascript
    dom.cameraLoading.style.display = "none";
    dom.cameraLoading.classList.remove("error");
    dom.cameraLoading.querySelector("p").textContent = "Connecting to camera...";
    if (state.cameraTimeout) {
      clearTimeout(state.cameraTimeout);
      state.cameraTimeout = null;
    }
```

**Step 3: Commit**

```bash
git add templates/dashboard/index.html static/js/dashboard/session.js
git commit -m "feat: add camera loading state with 10s timeout"
```

---

### Task 8: Frontend — Low-light Warning Banner

**Files:**
- Modify: `templates/dashboard/index.html` (add warning banner markup)
- Modify: `static/js/dashboard/session.js` (handle `camera:low_light` SocketIO event)

**Step 1: Add low-light warning HTML**

In `templates/dashboard/index.html`, inside the `.camera-aspect` div, add above the canvas:
```html
        <div class="camera-warning" id="camera-warning" style="display: none;">
          <span id="camera-warning-text">Low light detected - move to a brighter area</span>
        </div>
```

Add CSS:
```css
.camera-warning {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  padding: 8px 16px;
  background: rgba(239, 68, 68, 0.9);
  color: white;
  text-align: center;
  font-size: 0.85rem;
  font-weight: 500;
}
```

**Step 2: Handle SocketIO event in JS**

Add DOM ref:
```javascript
    cameraWarning: document.getElementById("camera-warning"),
    cameraWarningText: document.getElementById("camera-warning-text"),
```

Add SocketIO handler:
```javascript
    socket.on("camera:low_light", function (data) {
      if (dom.cameraWarning) {
        if (data.is_low) {
          dom.cameraWarningText.textContent = data.message || "Low light detected";
          dom.cameraWarning.style.display = "block";
        } else {
          dom.cameraWarning.style.display = "none";
        }
      }
    });
```

Clear warning in `setSessionInactive()`:
```javascript
    if (dom.cameraWarning) dom.cameraWarning.style.display = "none";
```

**Step 3: Commit**

```bash
git add templates/dashboard/index.html static/js/dashboard/session.js
git commit -m "feat: add low-light warning banner on dashboard camera feed"
```

---

### Task 9: Frontend — Faster Attendance Polling + Direct Append

**Files:**
- Modify: `static/js/dashboard/session.js:462-548` (polling and attendance rendering)

**Step 1: Reduce polling interval to 1 second**

Change line 465 from:
```javascript
    state.pollingTimer = setInterval(loadAttendance, 3000);
```
to:
```javascript
    state.pollingTimer = setInterval(loadAttendance, 1000);
```

**Step 2: Update `attendance:new` handler to directly append**

Change lines 79-82 from:
```javascript
    socket.on("attendance:new", function () {
      loadAttendance();
      loadStats();
    });
```
to:
```javascript
    socket.on("attendance:new", function (data) {
      // Direct append for instant UI update
      if (data && data.student_id) {
        appendAttendanceRow(data);
      }
      // Also refresh full list to stay in sync
      loadAttendance();
      loadStats();
    });
```

Add helper function `appendAttendanceRow()`:
```javascript
  function appendAttendanceRow(rec) {
    if (!rec || !rec.student_id) return;
    var key = rec.student_id + "|" + (rec.timestamp || new Date().toISOString());
    if (state.knownAttendanceIds.has(key)) return;

    dom.attendanceEmpty.style.display = "none";
    var tr = document.createElement("tr");
    tr.className = "attendance-row-new";

    var statusClass = "pill-present";
    var statusText = rec.status || "present";
    if (statusText === "late") statusClass = "pill-late";
    if (statusText === "not_enrolled") statusClass = "pill-not-enrolled";

    var actionsHtml = "";
    if (statusText === "not_enrolled" && rec.id) {
      actionsHtml =
        '<td><button class="btn btn-ghost btn-sm btn-approve" data-approve="' + rec.id + '">Approve</button> ' +
        '<button class="btn btn-ghost btn-sm btn-danger-ghost" data-dismiss-att="' + rec.id + '">Dismiss</button></td>';
    } else {
      actionsHtml = "<td></td>";
    }

    tr.innerHTML =
      "<td>" + escapeHtml(formatTime(rec.timestamp || new Date().toISOString())) + "</td>" +
      '<td class="font-mono">' + escapeHtml(rec.student_id || "") + "</td>" +
      "<td>" + escapeHtml(rec.student_name || "") + "</td>" +
      '<td><span class="pill ' + statusClass + '">' + escapeHtml(statusText) + "</span></td>" +
      actionsHtml;

    dom.attendanceTbody.appendChild(tr);
    state.knownAttendanceIds.add(key);
  }
```

**Step 3: Commit**

```bash
git add static/js/dashboard/session.js
git commit -m "feat: reduce attendance polling to 1s and add direct append on SocketIO event"
```

---

### Task 10: Frontend — Attendance Approve/Dismiss UI + Not-enrolled Styling

**Files:**
- Modify: `static/js/dashboard/session.js:487-548` (renderAttendance — add approve/dismiss buttons)
- Modify: `templates/dashboard/index.html` (add CSS for not_enrolled pill and buttons)
- Modify: `static/js/dashboard/session.js` (add delegated click handlers for approve/dismiss)

**Step 1: Update `renderAttendance()` to show approve/dismiss for not_enrolled rows**

In the `renderAttendance()` function, update the row rendering loop (around line 526) to include an Actions column:

Replace the `tr.innerHTML = ...` block with:
```javascript
      var statusText = rec.status || "present";
      var pillClass = "pill-present";
      if (statusText === "late") pillClass = "pill-late";
      if (statusText === "not_enrolled") pillClass = "pill-not-enrolled";

      var actionsHtml = "";
      if (statusText === "not_enrolled" && rec.id) {
        actionsHtml =
          '<td><button class="btn btn-ghost btn-sm btn-approve" data-approve="' + rec.id + '">Approve</button> ' +
          '<button class="btn btn-ghost btn-sm btn-danger-ghost" data-dismiss-att="' + rec.id + '">Dismiss</button></td>';
      } else {
        actionsHtml = "<td></td>";
      }

      tr.innerHTML =
        "<td>" + escapeHtml(formatTime(rec.timestamp)) + "</td>" +
        '<td class="font-mono">' + escapeHtml(rec.student_id || "") + "</td>" +
        "<td>" + escapeHtml(rec.student_name || "") + "</td>" +
        '<td><span class="pill ' + pillClass + '">' + escapeHtml(statusText) + "</span></td>" +
        actionsHtml;
```

**Step 2: Add Actions column header**

In `templates/dashboard/index.html`, add a new `<th>` after the Status column header in the attendance table:
```html
              <th scope="col">Actions</th>
```

**Step 3: Add CSS for not_enrolled pill**

```css
.pill-not-enrolled {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}
.btn-approve {
  color: var(--primary) !important;
}
```

**Step 4: Add delegated click handlers for approve/dismiss**

In `session.js`, add a delegated click handler on the attendance table body:
```javascript
  dom.attendanceTbody.addEventListener("click", function (e) {
    var approveBtn = e.target.closest("[data-approve]");
    if (approveBtn) {
      var id = approveBtn.getAttribute("data-approve");
      apiFetch("/api/attendance/" + id + "/approve", { method: "PATCH" })
        .then(function () {
          showToast("Attendance approved", "success");
          loadAttendance();
          loadStats();
        })
        .catch(function (err) {
          showToast(err.message || "Failed to approve", "error");
        });
      return;
    }

    var dismissBtn = e.target.closest("[data-dismiss-att]");
    if (dismissBtn) {
      var id = dismissBtn.getAttribute("data-dismiss-att");
      apiFetch("/api/attendance/" + id, { method: "DELETE" })
        .then(function () {
          showToast("Attendance dismissed", "success");
          loadAttendance();
          loadStats();
        })
        .catch(function (err) {
          showToast(err.message || "Failed to dismiss", "error");
        });
    }
  });
```

**Step 5: Update stats to exclude not_enrolled from Present count**

Check `db_helper.py:get_statistics()` — ensure the present count query uses `status = 'present'` (not counting `not_enrolled`). This should already be the case if the query filters on status, but verify and fix if needed.

**Step 6: Commit**

```bash
git add static/js/dashboard/session.js templates/dashboard/index.html
git commit -m "feat: add approve/dismiss UI for not-enrolled attendance records"
```

---

### Task 11: Frontend — Equivalent Courses Input on Session Start

**Files:**
- Modify: `templates/dashboard/index.html` (add input field in session start area)
- Modify: `static/js/dashboard/session.js:649-676` (startSession — pass equivalent_courses)
- Modify: `static/js/dashboard/session.js:276-301` (onQuickStartClick — add equivalent courses)

**Step 1: Add HTML input for equivalent courses**

In `templates/dashboard/index.html`, find the session start form area (near the course select and Start Session button). Add after the course select:

```html
        <div class="equiv-input-group" id="equiv-input-group">
          <label for="equiv-courses" class="equiv-label">Equivalent courses <span class="text-muted">(optional)</span></label>
          <input
            type="text"
            id="equiv-courses"
            class="input-field input-sm"
            placeholder="e.g. MTE401, MEE301"
          />
        </div>
```

Add CSS:
```css
.equiv-input-group {
  margin-top: 8px;
}
.equiv-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 4px;
  display: block;
}
```

**Step 2: Update `startSession()` to send equivalent_courses**

In `static/js/dashboard/session.js`, update `startSession()`:
```javascript
    var equivInput = document.getElementById("equiv-courses");
    var equivalentCourses = equivInput ? equivInput.value.trim() : "";

    apiFetch("/api/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        course_code: courseCode,
        equivalent_courses: equivalentCourses || undefined,
      }),
    })
```

**Step 3: Clear the input after session starts and on session end**

In `setSessionActive()`:
```javascript
    var equivInput = document.getElementById("equiv-courses");
    if (equivInput) equivInput.value = "";
```

**Step 4: Commit**

```bash
git add templates/dashboard/index.html static/js/dashboard/session.js
git commit -m "feat: add optional equivalent courses input when starting session"
```

---

### Task 12: Ensure `attendance:new` SocketIO Event Includes Full Record Data

**Files:**
- Modify: `app.py:399-411` (handle_worker_attendance — include student_name in emitted data)
- Modify: `db_helper.py:record_attendance()` return value (include student_name)

**Step 1: Update `record_attendance()` to return student_name**

At the end of `record_attendance()` in `db_helper.py`, change the return statement from:
```python
        return {"id": new_id, "status": status, "student_id": student_id}
```
to:
```python
        return {
            "id": new_id,
            "status": status,
            "student_id": student_id,
            "student_name": student["name"],
            "timestamp": datetime.now().isoformat(),
        }
```

**Step 2: Commit**

```bash
git add db_helper.py
git commit -m "feat: include student_name and timestamp in attendance record response"
```

---

### Task 13: Manual Smoke Test

**Step 1: Test equivalent courses flow**
1. Start the server and worker
2. Start a session with MEE401 and equivalent courses "MTE401, MEE301"
3. Have a student enrolled in MTE401 (not MEE401) face the camera
4. Verify they appear in Live Attendance as "present"

**Step 2: Test not_enrolled flow**
1. Have a student not enrolled in MEE401 or any equivalent face the camera
2. Verify they appear with "not_enrolled" badge
3. Click "Approve" — verify status changes to "present"
4. Repeat — click "Dismiss" — verify record is removed

**Step 3: Test low-light warning**
1. Cover the camera or use it in a dark room
2. Verify the red "LOW LIGHT" text overlay appears on the video
3. Verify the warning banner appears above the video feed
4. Uncover/improve lighting — verify warning disappears

**Step 4: Test camera loading state**
1. Start a session
2. Verify "Connecting to camera..." spinner appears
3. Verify it transitions to the video feed once frames arrive
4. Test timeout: stop the worker, start a session, wait 10 seconds
5. Verify error message: "Camera not responding..."

**Step 5: Test faster attendance updates**
1. Start a session with a known student
2. Face the camera — time how long until name appears in Live Attendance
3. Should be noticeably faster (1-3 seconds vs previous 3-6 seconds)
