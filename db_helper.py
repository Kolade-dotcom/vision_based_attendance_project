"""
Database Helper Module
Handles all SQLite database operations for the attendance system.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
import json
import secrets

logger = logging.getLogger(__name__)

# Import configuration
try:
    import config
except ImportError:
    config = None


# Database file path (can be overridden for deployment/testing)
_DEFAULT_DATABASE_PATH = os.path.join(os.path.dirname(__file__), "database", "attendance.db")

if os.environ.get("DATABASE_PATH"):
    _DATABASE_PATH = os.environ["DATABASE_PATH"]
else:
    _DATABASE_PATH = _DEFAULT_DATABASE_PATH


def get_database_path():
    """Get the current database path."""
    return _DATABASE_PATH


def set_database_path(path):
    """Set the database path. Used for test isolation."""
    global _DATABASE_PATH
    _DATABASE_PATH = path


@contextmanager
def get_db_connection():
    """Context manager for database connection."""
    conn = sqlite3.connect(_DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize the database with schema and run migrations."""
    schema_path = os.path.join(os.path.dirname(__file__), "database", "schema.sql")

    with open(schema_path, "r") as f:
        schema = f.read()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if class_sessions table exists and needs migration
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='class_sessions'"
        )
        table_exists = cursor.fetchone() is not None

        if table_exists:
            # Check if user_id column exists
            cursor.execute("PRAGMA table_info(class_sessions)")
            columns = [info[1] for info in cursor.fetchall()]
            if "user_id" not in columns:
                # Add column with default value for existing records
                conn.execute(
                    "ALTER TABLE class_sessions ADD COLUMN user_id INTEGER DEFAULT 1"
                )
                logger.info("Migration: Added user_id column to class_sessions")

        # Check if students table needs migration for self-enrollment columns
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='students'"
        )
        students_exists = cursor.fetchone() is not None

        if students_exists:
            cursor.execute("PRAGMA table_info(students)")
            columns = [info[1] for info in cursor.fetchall()]

            if "status" not in columns:
                conn.execute(
                    "ALTER TABLE students ADD COLUMN status TEXT DEFAULT 'approved'"
                )
                logger.info("Migration: Added status column to students")

            if "enrolled_via_link_id" not in columns:
                conn.execute(
                    "ALTER TABLE students ADD COLUMN enrolled_via_link_id INTEGER"
                )
                logger.info("Migration: Added enrolled_via_link_id column to students")

            if "created_by" not in columns:
                conn.execute("ALTER TABLE students ADD COLUMN created_by INTEGER")
                logger.info("Migration: Added created_by column to students")

            if "rejection_reason" not in columns:
                conn.execute("ALTER TABLE students ADD COLUMN rejection_reason TEXT")
                logger.info("Migration: Added rejection_reason column to students")

        # Now execute the schema (CREATE IF NOT EXISTS won't modify existing tables)
        conn.executescript(schema)
        conn.commit()

    logger.info("Database initialized successfully!")


def create_session(course_code, user_id):
    """
    Start a new class session.
    Ensures only one active session per user exists.

    Args:
        course_code: The course code for this session
        user_id: The ID of the lecturer creating the session
    """
    start_time = datetime.now().isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # End any existing active sessions for this user
        cursor.execute(
            "UPDATE class_sessions SET is_active = 0, end_time = ? WHERE user_id = ? AND is_active = 1",
            (start_time, user_id),
        )

        cursor.execute(
            """
            INSERT INTO class_sessions (user_id, course_code, scheduled_start, start_time, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (user_id, course_code, start_time, start_time),
        )
        conn.commit()
        return cursor.lastrowid


def end_session(session_id):
    """End a specific session."""
    end_time = datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE class_sessions SET is_active = 0, end_time = ? WHERE id = ?",
            (end_time, session_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_session(session_id):
    """Delete a session and its associated attendance records."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Delete attendance records for this session first
        cursor.execute("DELETE FROM attendance WHERE session_id = ?", (session_id,))
        # Delete the session
        cursor.execute("DELETE FROM class_sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_active_session(user_id, course_code=None):
    """Get the currently active session for a specific user, optionally filtered by course."""
    query = "SELECT * FROM class_sessions WHERE is_active = 1 AND user_id = ?"
    params = [user_id]

    if course_code:
        query += " AND course_code = ?"
        params.append(course_code)

    query += " ORDER BY start_time DESC LIMIT 1"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def create_user(email, password_hash, name):
    """Create a new admin user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                (email, password_hash, name),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_user_by_email(email):
    """Get user by email."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def update_student(current_student_id, new_student_id, name, level=None, courses=None):
    """
    Update student details, including potential ID change.

    Args:
        current_student_id (str): The existing ID to find the student.
        new_student_id (str): The new ID (can be same as current).
        name (str): New Name
        level (str, optional): New Level
        courses (list, optional): New List of course codes
    """
    if courses is None:
        courses = []

    courses_json = json.dumps(courses)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # If ID is changing, we need to ensure new ID doesn't exist
        if current_student_id != new_student_id:
            cursor.execute(
                "SELECT 1 FROM students WHERE student_id = ?", (new_student_id,)
            )
            if cursor.fetchone():
                return False  # New ID already exists

            # Strategy:
            # 1. Update the student record (We need to disable FK constraints temporarily or use valid approaches)
            # Since SQLite FK support for ON UPDATE CASCADE is not enabled in our schema,
            # and disabling FKs is risky, we will use the Clone-Move-Delete approach or try direct update if constraints allow (they usually don't if children exist).

            # Actually, standard way if PRAGMA foreign_keys = ON:
            # You cannot update the parent key if children exist.
            # We must:
            # 1. Turn off FKs
            # 2. Update Student
            # 3. Update Attendance
            # 4. Turn on FKs

            try:
                cursor.execute("PRAGMA foreign_keys=OFF")

                cursor.execute(
                    """
                    UPDATE students 
                    SET student_id = ?, name = ?, level = ?, courses = ?
                    WHERE student_id = ?
                    """,
                    (new_student_id, name, level, courses_json, current_student_id),
                )

                if cursor.rowcount > 0:
                    cursor.execute(
                        "UPDATE attendance SET student_id = ? WHERE student_id = ?",
                        (new_student_id, current_student_id),
                    )
                    conn.commit()
                    return True
                return False
            finally:
                cursor.execute("PRAGMA foreign_keys=ON")

        else:
            # Simple update (ID not changing)
            cursor.execute(
                """
                UPDATE students 
                SET name = ?, level = ?, courses = ?
                WHERE student_id = ?
                """,
                (name, level, courses_json, current_student_id),
            )
            conn.commit()
            return cursor.rowcount > 0


def delete_student(student_id):
    """
    Delete a student from the database.

    Args:
        student_id (str): Student ID to delete
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # With ON DELETE CASCADE in schema, this might suffice, but explicit is safer
        cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()
        return cursor.rowcount > 0


def add_student(
    student_id,
    name,
    email=None,
    level=None,
    courses=None,
    face_encoding=None,
    status="approved",
    created_by=None,
    enrolled_via_link_id=None,
):
    """
    Add a new student to the database.

    Args:
        student_id (str): Unique Matric Number/ID
        name (str): Full Name
        email (str, optional): Email address
        level (str, optional): Student Level (e.g. "400")
        courses (list, optional): List of course codes
        face_encoding (bytes, optional): Serialized face encoding
        status (str): Enrollment status ('pending', 'approved', 'rejected')
        created_by (int, optional): User ID of lecturer who enrolled/approved
        enrolled_via_link_id (int, optional): ID of enrollment link used
    """
    if courses is None:
        courses = []

    # Serialize courses list to JSON string
    courses_json = json.dumps(courses)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO students (student_id, name, email, level, courses, face_encoding, 
                                      status, created_by, enrolled_via_link_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    name,
                    email,
                    level,
                    courses_json,
                    face_encoding,
                    status,
                    created_by,
                    enrolled_via_link_id,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.error(f"Student ID {student_id} already exists.")
            return None


def get_student(student_id):
    """Get student details by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_all_students(status_filter=None):
    """
    Get a list of all enrolled students.

    Args:
        status_filter (str, optional): Filter by status ('pending', 'approved', 'rejected')
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT student_id, name, email, level, courses, status, created_at FROM students"
        params = []

        if status_filter:
            query += " WHERE status = ?"
            params.append(status_filter)

        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_all_student_encodings():
    """
    Get all approved students' face encodings.
    Only approved students are included for attendance recognition.

    Returns:
        list: List of dicts with 'student_id', 'name', and 'face_encoding' (bytes)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT student_id, name, face_encoding FROM students "
            "WHERE face_encoding IS NOT NULL AND status = 'approved'"
        )
        return [dict(row) for row in cursor.fetchall()]


def record_attendance(student_id, status="present", course_code=None, level=None):
    """
    Record attendance for a student.

    Args:
        student_id (str): Student ID
        status (str): Attendance status
        course_code (str, optional): Course context for this attendance
        level (str, optional): Level context
    """

    session_id = None

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check active session
        active_session_query = (
            "SELECT id, start_time FROM class_sessions WHERE is_active = 1"
        )
        active_params = []
        if course_code:
            active_session_query += " AND course_code = ?"
            active_params.append(course_code)

        cursor.execute(
            active_session_query + " ORDER BY start_time DESC LIMIT 1", active_params
        )
        session_row = cursor.fetchone()
        if session_row:
            session_id = session_row["id"]
            # Check for late status based on session start_time
            # Grace period: students arriving within 15 minutes of session start are "present"
            # After 15 minutes from session start, they are marked "late"
            if session_row["start_time"]:
                session_start = datetime.fromisoformat(session_row["start_time"])
                current_time = datetime.now()
                # Use threshold from config or default to 15 minutes
                threshold_minutes = config.LATE_THRESHOLD_MINUTES if config else 15
                grace_period_seconds = threshold_minutes * 60

                if (
                    current_time - session_start
                ).total_seconds() > grace_period_seconds:
                    status = "late"

        # Check if student exists and get their enrolled courses
        cursor.execute(
            "SELECT id, name, level, courses FROM students WHERE student_id = ?",
            (student_id,),
        )
        student = cursor.fetchone()

        if not student:
            logger.error(f"Student {student_id} not found.")
            return None

        # Log the student we found for this ID
        logger.debug(
            f"record_attendance - DB lookup for ID '{student_id}' found student: '{student['name']}'"
        )

        # Check if student is enrolled in this course
        if course_code and student["courses"]:
            try:
                enrolled_courses = json.loads(student["courses"])
                if course_code not in enrolled_courses:
                    logger.info(
                        f"Student {student_id} is not enrolled in {course_code}. Courses: {enrolled_courses}. Skipping attendance."
                    )
                    return None
            except (json.JSONDecodeError, TypeError):
                # If courses is invalid JSON, skip validation
                logger.warning(f"Invalid courses JSON for student {student_id}")
                pass

        # If level is not passed, use student's level
        if not level and student["level"]:
            level = student["level"]

        # Check for existing attendance in this session to prevent duplicates
        if session_id:
            cursor.execute(
                "SELECT 1 FROM attendance WHERE session_id = ? AND student_id = ?",
                (session_id, student_id),
            )
            if cursor.fetchone():
                # Already marked present
                # print(f"DEBUG: Student {student_id} already marked present in session {session_id}")
                return None
        else:
            logger.debug(
                f"No active session found for course {course_code} when recording attendance"
            )
            # If no session ID, we might still record it if design allows, but usually we need a session.
            # Current logic records it with session_id=None if not found.
            pass

        cursor.execute(
            """
            INSERT INTO attendance (student_id, timestamp, status, course_code, level, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                datetime.now().isoformat(),
                status,
                course_code,
                level,
                session_id,
            ),
        )
        conn.commit()
        logger.debug(
            f"Successfully inserted attendance for {student_id} in session {session_id}"
        )
        return {"id": cursor.lastrowid, "status": status, "student_id": student_id}


def get_attendance_today(course_code=None, level=None):
    """
    Get all attendance records for today, optionally filtered.
    """
    start_of_day = datetime.now().strftime("%Y-%m-%dT00:00:00")

    query = """
        SELECT a.student_id, s.name as student_name, a.timestamp, a.status, a.course_code, a.level
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.timestamp >= ?
    """
    params = [start_of_day]

    if course_code:
        query += " AND a.course_code = ?"
        params.append(course_code)

    if level:
        query += " AND a.level = ?"
        params.append(level)

    query += " ORDER BY a.timestamp DESC"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_statistics(course_code=None, level=None):
    """
    Get attendance statistics for today, optionally filtered.
    """
    start_of_day = datetime.now().strftime("%Y-%m-%dT00:00:00")

    # Base WHERE clause
    where_clause = "WHERE timestamp >= ?"
    params = [start_of_day]

    if course_code:
        where_clause += " AND course_code = ?"
        params.append(course_code)

    if level:
        where_clause += " AND level = ?"
        params.append(level)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Total present
        cursor.execute(
            f"SELECT COUNT(*) FROM attendance {where_clause} AND status = 'present'",
            params,
        )
        present_count = cursor.fetchone()[0]

        # Total late
        cursor.execute(
            f"SELECT COUNT(*) FROM attendance {where_clause} AND status = 'late'",
            params,
        )
        late_count = cursor.fetchone()[0]

        # Total students (filtered by level if provided, otherwise all)
        student_query = "SELECT COUNT(*) FROM students"
        student_params = []

        if level:
            student_query += " WHERE level = ?"
            student_params.append(level)

        cursor.execute(student_query, student_params)
        total_students = cursor.fetchone()[0]

        return {
            "present_today": present_count,
            "late_today": late_count,
            "total_students": total_students,
        }


def get_session_history(user_id):
    """
    Get all past (inactive) sessions for a specific user, ordered by start time descending.

    Args:
        user_id: The ID of the lecturer whose sessions to retrieve.

    Returns:
        list: List of session dictionaries.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, course_code, scheduled_start, start_time, end_time, is_active
            FROM class_sessions
            WHERE is_active = 0 AND user_id = ?
            ORDER BY start_time DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_session_attendance(session_id):
    """
    Get all attendance records for a specific session.

    Args:
        session_id: The ID of the session.

    Returns:
        list: List of attendance record dictionaries.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.student_id, s.name as student_name, a.timestamp, a.status, a.course_code
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.session_id = ?
            ORDER BY a.timestamp DESC
            """,
            (session_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_attendance_for_active_session(user_id):
    """
    Get attendance records for the currently active session.

    Args:
        user_id: The ID of the user whose active session to query.

    Returns:
        list: List of attendance record dictionaries, or empty list if no active session.
    """
    active_session = get_active_session(user_id)
    if not active_session:
        return []

    return get_session_attendance(active_session["id"])


# ============================================================================
# Enrollment Link Functions
# ============================================================================


def create_enrollment_link(
    user_id,
    course_code=None,
    level=None,
    description=None,
    expires_hours=48,
    max_uses=None,
):
    """
    Create a new enrollment link for self-service student enrollment.

    Args:
        user_id: ID of the lecturer creating the link
        course_code: Optional course to pre-fill
        level: Optional level to pre-fill
        description: Optional description/name for the link
        expires_hours: Hours until link expires (default 48)
        max_uses: Maximum number of uses (None = unlimited)

    Returns:
        dict: Created link details including token
    """
    token = secrets.token_urlsafe(24)  # 192 bits of entropy
    expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO enrollment_links 
            (token, created_by, course_code, level, description, max_uses, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (token, user_id, course_code, level, description, max_uses, expires_at),
        )
        conn.commit()
        return {
            "id": cursor.lastrowid,
            "token": token,
            "course_code": course_code,
            "level": level,
            "description": description,
            "max_uses": max_uses,
            "expires_at": expires_at,
            "created_by": user_id,
        }


def validate_enrollment_link(token):
    """
    Validate an enrollment link token.

    Args:
        token: The enrollment link token

    Returns:
        dict: Link details if valid, None if invalid/expired/exhausted
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, token, created_by, course_code, level, description,
                   max_uses, current_uses, expires_at, is_active
            FROM enrollment_links
            WHERE token = ?
            """,
            (token,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        link = dict(row)

        # Check if active
        if not link["is_active"]:
            return None

        # Check expiration
        expires_at = datetime.fromisoformat(link["expires_at"])
        if datetime.now() > expires_at:
            return None

        # Check usage limit
        if link["max_uses"] is not None and link["current_uses"] >= link["max_uses"]:
            return None

        return link


def increment_link_usage(token):
    """
    Increment the usage count for an enrollment link.

    Args:
        token: The enrollment link token

    Returns:
        bool: True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE enrollment_links SET current_uses = current_uses + 1 WHERE token = ?",
            (token,),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_user_enrollment_links(user_id):
    """
    Get all enrollment links created by a user.

    Args:
        user_id: The ID of the lecturer

    Returns:
        list: List of enrollment link dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, token, course_code, level, description, max_uses, 
                   current_uses, expires_at, is_active, created_at
            FROM enrollment_links
            WHERE created_by = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def revoke_enrollment_link(link_id, user_id):
    """
    Revoke (deactivate) an enrollment link.

    Args:
        link_id: The ID of the link to revoke
        user_id: The ID of the user (for authorization check)

    Returns:
        bool: True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE enrollment_links SET is_active = 0 WHERE id = ? AND created_by = ?",
            (link_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_enrollment_link(link_id, user_id):
    """
    Delete an enrollment link.

    Args:
        link_id: The ID of the link to delete
        user_id: The ID of the user (for authorization check)

    Returns:
        bool: True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM enrollment_links WHERE id = ? AND created_by = ?",
            (link_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# Student Approval Workflow Functions
# ============================================================================


def approve_student(student_id, user_id):
    """
    Approve a pending student enrollment.

    Args:
        student_id: The student's matric number/ID
        user_id: The ID of the approving lecturer

    Returns:
        bool: True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE students 
            SET status = 'approved', created_by = ?, updated_at = ?
            WHERE student_id = ? AND status = 'pending'
            """,
            (user_id, datetime.now().isoformat(), student_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def reject_student(student_id, user_id, reason=None):
    """
    Reject a pending student enrollment.

    Args:
        student_id: The student's matric number/ID
        user_id: The ID of the rejecting lecturer
        reason: Optional rejection reason

    Returns:
        bool: True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE students 
            SET status = 'rejected', created_by = ?, rejection_reason = ?, updated_at = ?
            WHERE student_id = ? AND status = 'pending'
            """,
            (user_id, reason, datetime.now().isoformat(), student_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_pending_students_count():
    """
    Get count of pending student enrollments.

    Returns:
        int: Number of pending students
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'pending'")
        return cursor.fetchone()[0]


if __name__ == "__main__":
    # Test database operations
    logger.info("Testing database module...")

    # Initialize database
    init_database()
