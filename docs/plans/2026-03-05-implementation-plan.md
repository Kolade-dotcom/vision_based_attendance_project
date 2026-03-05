# Lumina App Split + Bug Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split the monolithic Lumina attendance app into a Lecturer Dashboard (`/dashboard/*`) and Student Portal (`/portal/*`), fix all critical bugs from code review, and overhaul the UI with a distinctive anti-vibecode design system.

**Architecture:** Same Flask server with separate blueprint groups. Shared core (db_helper, camera, face_processor, esp32_bridge, config). Two independent auth systems (lecturer sessions vs student sessions). Designed for future separation into independent Flask apps.

**Tech Stack:** Flask, SQLite, Jinja2, Tailwind CSS (CDN), vanilla JS, face_recognition, OpenCV, Bricolage Grotesque + Plus Jakarta Sans + JetBrains Mono fonts.

**Anti-Vibecode Design Rules (FRONTEND_ASSIST.md):**
- NO indigo/violet/purple primary colors — use teal `#0d9488` + orange accent `#f97316`
- NO Inter/Roboto/system-ui — use Bricolage Grotesque (display) + Plus Jakarta Sans (body)
- NO uniform rounded-lg — mix sharp corners (tables, inputs) with soft rounds (avatars, badges)
- NO colored-circle icons — icons used functionally, varying sizes
- NO transition-all — specify exact properties
- NO pure white `#FFFFFF` backgrounds — use warm off-white `#FAFAF8`
- Semantic HTML (nav, main, section, header, footer)
- All interactive states: hover, focus, active, disabled
- All data states: loading, empty, error, populated
- Mobile-first responsive design
- WCAG AA contrast ratios
- Custom shadow scale, intentional spacing rhythm

---

## Phase 0: Critical Bug Fixes & Security

These MUST be fixed before any feature work. They affect the shared core that both apps depend on.

### Task 0.1: Fix SECRET_KEY Hardcoded Fallback

**Files:**
- Modify: `app.py:29`

**Step 1: Fix the secret key handling**

Replace line 29:
```python
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
```

With:
```python
import logging
logger = logging.getLogger(__name__)

secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    logger.warning("SECRET_KEY not set! Using generated key. Sessions will not persist across restarts.")
    secret_key = os.urandom(24).hex()
app.config["SECRET_KEY"] = secret_key
```

**Step 2: Commit**
```bash
git add app.py
git commit -m "fix(security): remove hardcoded SECRET_KEY fallback"
```

---

### Task 0.2: Replace pickle with numpy for Face Encoding Serialization

**Files:**
- Modify: `app.py:117` (pickle.loads)
- Modify: `face_processor.py:78` (pickle.dumps)
- Modify: `db_helper.py` (any pickle usage)
- Modify: `api/controllers/face_capture_controller.py` (any pickle usage)
- Test: `tests/test_face_capture.py`

**Step 1: Write failing test**

In `tests/test_face_capture.py`, add:
```python
import numpy as np

def test_face_encoding_serialization_uses_numpy():
    """Face encodings should serialize via numpy, not pickle."""
    encoding = np.random.rand(128).astype(np.float64)

    # Serialize
    encoding_bytes = encoding.tobytes()

    # Deserialize
    restored = np.frombuffer(encoding_bytes, dtype=np.float64)

    np.testing.assert_array_almost_equal(encoding, restored)
```

**Step 2: Run test to verify it passes (this tests numpy approach)**
```bash
python -m pytest tests/test_face_capture.py::test_face_encoding_serialization_uses_numpy -v
```

**Step 3: Replace all pickle.dumps with numpy.tobytes**

In `face_processor.py`, replace:
```python
encoding_bytes = pickle.dumps(face_encodings[0])
```
With:
```python
encoding_bytes = face_encodings[0].tobytes()
```

**Step 4: Replace all pickle.loads with numpy.frombuffer**

In `app.py`, replace:
```python
encoding = pickle.loads(student["face_encoding"])
```
With:
```python
encoding = np.frombuffer(student["face_encoding"], dtype=np.float64)
```

Remove `import pickle` from `app.py`.

**Step 5: Search for and replace any other pickle usage in the codebase**

Check: `db_helper.py`, `api/controllers/face_capture_controller.py`, `api/controllers/student_controller.py`, `api/controllers/public_enrollment_controller.py`.

Replace ALL `pickle.dumps(encoding)` → `encoding.tobytes()` and `pickle.loads(blob)` → `np.frombuffer(blob, dtype=np.float64)`.

**Step 6: Run all tests**
```bash
python -m pytest tests/ -v
```

**Step 7: Commit**
```bash
git add -A
git commit -m "fix(security): replace pickle with numpy for face encoding serialization"
```

**IMPORTANT NOTE:** This change is NOT backward-compatible with existing face encodings stored via pickle. Existing students will need to re-enroll. If preserving existing data is critical, add a migration function that reads pickle and re-writes as numpy. But since this is pre-production, re-enrollment is acceptable.

---

### Task 0.3: Fix record_attendance Return Type Bug

**Files:**
- Modify: `db_helper.py` (the `record_attendance` function)
- Modify: `app.py:219-223` (the caller)

**Step 1: Write failing test**

In `tests/test_sessions.py`, add:
```python
def test_record_attendance_returns_dict_with_status(self):
    """record_attendance should return a dict with 'status' key, not an int."""
    # Create a user, session, and student first
    user_id = db_helper.create_user("test@test.com", "hash", "Test")
    session_data = db_helper.create_session(user_id, "MTE411")
    db_helper.add_student("STU001", "Test Student", face_encoding=b"fake_encoding")

    result = db_helper.record_attendance("STU001", status="present", course_code="MTE411")

    assert result is not None
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ("present", "late")
```

**Step 2: Run test to verify it fails**
```bash
python -m pytest tests/test_sessions.py::TestSessionManagement::test_record_attendance_returns_dict_with_status -v
```
Expected: FAIL (returns int, not dict)

**Step 3: Fix record_attendance to return a dict**

In `db_helper.py`, find the `record_attendance` function. Change the return from:
```python
return cursor.lastrowid
```
To:
```python
return {"id": cursor.lastrowid, "status": actual_status, "student_id": student_id}
```

Where `actual_status` is the status that was actually recorded (either "present" or "late" based on the late threshold logic).

**Step 4: Run test to verify it passes**
```bash
python -m pytest tests/test_sessions.py -v
```

**Step 5: Commit**
```bash
git add db_helper.py tests/test_sessions.py
git commit -m "fix: record_attendance returns dict with status instead of int"
```

---

### Task 0.4: Fix get_attendance_for_active_session Missing Argument

**Files:**
- Modify: `db_helper.py` (the `get_attendance_for_active_session` function, around line 692)

**Step 1: Fix the function to accept and pass user_id**

Find `get_attendance_for_active_session` and change:
```python
def get_attendance_for_active_session():
    active_session = get_active_session()
```
To:
```python
def get_attendance_for_active_session(user_id):
    active_session = get_active_session(user_id)
```

**Step 2: Find and fix all callers**

Search the codebase for calls to `get_attendance_for_active_session()` and pass the appropriate `user_id`.

**Step 3: Run all tests**
```bash
python -m pytest tests/ -v
```

**Step 4: Commit**
```bash
git add db_helper.py
git commit -m "fix: pass user_id to get_attendance_for_active_session"
```

---

### Task 0.5: Add MAX_CONTENT_LENGTH and Replace Debug Prints with Logging

**Files:**
- Modify: `app.py`
- Modify: `db_helper.py`

**Step 1: Add MAX_CONTENT_LENGTH to Flask app**

In `app.py`, after the SECRET_KEY line:
```python
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max request size
```

**Step 2: Set up logging in app.py**

At the top of `app.py`:
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

Replace ALL `print(f"[DEBUG]...")` and `print(f"DEBUG:...")` with `logger.debug(...)`.
Replace ALL `print(f"✓ ...")` with `logger.info(...)`.
Replace ALL `print(f"Error ...")` with `logger.error(...)`.

**Step 3: Do the same for db_helper.py**

Add `logger = logging.getLogger(__name__)` at the top.
Replace all print statements with appropriate logger calls.

**Step 4: Remove duplicate face_distance computation in app.py**

In `app.py`, the face_distance is computed twice (lines ~186-191 and ~200-203). Remove the first computation (the debug-only one). Keep only the one inside the `if True in matches:` block.

**Step 5: Remove developer "thinking" comments from db_helper.py**

Delete the block of comments around lines 431-446 that contain developer thought process notes.

**Step 6: Move `import time` to top of app.py**

Remove `import time` from inside `gen_enrollment_frames` and add it to the top-level imports.

**Step 7: Commit**
```bash
git add app.py db_helper.py
git commit -m "fix: add request size limit, replace prints with logging, remove dead code"
```

---

### Task 0.6: Fix XSS in JavaScript Template Literals

**Files:**
- Modify: `static/js/modules/ui.js`
- Modify: `static/js/pages/dashboard.js`
- Modify: `static/js/pages/enrollment.js`

**Step 1: Create a shared HTML escape utility**

In `static/js/modules/ui.js`, add at the top:
```javascript
/**
 * Escape HTML special characters to prevent XSS.
 */
export function escapeHtml(str) {
    if (str == null) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
}
```

**Step 2: Find and wrap all dynamic content in template literals**

In every JS file that renders student data into HTML, wrap dynamic values:

Before:
```javascript
`<td>${record.student_name}</td>`
```
After:
```javascript
`<td>${escapeHtml(record.student_name)}</td>`
```

Apply to ALL dynamic content: student names, IDs, course codes, emails, etc.

**Step 3: Commit**
```bash
git add static/js/modules/ui.js static/js/pages/dashboard.js static/js/pages/enrollment.js
git commit -m "fix(security): escape HTML in dynamic content to prevent XSS"
```

---

## Phase 1: Database Migration & Shared Design System

### Task 1.1: Database Schema Changes for Student Auth

**Files:**
- Modify: `database/schema.sql`
- Modify: `db_helper.py` (migration logic in `init_database`)

**Step 1: Update schema.sql**

Add columns to students table definition:
```sql
-- In the students CREATE TABLE, add:
    password_hash TEXT,            -- bcrypt hash for portal login
    is_enrolled INTEGER DEFAULT 0, -- 1 = face capture completed
```

Remove `status`, `enrolled_via_link_id`, `created_by`, `rejection_reason` columns from the schema definition (keep them in migration logic for backward compat).

**Step 2: Add migration logic in db_helper.py init_database()**

In the students migration section, add:
```python
if "password_hash" not in columns:
    conn.execute("ALTER TABLE students ADD COLUMN password_hash TEXT")
    print("Migration: Added password_hash column to students")

if "is_enrolled" not in columns:
    conn.execute("ALTER TABLE students ADD COLUMN is_enrolled INTEGER DEFAULT 0")
    print("Migration: Added is_enrolled column to students")
```

**Step 3: Add student auth helper functions to db_helper.py**

```python
def get_student_by_matric(matric_number):
    """Get student by matric number (student_id)."""
    with get_db_connection() as conn:
        student = conn.execute(
            "SELECT * FROM students WHERE student_id = ?", (matric_number,)
        ).fetchone()
        return dict(student) if student else None

def create_student_account(matric_number, name, email, password_hash):
    """Create a student account (no face encoding yet)."""
    with get_db_connection() as conn:
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """INSERT INTO students (student_id, name, email, password_hash, status, is_enrolled, created_at)
               VALUES (?, ?, ?, ?, 'approved', 0, ?)""",
            (matric_number, name, email, password_hash, now)
        )
        conn.commit()
        return cursor.lastrowid

def update_student_enrollment(student_id, face_encoding, level, courses):
    """Mark student as enrolled with face encoding and academic details."""
    with get_db_connection() as conn:
        courses_json = json.dumps(courses) if isinstance(courses, list) else courses
        conn.execute(
            """UPDATE students
               SET face_encoding = ?, level = ?, courses = ?, is_enrolled = 1, updated_at = ?
               WHERE student_id = ?""",
            (face_encoding, level, courses_json, datetime.now().isoformat(), student_id)
        )
        conn.commit()

def get_student_attendance(student_id, course_code=None):
    """Get attendance records for a student, optionally filtered by course."""
    with get_db_connection() as conn:
        if course_code:
            rows = conn.execute(
                """SELECT a.*, cs.course_code as session_course, cs.start_time as session_start
                   FROM attendance a
                   JOIN class_sessions cs ON a.session_id = cs.id
                   WHERE a.student_id = ? AND a.course_code = ?
                   ORDER BY a.timestamp DESC""",
                (student_id, course_code)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT a.*, cs.course_code as session_course, cs.start_time as session_start
                   FROM attendance a
                   JOIN class_sessions cs ON a.session_id = cs.id
                   WHERE a.student_id = ?
                   ORDER BY a.timestamp DESC""",
                (student_id,)
            ).fetchall()
        return [dict(row) for row in rows]

def get_student_attendance_stats(student_id, course_code=None):
    """Get attendance stats for a student."""
    with get_db_connection() as conn:
        if course_code:
            total = conn.execute(
                """SELECT COUNT(DISTINCT cs.id) FROM class_sessions cs
                   WHERE cs.course_code = ? AND cs.is_active = 0""",
                (course_code,)
            ).fetchone()[0]
            present = conn.execute(
                """SELECT COUNT(*) FROM attendance
                   WHERE student_id = ? AND course_code = ? AND status = 'present'""",
                (student_id, course_code)
            ).fetchone()[0]
            late = conn.execute(
                """SELECT COUNT(*) FROM attendance
                   WHERE student_id = ? AND course_code = ? AND status = 'late'""",
                (student_id, course_code)
            ).fetchone()[0]
        else:
            total = conn.execute(
                "SELECT COUNT(*) FROM class_sessions WHERE is_active = 0"
            ).fetchone()[0]
            present = conn.execute(
                "SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'present'",
                (student_id,)
            ).fetchone()[0]
            late = conn.execute(
                "SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'late'",
                (student_id,)
            ).fetchone()[0]

        attended = present + late
        rate = round((attended / total) * 100, 1) if total > 0 else 0
        return {
            "total_sessions": total,
            "present": present,
            "late": late,
            "absent": total - attended,
            "attendance_rate": rate
        }

def update_student_profile(student_id, name=None, email=None, level=None, courses=None):
    """Update student profile fields."""
    with get_db_connection() as conn:
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if level is not None:
            updates.append("level = ?")
            params.append(level)
        if courses is not None:
            updates.append("courses = ?")
            params.append(json.dumps(courses) if isinstance(courses, list) else courses)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(student_id)

        conn.execute(
            f"UPDATE students SET {', '.join(updates)} WHERE student_id = ?",
            params
        )
        conn.commit()
        return True

def update_student_face(student_id, face_encoding):
    """Update student face encoding (re-capture)."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE students SET face_encoding = ?, updated_at = ? WHERE student_id = ?",
            (face_encoding, datetime.now().isoformat(), student_id)
        )
        conn.commit()

def update_student_password(student_id, password_hash):
    """Update student password."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE students SET password_hash = ?, updated_at = ? WHERE student_id = ?",
            (password_hash, datetime.now().isoformat(), student_id)
        )
        conn.commit()
```

**Step 4: Write tests**

In `tests/test_db.py`, add:
```python
def test_create_student_account():
    student_id = db_helper.create_student_account("125/22/1/0178", "John Doe", "john@uni.edu", "hashed_pw")
    assert student_id is not None
    student = db_helper.get_student_by_matric("125/22/1/0178")
    assert student is not None
    assert student["name"] == "John Doe"
    assert student["is_enrolled"] == 0
    assert student["password_hash"] == "hashed_pw"

def test_update_student_enrollment():
    db_helper.create_student_account("125/22/1/0179", "Jane Doe", "jane@uni.edu", "hashed_pw")
    db_helper.update_student_enrollment("125/22/1/0179", b"fake_encoding", "400", ["MTE411", "MTE412"])
    student = db_helper.get_student_by_matric("125/22/1/0179")
    assert student["is_enrolled"] == 1
    assert student["level"] == "400"

def test_get_student_attendance_stats_empty():
    db_helper.create_student_account("125/22/1/0180", "Bob", "bob@uni.edu", "hashed_pw")
    stats = db_helper.get_student_attendance_stats("125/22/1/0180")
    assert stats["total_sessions"] == 0
    assert stats["attendance_rate"] == 0
```

**Step 5: Run tests**
```bash
python -m pytest tests/test_db.py -v
```

**Step 6: Commit**
```bash
git add database/schema.sql db_helper.py tests/test_db.py
git commit -m "feat: add student auth columns and portal DB helpers"
```

---

### Task 1.2: Create Shared Design System CSS

**Files:**
- Create: `static/css/design-system.css` (replaces theme.css)
- Modify: `static/js/theme.js` (keep theme toggle logic)

**Step 1: Create the design system CSS**

Create `static/css/design-system.css` with:

```css
/* ============================================================
   LUMINA DESIGN SYSTEM
   Anti-vibecode. Intentional. Warm.
   ============================================================ */

/* --- Fonts --- */
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,200..800&family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* --- Light Theme (Default) --- */
:root {
    /* Brand */
    --brand: #0d9488;
    --brand-hover: #0f766e;
    --brand-light: #ccfbf1;
    --brand-muted: rgba(13, 148, 136, 0.12);
    --accent: #f97316;
    --accent-hover: #ea580c;
    --accent-light: #fff7ed;

    /* Surfaces */
    --surface: #FAFAF8;
    --surface-raised: #FFFFFF;
    --surface-sunken: #f0f0ec;
    --surface-overlay: rgba(0, 0, 0, 0.4);

    /* Text */
    --text-primary: #1a1a1a;
    --text-secondary: #5c5c5c;
    --text-muted: #9ca3af;
    --text-inverse: #FAFAF8;

    /* Borders */
    --border: #e8e8e4;
    --border-strong: #d4d4cf;
    --border-focus: var(--brand);

    /* Semantic */
    --success: #059669;
    --success-light: #ecfdf5;
    --warning: #d97706;
    --warning-light: #fffbeb;
    --danger: #dc2626;
    --danger-light: #fef2f2;

    /* Shadows (custom scale, NOT Tailwind defaults) */
    --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.04);
    --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.06);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
    --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.1);
    --shadow-focus: 0 0 0 3px rgba(13, 148, 136, 0.25);

    /* Spacing scale */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 24px;
    --space-6: 32px;
    --space-7: 48px;
    --space-8: 64px;
    --space-9: 96px;

    /* Radii (mixed, NOT uniform rounded-lg) */
    --radius-none: 0;
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-full: 9999px;

    /* Typography */
    --font-display: 'Bricolage Grotesque', system-ui, sans-serif;
    --font-body: 'Plus Jakarta Sans', system-ui, sans-serif;
    --font-mono: 'JetBrains Mono', monospace;

    --text-xs: clamp(0.7rem, 1.5vw, 0.75rem);
    --text-sm: clamp(0.8rem, 1.8vw, 0.875rem);
    --text-base: clamp(0.875rem, 2vw, 1rem);
    --text-lg: clamp(1rem, 2.2vw, 1.125rem);
    --text-xl: clamp(1.125rem, 2.5vw, 1.25rem);
    --text-2xl: clamp(1.25rem, 3vw, 1.5rem);
    --text-3xl: clamp(1.5rem, 4vw, 1.875rem);
    --text-4xl: clamp(2rem, 5vw, 2.5rem);

    /* Transitions (NEVER transition-all) */
    --transition-colors: color 150ms ease, background-color 150ms ease, border-color 150ms ease;
    --transition-transform: transform 200ms ease;
    --transition-opacity: opacity 200ms ease;
    --transition-shadow: box-shadow 200ms ease;
}

/* --- Dark Theme --- */
[data-theme="dark"] {
    --brand: #2dd4bf;
    --brand-hover: #14b8a6;
    --brand-light: rgba(45, 212, 191, 0.12);
    --brand-muted: rgba(45, 212, 191, 0.08);
    --accent: #fb923c;
    --accent-hover: #f97316;
    --accent-light: rgba(251, 146, 60, 0.12);

    --surface: #141414;
    --surface-raised: #1e1e1e;
    --surface-sunken: #0a0a0a;
    --surface-overlay: rgba(0, 0, 0, 0.6);

    --text-primary: #f0f0ec;
    --text-secondary: #a1a1a1;
    --text-muted: #6b7280;
    --text-inverse: #1a1a1a;

    --border: #2a2a2a;
    --border-strong: #3a3a3a;

    --success: #34d399;
    --success-light: rgba(52, 211, 153, 0.12);
    --warning: #fbbf24;
    --warning-light: rgba(251, 191, 36, 0.12);
    --danger: #f87171;
    --danger-light: rgba(248, 113, 113, 0.12);

    --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.2);
    --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
    --shadow-focus: 0 0 0 3px rgba(45, 212, 191, 0.3);
}

/* --- Base Reset & Defaults --- */
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    font-size: 16px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    scroll-behavior: smooth;
}

body {
    font-family: var(--font-body);
    font-size: var(--text-base);
    color: var(--text-primary);
    background-color: var(--surface);
    line-height: 1.6;
    min-height: 100vh;
}

/* --- Typography --- */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-display);
    font-weight: 700;
    line-height: 1.2;
    letter-spacing: -0.02em;
    color: var(--text-primary);
}

h1 { font-size: var(--text-4xl); letter-spacing: -0.03em; }
h2 { font-size: var(--text-3xl); }
h3 { font-size: var(--text-2xl); }
h4 { font-size: var(--text-xl); }

p { color: var(--text-secondary); }

code, .mono {
    font-family: var(--font-mono);
    font-size: 0.9em;
}

/* --- Links --- */
a {
    color: var(--brand);
    text-decoration: none;
    transition: var(--transition-colors);
}
a:hover { color: var(--brand-hover); }
a:focus-visible {
    outline: 2px solid var(--brand);
    outline-offset: 2px;
    border-radius: var(--radius-sm);
}

/* --- Buttons --- */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-5);
    font-family: var(--font-body);
    font-size: var(--text-sm);
    font-weight: 600;
    line-height: 1;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: var(--transition-colors), var(--transition-transform), var(--transition-shadow);
    white-space: nowrap;
    min-height: 40px;
}
.btn:focus-visible {
    outline: none;
    box-shadow: var(--shadow-focus);
}
.btn:active { transform: scale(0.98); }
.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
}

.btn-primary {
    background: var(--brand);
    color: var(--text-inverse);
}
.btn-primary:hover:not(:disabled) { background: var(--brand-hover); }

.btn-secondary {
    background: transparent;
    color: var(--text-primary);
    border-color: var(--border-strong);
}
.btn-secondary:hover:not(:disabled) { background: var(--surface-sunken); }

.btn-danger {
    background: var(--danger);
    color: white;
}
.btn-danger:hover:not(:disabled) { background: #b91c1c; }

.btn-ghost {
    background: transparent;
    color: var(--text-secondary);
    border: none;
    padding: var(--space-2) var(--space-3);
}
.btn-ghost:hover:not(:disabled) {
    background: var(--surface-sunken);
    color: var(--text-primary);
}

.btn-sm {
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-xs);
    min-height: 32px;
}
.btn-lg {
    padding: var(--space-4) var(--space-6);
    font-size: var(--text-base);
    min-height: 48px;
}

/* --- Form Inputs (sharp corners, NOT rounded-lg) --- */
.input {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--text-primary);
    background: var(--surface-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    transition: var(--transition-colors), var(--transition-shadow);
    min-height: 44px; /* WCAG touch target */
}
.input:hover { border-color: var(--border-strong); }
.input:focus {
    outline: none;
    border-color: var(--brand);
    box-shadow: var(--shadow-focus);
}
.input::placeholder { color: var(--text-muted); }
.input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: var(--surface-sunken);
}
.input-error { border-color: var(--danger); }
.input-error:focus { box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.25); }

.label {
    display: block;
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-2);
}

select.input {
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' stroke='%239ca3af' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m4 6 4 4 4-4'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right var(--space-3) center;
    padding-right: var(--space-8);
}

/* --- Cards --- */
.card {
    background: var(--surface-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-xs);
}
.card-padded { padding: var(--space-5); }

/* --- Status Pills --- */
.pill {
    display: inline-flex;
    align-items: center;
    padding: var(--space-1) var(--space-3);
    font-size: var(--text-xs);
    font-weight: 600;
    border-radius: var(--radius-full);
    line-height: 1.4;
}
.pill-present {
    background: var(--success-light);
    color: var(--success);
}
.pill-late {
    background: var(--warning-light);
    color: var(--warning);
}
.pill-absent {
    background: var(--danger-light);
    color: var(--danger);
}
.pill-brand {
    background: var(--brand-light);
    color: var(--brand);
}

/* --- Tables (sharp corners, warm alternating rows) --- */
.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--text-sm);
}
.data-table th {
    text-align: left;
    padding: var(--space-3) var(--space-4);
    font-weight: 600;
    font-size: var(--text-xs);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    background: var(--surface-sunken);
}
.data-table td {
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border);
    color: var(--text-secondary);
}
.data-table tr:hover td {
    background: var(--brand-muted);
}
.data-table td:first-child { color: var(--text-primary); font-weight: 500; }

/* --- Course Selector (adaptive pills / dropdown) --- */
.course-pills {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
}
.course-pill {
    padding: var(--space-2) var(--space-4);
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    font-weight: 500;
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    transition: var(--transition-colors);
    min-height: 36px;
}
.course-pill:hover { border-color: var(--brand); color: var(--brand); }
.course-pill.active {
    background: var(--brand);
    color: var(--text-inverse);
    border-color: var(--brand);
}

/* --- Empty States --- */
.empty-state {
    text-align: center;
    padding: var(--space-8) var(--space-5);
    color: var(--text-muted);
}
.empty-state p {
    color: var(--text-muted);
    font-size: var(--text-sm);
    max-width: 320px;
    margin: 0 auto;
}

/* --- Toast Notifications --- */
.toast-container {
    position: fixed;
    top: var(--space-5);
    right: var(--space-5);
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
}
.toast {
    padding: var(--space-4) var(--space-5);
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
    font-weight: 500;
    box-shadow: var(--shadow-md);
    animation: toast-in 300ms ease forwards;
    max-width: 360px;
}
.toast-success { background: var(--success); color: white; }
.toast-error { background: var(--danger); color: white; }
.toast-warning { background: var(--warning); color: white; }

@keyframes toast-in {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
}

/* --- Loading Skeleton --- */
.skeleton {
    background: linear-gradient(90deg, var(--surface-sunken) 25%, var(--border) 50%, var(--surface-sunken) 75%);
    background-size: 200% 100%;
    animation: skeleton-pulse 1.5s ease-in-out infinite;
    border-radius: var(--radius-sm);
}
@keyframes skeleton-pulse {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* --- Responsive Utilities --- */
@media (max-width: 768px) {
    .hide-mobile { display: none !important; }
}
@media (min-width: 769px) {
    .hide-desktop { display: none !important; }
}

/* --- Focus visible for keyboard nav --- */
:focus:not(:focus-visible) { outline: none; }
:focus-visible {
    outline: 2px solid var(--brand);
    outline-offset: 2px;
}
```

**Step 2: Update theme.js**

Ensure theme.js uses `data-theme` attribute on `<html>`:
```javascript
(function() {
    const saved = localStorage.getItem('lumina-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
})();

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('lumina-theme', next);
}
```

**Step 3: Commit**
```bash
git add static/css/design-system.css static/js/theme.js
git commit -m "feat: add Lumina design system with light/dark themes"
```

---

## Phase 2: App Structure & Routing

### Task 2.1: Create Blueprint Structure

**Files:**
- Create: `api/routes/dashboard_routes.py`
- Create: `api/routes/portal_routes.py`
- Create: `api/controllers/portal_auth_controller.py`
- Create: `api/controllers/portal_controller.py`
- Modify: `app.py` (register new blueprints, update routes)

**Step 1: Create dashboard page routes**

Create `api/routes/dashboard_routes.py`:
```python
from flask import Blueprint, render_template, session, redirect

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def dashboard_login_required(view):
    """Decorator requiring lecturer login."""
    import functools
    @functools.wraps(view)
    def wrapped(**kwargs):
        if 'user_id' not in session:
            return redirect('/dashboard/login')
        return view(**kwargs)
    return wrapped

@dashboard_bp.route('/login')
def login():
    return render_template('dashboard/login.html')

@dashboard_bp.route('/')
@dashboard_login_required
def index():
    return render_template('dashboard/index.html')

@dashboard_bp.route('/analytics')
@dashboard_login_required
def analytics():
    return render_template('dashboard/analytics.html')

@dashboard_bp.route('/settings')
@dashboard_login_required
def settings():
    return render_template('dashboard/settings.html')
```

**Step 2: Create portal auth controller**

Create `api/controllers/portal_auth_controller.py`:
```python
import functools
from flask import session, redirect, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import db_helper

def student_login_required(view):
    """Decorator requiring student login."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if 'student_id' not in session:
            return redirect('/portal/login')
        return view(**kwargs)
    return wrapped

def student_enrollment_required(view):
    """Decorator requiring completed face enrollment."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if 'student_id' not in session:
            return redirect('/portal/login')
        student = db_helper.get_student_by_matric(session['student_id'])
        if not student or not student.get('is_enrolled'):
            return redirect('/portal/enroll')
        return view(**kwargs)
    return wrapped

def student_login_logic(data):
    """Handle student login."""
    matric = data.get('matric_number', '').strip()
    password = data.get('password', '')

    if not matric or not password:
        return jsonify({'error': 'Matric number and password are required'}), 400

    student = db_helper.get_student_by_matric(matric)

    if student and student.get('password_hash') and check_password_hash(student['password_hash'], password):
        session.clear()
        session['student_id'] = student['student_id']
        session['student_name'] = student['name']
        session['is_student'] = True
        return jsonify({'status': 'success', 'is_enrolled': bool(student.get('is_enrolled'))}), 200

    return jsonify({'error': 'Invalid matric number or password'}), 401

def student_signup_logic(data):
    """Handle student signup."""
    matric = data.get('matric_number', '').strip()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip() or None
    password = data.get('password', '')

    if not matric or not name or not password:
        return jsonify({'error': 'Matric number, name, and password are required'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    existing = db_helper.get_student_by_matric(matric)
    if existing:
        return jsonify({'error': 'Matric number already registered'}), 409

    password_hash = generate_password_hash(password)
    student_id = db_helper.create_student_account(matric, name, email, password_hash)

    if student_id:
        session.clear()
        session['student_id'] = matric
        session['student_name'] = name
        session['is_student'] = True
        return jsonify({'status': 'success', 'is_enrolled': False}), 201

    return jsonify({'error': 'Failed to create account'}), 500

def student_logout_logic():
    """Handle student logout."""
    session.clear()
    return redirect('/portal/login')
```

**Step 3: Create portal page routes**

Create `api/routes/portal_routes.py`:
```python
from flask import Blueprint, render_template, session, redirect
from api.controllers.portal_auth_controller import student_login_required, student_enrollment_required

portal_bp = Blueprint('portal', __name__, url_prefix='/portal')

@portal_bp.route('/login')
def login():
    return render_template('portal/login.html')

@portal_bp.route('/enroll')
@student_login_required
def enroll():
    return render_template('portal/enroll.html')

@portal_bp.route('/')
@student_enrollment_required
def home():
    return render_template('portal/home.html')

@portal_bp.route('/attendance')
@student_enrollment_required
def attendance():
    return render_template('portal/attendance.html')

@portal_bp.route('/profile')
@student_enrollment_required
def profile():
    return render_template('portal/profile.html')
```

**Step 4: Create portal API routes**

Create `api/routes/portal_api_routes.py`:
```python
from flask import Blueprint, request, session, jsonify
from api.controllers.portal_auth_controller import (
    student_login_logic, student_signup_logic, student_logout_logic,
    student_login_required, student_enrollment_required
)
from api.controllers.portal_controller import (
    get_home_data_logic, get_attendance_logic, get_profile_logic,
    update_profile_logic, update_face_logic, change_password_logic,
    complete_enrollment_logic
)

portal_api_bp = Blueprint('portal_api', __name__, url_prefix='/api/portal')

@portal_api_bp.route('/auth/login', methods=['POST'])
def login():
    return student_login_logic(request.json)

@portal_api_bp.route('/auth/signup', methods=['POST'])
def signup():
    return student_signup_logic(request.json)

@portal_api_bp.route('/auth/logout')
def logout():
    return student_logout_logic()

@portal_api_bp.route('/home', methods=['GET'])
@student_enrollment_required
def home_data():
    return get_home_data_logic(session['student_id'])

@portal_api_bp.route('/attendance', methods=['GET'])
@student_enrollment_required
def attendance():
    course = request.args.get('course')
    return get_attendance_logic(session['student_id'], course)

@portal_api_bp.route('/profile', methods=['GET'])
@student_login_required
def get_profile():
    return get_profile_logic(session['student_id'])

@portal_api_bp.route('/profile', methods=['PUT'])
@student_login_required
def update_profile():
    return update_profile_logic(session['student_id'], request.json)

@portal_api_bp.route('/face', methods=['PUT'])
@student_login_required
def update_face():
    return update_face_logic(session['student_id'], request.json)

@portal_api_bp.route('/password', methods=['PUT'])
@student_login_required
def change_password():
    return change_password_logic(session['student_id'], request.json)

@portal_api_bp.route('/enroll', methods=['POST'])
@student_login_required
def complete_enrollment():
    return complete_enrollment_logic(session['student_id'], request.json)
```

**Step 5: Create portal controller**

Create `api/controllers/portal_controller.py`:
```python
from flask import jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import db_helper
import json
import numpy as np

def get_home_data_logic(student_id):
    """Get student home page data."""
    student = db_helper.get_student_by_matric(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    courses = json.loads(student['courses']) if student.get('courses') else []
    stats = db_helper.get_student_attendance_stats(student_id)

    # Check for active sessions in student's courses
    today_attendance = []
    for course in courses:
        active = db_helper.get_active_session_by_course(course)
        if active:
            # Check if student was marked in this session
            attendance = db_helper.get_student_session_attendance(student_id, active['id'])
            today_attendance.append({
                'course_code': course,
                'session_active': True,
                'marked': attendance is not None,
                'status': attendance['status'] if attendance else None,
                'time': attendance['timestamp'] if attendance else None
            })

    recent = db_helper.get_student_attendance(student_id)[:5]

    return jsonify({
        'student': {
            'name': student['name'],
            'matric': student['student_id'],
            'is_enrolled': bool(student.get('is_enrolled'))
        },
        'stats': stats,
        'today': today_attendance,
        'recent': recent
    })

def get_attendance_logic(student_id, course_code=None):
    """Get student attendance records."""
    records = db_helper.get_student_attendance(student_id, course_code)
    stats = db_helper.get_student_attendance_stats(student_id, course_code)

    student = db_helper.get_student_by_matric(student_id)
    courses = json.loads(student['courses']) if student and student.get('courses') else []

    return jsonify({
        'records': records,
        'stats': stats,
        'courses': courses
    })

def get_profile_logic(student_id):
    """Get student profile."""
    student = db_helper.get_student_by_matric(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    courses = json.loads(student['courses']) if student.get('courses') else []

    return jsonify({
        'matric': student['student_id'],
        'name': student['name'],
        'email': student.get('email', ''),
        'level': student.get('level', ''),
        'courses': courses,
        'is_enrolled': bool(student.get('is_enrolled'))
    })

def update_profile_logic(student_id, data):
    """Update student profile."""
    name = data.get('name')
    email = data.get('email')
    level = data.get('level')
    courses = data.get('courses')

    success = db_helper.update_student_profile(student_id, name=name, email=email, level=level, courses=courses)

    if success:
        return jsonify({'status': 'success'})
    return jsonify({'error': 'No changes made'}), 400

def update_face_logic(student_id, data):
    """Update student face encoding."""
    import base64
    encoding_b64 = data.get('face_encoding')
    if not encoding_b64:
        return jsonify({'error': 'Face encoding is required'}), 400

    encoding_bytes = base64.b64decode(encoding_b64)
    db_helper.update_student_face(student_id, encoding_bytes)

    return jsonify({'status': 'success'})

def change_password_logic(student_id, data):
    """Change student password."""
    current = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current or not new_password:
        return jsonify({'error': 'Current and new password are required'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400

    student = db_helper.get_student_by_matric(student_id)
    if not student or not check_password_hash(student['password_hash'], current):
        return jsonify({'error': 'Current password is incorrect'}), 401

    db_helper.update_student_password(student_id, generate_password_hash(new_password))
    return jsonify({'status': 'success'})

def complete_enrollment_logic(student_id, data):
    """Complete student enrollment with face encoding and academic details."""
    import base64

    encoding_b64 = data.get('face_encoding')
    level = data.get('level')
    courses = data.get('courses', [])

    if not encoding_b64:
        return jsonify({'error': 'Face encoding is required'}), 400
    if not level:
        return jsonify({'error': 'Level is required'}), 400

    encoding_bytes = base64.b64decode(encoding_b64)
    db_helper.update_student_enrollment(student_id, encoding_bytes, level, courses)

    return jsonify({'status': 'success'})
```

**Step 6: Add missing DB helper functions**

Add to `db_helper.py`:
```python
def get_active_session_by_course(course_code):
    """Get active session for a specific course (any lecturer)."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM class_sessions WHERE course_code = ? AND is_active = 1",
            (course_code,)
        ).fetchone()
        return dict(row) if row else None

def get_student_session_attendance(student_id, session_id):
    """Get a student's attendance record for a specific session."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM attendance WHERE student_id = ? AND session_id = ?",
            (student_id, session_id)
        ).fetchone()
        return dict(row) if row else None
```

**Step 7: Update app.py — register new blueprints, add redirect**

In `app.py`:
- Import and register `dashboard_bp`, `portal_bp`, `portal_api_bp`
- Remove old page routes (`/`, `/enroll`, `/login`, `/enroll/<token>`, `/enrollment-success`)
- Remove enrollment link and public enrollment blueprint registrations
- Add root redirect:

```python
from api.routes.dashboard_routes import dashboard_bp
from api.routes.portal_routes import portal_bp
from api.routes.portal_api_routes import portal_api_bp

app.register_blueprint(dashboard_bp)
app.register_blueprint(portal_bp)
app.register_blueprint(portal_api_bp)

@app.route("/")
def root():
    return redirect("/dashboard/")
```

- Keep: `student_bp`, `attendance_bp`, `auth_bp`, `session_bp`, `face_capture_bp` (these are the API blueprints the dashboard still uses)
- Remove: `enrollment_link_bp`, `public_enrollment_bp`

**Step 8: Update auth_controller.py login_required redirect**

In `api/controllers/auth_controller.py`, change the redirect:
```python
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect('/dashboard/login')
        return view(**kwargs)
    return wrapped_view
```

Also update `logout_logic`:
```python
def logout_logic():
    session.clear()
    return redirect('/dashboard/login')
```

**Step 9: Commit**
```bash
git add api/routes/dashboard_routes.py api/routes/portal_routes.py api/routes/portal_api_routes.py api/controllers/portal_auth_controller.py api/controllers/portal_controller.py app.py db_helper.py api/controllers/auth_controller.py
git commit -m "feat: create dashboard and portal blueprint structure"
```

---

## Phase 3: Dashboard Templates (UI Overhaul)

### Task 3.1: Create Dashboard Base Template

**Files:**
- Create: `templates/dashboard/base.html`

This is the layout shell for all dashboard pages. Includes:
- Sidebar (desktop) with 240px width, logo, nav links, user card, theme toggle
- Mobile top bar with hamburger → drawer
- Content area with max-width 1280px
- Links to design-system.css, Google Fonts, theme.js
- FOUC prevention script in `<head>`
- Toast container
- Semantic HTML (nav, main, header, footer)

Follow the design doc in `docs/plans/2026-03-05-app-split-design.md` section 3.2 for layout specs.

Use `{% block content %}{% endblock %}` for page content.
Use `{% block title %}{% endblock %}` for page title.
Use `{% block scripts %}{% endblock %}` for page-specific JS.

Nav items: Live Session (href="/dashboard/"), Analytics (href="/dashboard/analytics"), Settings (href="/dashboard/settings").
Active nav item determined by `request.path`.

**Step 1: Create the template** (full HTML — see design doc for specs)

**Step 2: Commit**
```bash
git add templates/dashboard/base.html
git commit -m "feat: create dashboard base template with sidebar layout"
```

---

### Task 3.2: Create Dashboard Login Page

**Files:**
- Create: `templates/dashboard/login.html`
- Create: `static/js/dashboard/login.js`

Standalone page (does NOT extend dashboard/base.html — no sidebar for login).
Login/Signup toggle tabs. Clean, centered card on warm off-white background.
Uses design system CSS tokens.
Form fields: email, password, (name for signup).
Submits to `/api/auth/login` or `/api/auth/signup`.
On success: redirect to `/dashboard/`.

Follow FRONTEND_ASSIST.md anti-vibecode rules:
- No "Get Started" or "Supercharge" copy
- Specific button text: "Sign in" / "Create account"
- Visible focus states
- Error state handling
- Mobile-responsive (card should fill width on mobile with padding)

**Step 1: Create the template and JS**

**Step 2: Commit**
```bash
git add templates/dashboard/login.html static/js/dashboard/login.js
git commit -m "feat: create dashboard login page"
```

---

### Task 3.3: Create Dashboard Main Page (Live Session)

**Files:**
- Create: `templates/dashboard/index.html`
- Create: `static/js/dashboard/session.js`

Extends `dashboard/base.html`.

Layout (per design doc section 3.3):
1. Header bar with greeting + course selector
2. Session control strip (start/end session)
3. Two-column layout (camera + attendance table on left, stats on right)
4. Session history table below

Course selector: adaptive pills (1-3 courses) or dropdown (4+).
Session control: shows different state for active vs inactive.
Camera feed: `<img>` tag with `src="/video_feed"` (MJPEG stream).
Attendance table: real-time updates via polling `/api/attendance/today`.
Stats: large numbers with labels.
Session history: data table with export/delete actions.

JS handles:
- Course selector rendering
- Session start/end (POST to `/api/sessions/start`, `/api/sessions/end`)
- Polling attendance (every 3 seconds while session active)
- Session history loading
- Confirmation modals for end session / delete session

**Step 1: Create template and JS**

**Step 2: Test manually — start server, navigate to /dashboard/**

**Step 3: Commit**
```bash
git add templates/dashboard/index.html static/js/dashboard/session.js
git commit -m "feat: create dashboard live session page with real-time attendance"
```

---

### Task 3.4: Create Dashboard Analytics Page

**Files:**
- Create: `templates/dashboard/analytics.html`
- Create: `static/js/dashboard/analytics.js`
- Modify: `db_helper.py` (add analytics query functions)

Extends `dashboard/base.html`.

Layout (per design doc section 3.4):
- Course selector at top
- Attendance rate trend (last 10 sessions) — use simple SVG/CSS bar chart or Canvas. No heavy chart libraries.
- Student leaderboard — table sorted by attendance %. Red flag (orange pill) for < 75%.
- Session summaries — recent sessions with stats.

DB helper functions to add:
```python
def get_attendance_trend(user_id, course_code=None, limit=10):
    """Get attendance rate per session for last N sessions."""

def get_student_leaderboard(course_code=None):
    """Get students ranked by attendance rate for a course."""

def get_lecturer_courses(user_id):
    """Get distinct course codes from lecturer's sessions."""
```

**Step 1: Add DB helper functions**
**Step 2: Create template and JS**
**Step 3: Commit**
```bash
git add templates/dashboard/analytics.html static/js/dashboard/analytics.js db_helper.py
git commit -m "feat: create dashboard analytics page with attendance trends"
```

---

### Task 3.5: Create Dashboard Settings Page

**Files:**
- Create: `templates/dashboard/settings.html`
- Create: `static/js/dashboard/settings.js`
- Create: `api/controllers/settings_controller.py`
- Modify: `api/routes/dashboard_routes.py` or create `api/routes/dashboard_api_routes.py`

Extends `dashboard/base.html`.

Sections:
1. Late threshold (number input, save)
2. Camera source (radio: ESP32/Webcam/Auto, ESP32 IP field)
3. Courses (chips + add input)
4. Account (name, email, password change)

API endpoints:
- `GET /api/dashboard/settings` — get current settings
- `PUT /api/dashboard/settings` — update settings
- `PUT /api/dashboard/account` — update account info
- `PUT /api/dashboard/password` — change password

Settings stored in the `settings` table. Courses stored per-user (add `courses` column to `users` table, JSON array).

**Step 1: Add `courses` column to users table via migration**
**Step 2: Create settings controller**
**Step 3: Create API routes**
**Step 4: Create template and JS**
**Step 5: Commit**
```bash
git add templates/dashboard/settings.html static/js/dashboard/settings.js api/controllers/settings_controller.py db_helper.py
git commit -m "feat: create dashboard settings page"
```

---

## Phase 4: Student Portal Templates

### Task 4.1: Create Portal Base Template

**Files:**
- Create: `templates/portal/base.html`

Layout shell for all portal pages. Includes:
- Slim top bar: logo left ("Lumina"), theme toggle right
- Bottom nav (mobile): 3 tabs — Home, Attendance, Profile. Fixed bottom, 56px height. SVG icons (not Lucide library — inline SVGs for 3 icons).
- Desktop: bottom nav moves to horizontal top nav under header. Content max-width 640px centered.
- Links to design-system.css, Google Fonts, theme.js
- FOUC prevention script
- Toast container

Active tab determined by `request.path`.

**Step 1: Create the template**

**Step 2: Commit**
```bash
git add templates/portal/base.html
git commit -m "feat: create portal base template with bottom nav"
```

---

### Task 4.2: Create Portal Login/Signup Page

**Files:**
- Create: `templates/portal/login.html`
- Create: `static/js/portal/login.js`

Standalone (no base template — no nav for login).
Login/Signup tabs.
Signup: matric number, full name, email (optional), password.
Login: matric number, password.
On signup success: redirect to `/portal/enroll`.
On login success: redirect to `/portal/` (or `/portal/enroll` if not enrolled).

Mobile-first: full-width card, large inputs (44px min height), large buttons.
Match design system tokens.

**Step 1: Create template and JS**

**Step 2: Commit**
```bash
git add templates/portal/login.html static/js/portal/login.js
git commit -m "feat: create portal login/signup page"
```

---

### Task 4.3: Create Portal Enrollment (Onboarding) Page

**Files:**
- Create: `templates/portal/enroll.html`
- Create: `static/js/portal/enroll.js`

Full-screen onboarding flow (no bottom nav visible).
Reuses face capture logic from existing `face_processor.py` and camera system.

Steps:
1. Welcome + "Start Camera" button
2. Guided face capture (7 poses × 3 frames). Camera viewport large. Dot stepper (7 dots).
3. Academic details (level dropdown, courses input with chips)
4. Confirmation screen with summary

JS handles:
- Camera access via browser `getUserMedia` (NOT server MJPEG — student uses their own phone/laptop camera)
- Client-side face capture frames sent to server for processing
- Posts to `/api/portal/enroll` on completion

**IMPORTANT**: Unlike the lecturer's enrollment which uses server-side MJPEG, the student portal uses client-side camera (`getUserMedia`) since students use their own devices. Face frames are captured client-side and sent to the server API for encoding.

Use existing endpoints: `/api/public/process-face`, `/api/public/validate-pose`, `/api/public/process-guided-capture` — BUT move them under `/api/portal/` and add `@student_login_required`.

Actually — keep the face processing API under a shared prefix `/api/face/` since both dashboard and portal need face processing. Just add appropriate auth.

**Step 1: Create template and JS**
**Step 2: Commit**
```bash
git add templates/portal/enroll.html static/js/portal/enroll.js
git commit -m "feat: create portal enrollment onboarding flow"
```

---

### Task 4.4: Create Portal Home Page

**Files:**
- Create: `templates/portal/home.html`
- Create: `static/js/portal/home.js`

Extends `portal/base.html`.

Layout (per design doc section 4.4):
- Status card (teal tint): name, matric, enrollment status
- Today's attendance card (if active session exists for student's courses)
- Quick stats: attendance rate + courses enrolled (large numbers)
- Recent activity: last 5 attendance records as list

Fetches data from `GET /api/portal/home`.

**Step 1: Create template and JS**
**Step 2: Commit**
```bash
git add templates/portal/home.html static/js/portal/home.js
git commit -m "feat: create portal home page"
```

---

### Task 4.5: Create Portal Attendance Page

**Files:**
- Create: `templates/portal/attendance.html`
- Create: `static/js/portal/attendance.js`

Extends `portal/base.html`.

Layout (per design doc section 4.5):
- Course filter (adaptive pills/dropdown)
- Sticky summary bar with attendance rate
- Attendance list grouped by month, chronological
- Each entry: date, course, time, status pill
- Empty state

Fetches from `GET /api/portal/attendance?course=MTE411`.

**Step 1: Create template and JS**
**Step 2: Commit**
```bash
git add templates/portal/attendance.html static/js/portal/attendance.js
git commit -m "feat: create portal attendance page"
```

---

### Task 4.6: Create Portal Profile Page

**Files:**
- Create: `templates/portal/profile.html`
- Create: `static/js/portal/profile.js`

Extends `portal/base.html`.

Layout (per design doc section 4.6):
- Profile header with inline edit
- Courses as chips
- Level dropdown
- Face enrollment section with re-capture button
- Change password section
- Logout button

API calls:
- `GET /api/portal/profile`
- `PUT /api/portal/profile`
- `PUT /api/portal/face`
- `PUT /api/portal/password`
- `GET /api/portal/auth/logout`

**Step 1: Create template and JS**
**Step 2: Commit**
```bash
git add templates/portal/profile.html static/js/portal/profile.js
git commit -m "feat: create portal profile page"
```

---

## Phase 5: Cleanup & Integration

### Task 5.1: Remove Deprecated Files

**Files to delete:**
- `api/controllers/enrollment_link_controller.py`
- `api/controllers/public_enrollment_controller.py`
- `api/routes/enrollment_link_routes.py`
- `api/routes/public_enrollment_routes.py`
- `templates/public_enroll.html`
- `templates/enrollment_success.html`
- `templates/enroll.html` (replaced by dashboard enrollment if needed, or portal enrollment)
- `templates/index.html` (replaced by `templates/dashboard/index.html`)
- `templates/login.html` (replaced by `templates/dashboard/login.html`)
- `static/js/pages/enrollment.js` (replaced by portal/enroll.js)
- `static/js/pages/dashboard.js` (replaced by dashboard/session.js)

Keep `templates/base.html` temporarily until all pages are migrated, then delete.

**Step 1: Delete files**
**Step 2: Update any remaining imports in app.py**
**Step 3: Run tests to verify nothing breaks**
```bash
python -m pytest tests/ -v
```
**Step 4: Commit**
```bash
git add -A
git commit -m "refactor: remove deprecated templates and enrollment link system"
```

---

### Task 5.2: Update Tests

**Files:**
- Modify: `tests/test_sessions.py`
- Modify: `tests/test_api.py`
- Create: `tests/test_portal.py`

Update existing tests to work with new routes.
Add portal-specific tests:
- Student signup/login/logout
- Student enrollment flow
- Profile update
- Attendance retrieval
- Password change

**Step 1: Update existing tests for new route structure**
**Step 2: Write portal tests**
**Step 3: Run all tests**
```bash
python -m pytest tests/ -v
```
**Step 4: Commit**
```bash
git add tests/
git commit -m "test: update tests for new app structure and add portal tests"
```

---

### Task 5.3: Fix Conflicting Tailwind Class in enrollment_success.html

**Note:** This file is being deleted in Task 5.1. If it has already been deleted, skip this task. If it's still present for any reason, fix:

In `templates/enrollment_success.html` line 121, change:
```html
<p class="text-xs text-sm text-slate-400">
```
To:
```html
<p class="text-xs text-slate-400">
```

---

### Task 5.4: Final Integration Test

**Step 1: Start the server**
```bash
python app.py
```

**Step 2: Manual test checklist**

Dashboard:
- [ ] `/` redirects to `/dashboard/`
- [ ] `/dashboard/login` shows login page
- [ ] Sign up as lecturer, redirected to `/dashboard/`
- [ ] Live session page loads with camera feed placeholder
- [ ] Start session works with course selector
- [ ] Analytics page loads with charts
- [ ] Settings page loads and saves changes
- [ ] Logout redirects to `/dashboard/login`

Portal:
- [ ] `/portal/login` shows student login page
- [ ] Sign up as student, redirected to `/portal/enroll`
- [ ] Face capture onboarding flow works
- [ ] After enrollment, redirected to `/portal/`
- [ ] Home page shows status and stats
- [ ] Attendance page shows records
- [ ] Profile page allows editing
- [ ] Face re-capture works
- [ ] Logout redirects to `/portal/login`

Cross-app:
- [ ] Lecturer session started → student attendance appears in portal
- [ ] Theme toggle works on both apps
- [ ] Dark mode works on both apps
- [ ] Mobile responsive on both apps

**Step 3: Commit any final fixes**
```bash
git add -A
git commit -m "fix: integration test fixes"
```

---

## Task Dependency Graph

```
Phase 0 (Bug Fixes) — no dependencies, do first:
  0.1 → 0.2 → 0.3 → 0.4 → 0.5 → 0.6

Phase 1 (Foundation) — depends on Phase 0:
  1.1 (DB schema) → 1.2 (Design CSS) — can be parallel

Phase 2 (Structure) — depends on 1.1:
  2.1 (Blueprints) — depends on 1.1

Phase 3 (Dashboard) — depends on 1.2 + 2.1:
  3.1 (base) → 3.2 (login) → 3.3 (session) → 3.4 (analytics) → 3.5 (settings)

Phase 4 (Portal) — depends on 1.2 + 2.1:
  4.1 (base) → 4.2 (login) → 4.3 (enroll) → 4.4 (home) → 4.5 (attendance) → 4.6 (profile)

Phase 3 and Phase 4 can run in PARALLEL (independent template work).

Phase 5 (Cleanup) — depends on Phase 3 + Phase 4:
  5.1 (delete files) → 5.2 (tests) → 5.3 (fix) → 5.4 (integration)
```

Total: ~20 tasks across 6 phases.
