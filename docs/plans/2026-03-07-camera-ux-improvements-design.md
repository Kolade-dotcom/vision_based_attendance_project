# Camera UX Improvements Design

## Date: 2026-03-07

## Problems

1. **No low-light warning** during live sessions (dashboard + student portal). Brightness detection exists in `face_capture.py` but is not used in `app.py:gen_frames()` or `worker.py:start_capture()`.
2. **Slow camera startup** on worker deployment. Camera only initializes when session starts, causing minutes of black screen. No loading indicator shown.
3. **Slow/missing attendance marking.** Frontend polls every 3s. Non-enrolled students are silently rejected — cross-listed courses (MEE401/MTE401/MEE301) cause legitimate students to be skipped.

## Design

### 1. Low-light Warning

- Reuse `face_capture.py:analyze_lighting()` logic in both `worker.py` and `app.py:gen_frames()`.
- When frame brightness < `MIN_BRIGHTNESS` (40), overlay a text banner on the video frame: "Low light - move to a brighter area".
- Emit a SocketIO event `camera:low_light` with `{is_low: true/false}` so the frontend can show a persistent warning toast above the video feed.
- Debounce: only emit when state changes (low -> ok or ok -> low), not every frame.
- Apply to both lecturer dashboard camera and student portal face capture page.

### 2. Faster Camera Startup

- **Pre-warm camera:** In `worker.py`, open `cv2.VideoCapture` on worker connect (not on `start_capture`). Keep a warm reference. On `start_capture`, reuse the already-open capture.
- **Loading state:** Frontend shows "Connecting to camera..." with a spinner in the canvas area when session starts but no frames have arrived yet.
- **Timeout:** If no frames arrive within 10 seconds, show an error: "Camera not responding. Check your worker connection."

### 3. Attendance Marking Speed + Enrollment Flexibility

#### 3a. Faster UI Updates
- Reduce polling interval from 3s to 1s.
- On `attendance:new` SocketIO event, directly append the new record to the table instead of re-fetching the full list.

#### 3b. Equivalent Courses
- Add optional "Equivalent course codes" input when starting a session (comma-separated, skippable).
- Store in `class_sessions` table as `equivalent_courses` (JSON array or null).
- In `record_attendance()`, check enrollment against both the session course code AND equivalent courses.

#### 3c. Non-enrolled Student Handling
- Remove the hard `return None` block for non-enrolled students in `db_helper.py:record_attendance()`.
- Instead, record attendance with status `"not_enrolled"`.
- Frontend shows these rows with a "not enrolled" badge and approve/dismiss buttons.
- **Approve:** Changes status to "present" (PATCH endpoint).
- **Dismiss:** Deletes the attendance record (DELETE endpoint).
- "not_enrolled" students do NOT count in the "Present" counter until approved.

## Files to Modify

- `worker.py` — pre-warm camera, add brightness detection
- `app.py` — add brightness detection to gen_frames(), new API endpoints for approve/dismiss
- `db_helper.py` — modify record_attendance(), add equivalent_courses support, add approve/dismiss helpers
- `camera.py` — add pre-warm capability
- `static/js/dashboard/session.js` — loading state, low-light toast, faster polling, approve/dismiss UI, equivalent courses input
- `templates/dashboard/index.html` — loading spinner markup, low-light warning markup, approve/dismiss buttons
- `templates/portal/enroll.html` — low-light warning (if not already shown during capture)
- Database migration — add `equivalent_courses` column to `class_sessions`
