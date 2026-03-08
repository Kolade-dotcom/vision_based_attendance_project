"""
Database Helper Module
Handles all database operations for the attendance system.
Supports PostgreSQL (via DATABASE_URL env var) and SQLite (fallback).
"""

import sqlite3
import logging
from datetime import datetime, timedelta, timezone
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

# PostgreSQL support: if DATABASE_URL is set, use PostgreSQL; otherwise SQLite
DATABASE_URL = os.environ.get("DATABASE_URL")
_USE_POSTGRES = DATABASE_URL is not None

if _USE_POSTGRES:
    import psycopg2
    import psycopg2.extras


# Database file path (can be overridden for deployment/testing) — SQLite only
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


def _q(sql):
    """Convert ? placeholders to %s for PostgreSQL."""
    if _USE_POSTGRES:
        return sql.replace("?", "%s")
    return sql


@contextmanager
def get_db_connection():
    """Context manager for database connection."""
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


def _init_postgres():
    """Initialize PostgreSQL database with schema."""
    schema_path = os.path.join(os.path.dirname(__file__), "database", "schema_postgres.sql")

    with open(schema_path, "r") as f:
        schema = f.read()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(schema)
        conn.commit()

    # Run migrations for existing PostgreSQL databases
    _migrate_postgres()

    logger.info("PostgreSQL database initialized successfully!")


def _migrate_postgres():
    """Run migrations for existing PostgreSQL databases."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Add equivalent_courses column to class_sessions if missing
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'class_sessions' AND column_name = 'equivalent_courses'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE class_sessions ADD COLUMN equivalent_courses TEXT")
            logger.info("Migration: Added equivalent_courses column to class_sessions (PostgreSQL)")

        # Add unique index to prevent duplicate attendance per student per session
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_unique_session_student
            ON attendance(session_id, student_id) WHERE session_id IS NOT NULL
        """)

        conn.commit()


def _init_sqlite():
    """Initialize SQLite database with schema and run migrations."""
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
                conn.execute(
                    "ALTER TABLE class_sessions ADD COLUMN user_id INTEGER DEFAULT 1"
                )
                logger.info("Migration: Added user_id column to class_sessions")

            if "equivalent_courses" not in columns:
                conn.execute(
                    "ALTER TABLE class_sessions ADD COLUMN equivalent_courses TEXT"
                )
                logger.info("Migration: Added equivalent_courses column to class_sessions")

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

            if "password_hash" not in columns:
                conn.execute("ALTER TABLE students ADD COLUMN password_hash TEXT")
                logger.info("Migration: Added password_hash column to students")

            if "is_enrolled" not in columns:
                conn.execute("ALTER TABLE students ADD COLUMN is_enrolled INTEGER DEFAULT 0")
                logger.info("Migration: Added is_enrolled column to students")

        # Check if users table needs courses column
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        users_exists = cursor.fetchone() is not None

        if users_exists:
            cursor.execute("PRAGMA table_info(users)")
            user_columns = [info[1] for info in cursor.fetchall()]
            if "courses" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN courses TEXT")
                logger.info("Migration: Added courses column to users")

        # Now execute the schema (CREATE IF NOT EXISTS won't modify existing tables)
        conn.executescript(schema)
        conn.commit()

    logger.info("SQLite database initialized successfully!")


def init_database():
    """Initialize the database with schema and run migrations."""
    if _USE_POSTGRES:
        _init_postgres()
    else:
        _init_sqlite()


def create_session(course_code, user_id, equivalent_courses=None):
    """
    Start a new class session.
    Ensures only one active session per user exists.

    Args:
        course_code: The course code for this session
        user_id: The ID of the lecturer creating the session
        equivalent_courses: Optional list of equivalent course codes
    """
    start_time = datetime.now(timezone.utc).isoformat()
    equiv_json = json.dumps(equivalent_courses) if equivalent_courses else None

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # End any existing active sessions for this user
        cursor.execute(
            _q("UPDATE class_sessions SET is_active = 0, end_time = ? WHERE user_id = ? AND is_active = 1"),
            (start_time, user_id),
        )

        if _USE_POSTGRES:
            cursor.execute(
                _q("""
                INSERT INTO class_sessions (user_id, course_code, scheduled_start, start_time, is_active, equivalent_courses)
                VALUES (?, ?, ?, ?, 1, ?) RETURNING id
                """),
                (user_id, course_code, start_time, start_time, equiv_json),
            )
            new_id = cursor.fetchone()["id"]
            conn.commit()
        else:
            cursor.execute(
                """
                INSERT INTO class_sessions (user_id, course_code, scheduled_start, start_time, is_active, equivalent_courses)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (user_id, course_code, start_time, start_time, equiv_json),
            )
            conn.commit()
            new_id = cursor.lastrowid
        return new_id


def end_session(session_id):
    """End a specific session."""
    end_time = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("UPDATE class_sessions SET is_active = 0, end_time = ? WHERE id = ?"),
            (end_time, session_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_session(session_id):
    """Delete a session and its associated attendance records."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Delete attendance records for this session first
        cursor.execute(_q("DELETE FROM attendance WHERE session_id = ?"), (session_id,))
        # Delete the session
        cursor.execute(_q("DELETE FROM class_sessions WHERE id = ?"), (session_id,))
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
        cursor.execute(_q(query), params)
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def create_user(email, password_hash, name):
    """Create a new admin user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if _USE_POSTGRES:
                cursor.execute(
                    _q("INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?) RETURNING id"),
                    (email, password_hash, name),
                )
                new_id = cursor.fetchone()["id"]
                conn.commit()
                return new_id
            else:
                cursor.execute(
                    "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                    (email, password_hash, name),
                )
                conn.commit()
                return cursor.lastrowid
        except (sqlite3.IntegrityError, Exception) as e:
            if _USE_POSTGRES:
                conn.rollback()
            if "UNIQUE" in str(e).upper() or "unique" in str(e).lower() or isinstance(e, sqlite3.IntegrityError):
                return None
            raise


def get_user_by_email(email):
    """Get user by email."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_q("SELECT * FROM users WHERE email = ?"), (email,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_user_settings(user_id):
    """Get user settings including courses and system settings."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_q("SELECT * FROM users WHERE id = ?"), (user_id,))
        user = cursor.fetchone()
        settings = {}
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        for row in rows:
            settings[row["key"]] = row["value"]

        courses = json.loads(user["courses"]) if user and user["courses"] else []
        return {
            "user": {
                "name": user["name"] if user else "",
                "email": user["email"] if user else "",
                "courses": courses,
            },
            "late_threshold_minutes": int(settings.get("late_threshold_minutes", 15)),
            "camera_source": settings.get("camera_source", "auto"),
            "esp32_ip": settings.get("esp32_ip", "192.168.1.100"),
        }


def update_user_settings(user_id, data):
    """Update user settings."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        if _USE_POSTGRES:
            upsert_sql = _q(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at"
            )
        else:
            upsert_sql = "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)"
        if "late_threshold_minutes" in data:
            cursor.execute(
                upsert_sql,
                ("late_threshold_minutes", str(data["late_threshold_minutes"]), now),
            )
        if "camera_source" in data:
            cursor.execute(
                upsert_sql,
                ("camera_source", data["camera_source"], now),
            )
        if "esp32_ip" in data:
            cursor.execute(
                upsert_sql,
                ("esp32_ip", data["esp32_ip"], now),
            )
        if "courses" in data:
            courses_json = (
                json.dumps(data["courses"])
                if isinstance(data["courses"], list)
                else data["courses"]
            )
            cursor.execute(
                _q("UPDATE users SET courses = ? WHERE id = ?"), (courses_json, user_id)
            )
        conn.commit()


def update_user_account(user_id, name=None, email=None):
    """Update user account info."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if name:
            cursor.execute(_q("UPDATE users SET name = ? WHERE id = ?"), (name, user_id))
        if email:
            cursor.execute(_q("UPDATE users SET email = ? WHERE id = ?"), (email, user_id))
        conn.commit()


def update_user_password(user_id, password_hash):
    """Update user password."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("UPDATE users SET password_hash = ? WHERE id = ?"),
            (password_hash, user_id),
        )
        conn.commit()


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
                _q("SELECT 1 FROM students WHERE student_id = ?"), (new_student_id,)
            )
            if cursor.fetchone():
                return False  # New ID already exists

            if _USE_POSTGRES:
                cursor.execute(
                    _q("""
                    UPDATE students
                    SET student_id = ?, name = ?, level = ?, courses = ?
                    WHERE student_id = ?
                    """),
                    (new_student_id, name, level, courses_json, current_student_id),
                )

                if cursor.rowcount > 0:
                    cursor.execute(
                        _q("UPDATE attendance SET student_id = ? WHERE student_id = ?"),
                        (new_student_id, current_student_id),
                    )
                    conn.commit()
                    return True
                return False
            else:
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
                _q("""
                UPDATE students
                SET name = ?, level = ?, courses = ?
                WHERE student_id = ?
                """),
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
        cursor.execute(_q("DELETE FROM attendance WHERE student_id = ?"), (student_id,))
        cursor.execute(_q("DELETE FROM students WHERE student_id = ?"), (student_id,))
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
            if _USE_POSTGRES:
                cursor.execute(
                    _q("""
                    INSERT INTO students (student_id, name, email, level, courses, face_encoding,
                                          status, created_by, enrolled_via_link_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
                    """),
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
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                new_id = cursor.fetchone()["id"]
                conn.commit()
                return new_id
            else:
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
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
                return cursor.lastrowid
        except (sqlite3.IntegrityError, Exception) as e:
            if _USE_POSTGRES:
                conn.rollback()
            if "UNIQUE" in str(e).upper() or "unique" in str(e).lower() or isinstance(e, sqlite3.IntegrityError):
                logger.error(f"Student ID {student_id} already exists.")
                return None
            raise


def get_student(student_id):
    """Get student details by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_q("SELECT * FROM students WHERE student_id = ?"), (student_id,))
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
        cursor.execute(_q(query), params)
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
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            encoding_data = d["face_encoding"]
            if isinstance(encoding_data, memoryview):
                d["face_encoding"] = bytes(encoding_data)
            results.append(d)
        return results


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
            _q(active_session_query + " ORDER BY start_time DESC LIMIT 1"), active_params
        )
        session_row = cursor.fetchone()
        if session_row:
            session_id = session_row["id"]
            # Check for late status based on session start_time
            # Grace period: students arriving within 15 minutes of session start are "present"
            # After 15 minutes from session start, they are marked "late"
            if session_row["start_time"]:
                session_start = datetime.fromisoformat(session_row["start_time"])
                # Ensure session_start is timezone-aware for comparison
                if session_start.tzinfo is None:
                    session_start = session_start.replace(tzinfo=timezone.utc)
                current_time = datetime.now(timezone.utc)
                # Use threshold from config or default to 15 minutes
                threshold_minutes = config.LATE_THRESHOLD_MINUTES if config else 15
                grace_period_seconds = threshold_minutes * 60

                if (
                    current_time - session_start
                ).total_seconds() > grace_period_seconds:
                    status = "late"

        # Check if student exists and get their enrolled courses
        cursor.execute(
            _q("SELECT id, name, level, courses FROM students WHERE student_id = ?"),
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

        # Check if student is enrolled in this course (or equivalent courses)
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
                    logger.info(
                        f"Student {student_id} not enrolled in {course_code} or equivalents {accepted_courses}. "
                        f"Courses: {enrolled_courses}. Recording as not_enrolled."
                    )
                    status = "not_enrolled"
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid courses JSON for student {student_id}")

        # If level is not passed, use student's level
        if not level and student["level"]:
            level = student["level"]

        # Check for existing attendance in this session to prevent duplicates
        if session_id:
            cursor.execute(
                _q("SELECT 1 FROM attendance WHERE session_id = ? AND student_id = ?"),
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

        if _USE_POSTGRES:
            cursor.execute(
                _q("""
                INSERT INTO attendance (student_id, timestamp, status, course_code, level, session_id)
                VALUES (?, ?, ?, ?, ?, ?) RETURNING id
                """),
                (
                    student_id,
                    datetime.now(timezone.utc).isoformat(),
                    status,
                    course_code,
                    level,
                    session_id,
                ),
            )
            new_id = cursor.fetchone()["id"]
            conn.commit()
        else:
            cursor.execute(
                """
                INSERT INTO attendance (student_id, timestamp, status, course_code, level, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    datetime.now(timezone.utc).isoformat(),
                    status,
                    course_code,
                    level,
                    session_id,
                ),
            )
            conn.commit()
            new_id = cursor.lastrowid
        logger.debug(
            f"Successfully inserted attendance for {student_id} in session {session_id}"
        )
        return {
            "id": new_id,
            "status": status,
            "student_id": student_id,
            "student_name": student["name"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


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


def get_attendance_today(course_code=None, level=None):
    """
    Get all attendance records for today, optionally filtered.
    """
    start_of_day = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")

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
        cursor.execute(_q(query), params)
        return [dict(row) for row in cursor.fetchall()]


def get_statistics(course_code=None, level=None):
    """
    Get attendance statistics for today, optionally filtered.
    """
    start_of_day = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")

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
            _q(f"SELECT COUNT(*) as cnt FROM attendance {where_clause} AND status = 'present'"),
            params,
        )
        present_count = cursor.fetchone()["cnt"]

        # Total late
        cursor.execute(
            _q(f"SELECT COUNT(*) as cnt FROM attendance {where_clause} AND status = 'late'"),
            params,
        )
        late_count = cursor.fetchone()["cnt"]

        # Total students (filtered by level if provided, otherwise all)
        student_query = "SELECT COUNT(*) as cnt FROM students"
        student_params = []

        if level:
            student_query += " WHERE level = ?"
            student_params.append(level)

        cursor.execute(_q(student_query), student_params)
        total_students = cursor.fetchone()["cnt"]

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
            _q("""
            SELECT id, course_code, scheduled_start, start_time, end_time, is_active
            FROM class_sessions
            WHERE is_active = 0 AND user_id = ?
            ORDER BY start_time DESC
            """),
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
            _q("""
            SELECT a.student_id, s.name as student_name, a.timestamp, a.status, a.course_code
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.session_id = ?
            ORDER BY a.timestamp DESC
            """),
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
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=expires_hours)).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if _USE_POSTGRES:
            cursor.execute(
                _q("""
                INSERT INTO enrollment_links
                (token, created_by, course_code, level, description, max_uses, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id
                """),
                (token, user_id, course_code, level, description, max_uses, expires_at),
            )
            new_id = cursor.fetchone()["id"]
            conn.commit()
        else:
            cursor.execute(
                """
                INSERT INTO enrollment_links
                (token, created_by, course_code, level, description, max_uses, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (token, user_id, course_code, level, description, max_uses, expires_at),
            )
            conn.commit()
            new_id = cursor.lastrowid
        return {
            "id": new_id,
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
            _q("""
            SELECT id, token, created_by, course_code, level, description,
                   max_uses, current_uses, expires_at, is_active
            FROM enrollment_links
            WHERE token = ?
            """),
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
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
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
            _q("UPDATE enrollment_links SET current_uses = current_uses + 1 WHERE token = ?"),
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
            _q("""
            SELECT id, token, course_code, level, description, max_uses,
                   current_uses, expires_at, is_active, created_at
            FROM enrollment_links
            WHERE created_by = ?
            ORDER BY created_at DESC
            """),
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
            _q("UPDATE enrollment_links SET is_active = 0 WHERE id = ? AND created_by = ?"),
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
            _q("DELETE FROM enrollment_links WHERE id = ? AND created_by = ?"),
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
            _q("""
            UPDATE students
            SET status = 'approved', created_by = ?, updated_at = ?
            WHERE student_id = ? AND status = 'pending'
            """),
            (user_id, datetime.now(timezone.utc).isoformat(), student_id),
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
            _q("""
            UPDATE students
            SET status = 'rejected', created_by = ?, rejection_reason = ?, updated_at = ?
            WHERE student_id = ? AND status = 'pending'
            """),
            (user_id, reason, datetime.now(timezone.utc).isoformat(), student_id),
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
        cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE status = 'pending'")
        return cursor.fetchone()["cnt"]


# ============================================================================
# Student Portal Auth & Profile Functions
# ============================================================================


def get_student_by_matric(matric_number):
    """Get student by matric number (student_id)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("SELECT * FROM students WHERE student_id = ?"), (matric_number,)
        )
        student = cursor.fetchone()
        return dict(student) if student else None


def create_student_account(matric_number, name, email, password_hash):
    """Create a student account (no face encoding yet)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        if _USE_POSTGRES:
            cursor.execute(
                _q("""INSERT INTO students (student_id, name, email, password_hash, status, is_enrolled, created_at)
                   VALUES (?, ?, ?, ?, 'approved', 0, ?) RETURNING id"""),
                (matric_number, name, email, password_hash, now),
            )
            new_id = cursor.fetchone()["id"]
            conn.commit()
            return new_id
        else:
            cursor.execute(
                """INSERT INTO students (student_id, name, email, password_hash, status, is_enrolled, created_at)
                   VALUES (?, ?, ?, ?, 'approved', 0, ?)""",
                (matric_number, name, email, password_hash, now),
            )
            conn.commit()
            return cursor.lastrowid


def update_student_enrollment(student_id, face_encoding, level, courses):
    """Mark student as enrolled with face encoding and academic details."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        courses_json = json.dumps(courses) if isinstance(courses, list) else courses
        cursor.execute(
            _q("""UPDATE students
               SET face_encoding = ?, level = ?, courses = ?, is_enrolled = 1, updated_at = ?
               WHERE student_id = ?"""),
            (face_encoding, level, courses_json, datetime.now(timezone.utc).isoformat(), student_id),
        )
        conn.commit()


def get_student_attendance(student_id, course_code=None):
    """Get attendance records for a student, optionally filtered by course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if course_code:
            cursor.execute(
                _q("""SELECT a.*, cs.course_code as session_course, cs.start_time as session_start
                   FROM attendance a
                   JOIN class_sessions cs ON a.session_id = cs.id
                   WHERE a.student_id = ? AND a.course_code = ?
                   ORDER BY a.timestamp DESC"""),
                (student_id, course_code),
            )
        else:
            cursor.execute(
                _q("""SELECT a.*, cs.course_code as session_course, cs.start_time as session_start
                   FROM attendance a
                   JOIN class_sessions cs ON a.session_id = cs.id
                   WHERE a.student_id = ?
                   ORDER BY a.timestamp DESC"""),
                (student_id,),
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_student_attendance_stats(student_id, course_code=None):
    """Get attendance stats for a student, scoped to their enrolled courses."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if course_code:
            cursor.execute(
                _q("""SELECT COUNT(DISTINCT cs.id) as cnt FROM class_sessions cs
                   WHERE cs.course_code = ? AND cs.is_active = 0"""),
                (course_code,),
            )
            total = cursor.fetchone()["cnt"]
            cursor.execute(
                _q("""SELECT COUNT(*) as cnt FROM attendance
                   WHERE student_id = ? AND course_code = ? AND status = 'present'"""),
                (student_id, course_code),
            )
            present = cursor.fetchone()["cnt"]
            cursor.execute(
                _q("""SELECT COUNT(*) as cnt FROM attendance
                   WHERE student_id = ? AND course_code = ? AND status = 'late'"""),
                (student_id, course_code),
            )
            late = cursor.fetchone()["cnt"]
        else:
            student = get_student_by_matric(student_id)
            courses = json.loads(student["courses"]) if student and student.get("courses") else []
            if courses:
                placeholders = ",".join(["?"] * len(courses))
                cursor.execute(
                    _q(f"SELECT COUNT(*) as cnt FROM class_sessions WHERE is_active = 0 AND course_code IN ({placeholders})"),
                    tuple(courses),
                )
            else:
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM class_sessions WHERE is_active = 0"
                )
            total = cursor.fetchone()["cnt"]
            cursor.execute(
                _q("SELECT COUNT(*) as cnt FROM attendance WHERE student_id = ? AND status = 'present'"),
                (student_id,),
            )
            present = cursor.fetchone()["cnt"]
            cursor.execute(
                _q("SELECT COUNT(*) as cnt FROM attendance WHERE student_id = ? AND status = 'late'"),
                (student_id,),
            )
            late = cursor.fetchone()["cnt"]

        attended = present + late
        rate = round((attended / total) * 100, 1) if total > 0 else 0
        return {
            "total_sessions": total,
            "present": present,
            "late": late,
            "absent": total - attended,
            "attendance_rate": rate,
        }


def update_student_profile(student_id, name=None, email=None, level=None, courses=None):
    """Update student profile fields."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
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
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(student_id)

        cursor.execute(
            _q(f"UPDATE students SET {', '.join(updates)} WHERE student_id = ?"),
            params,
        )
        conn.commit()
        return True


def update_student_face(student_id, face_encoding):
    """Update student face encoding (re-capture)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("UPDATE students SET face_encoding = ?, updated_at = ? WHERE student_id = ?"),
            (face_encoding, datetime.now(timezone.utc).isoformat(), student_id),
        )
        conn.commit()


def update_student_password(student_id, password_hash):
    """Update student password."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("UPDATE students SET password_hash = ?, updated_at = ? WHERE student_id = ?"),
            (password_hash, datetime.now(timezone.utc).isoformat(), student_id),
        )
        conn.commit()


def get_active_session_by_course(course_code):
    """Get active session for a specific course (any lecturer)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("SELECT * FROM class_sessions WHERE course_code = ? AND is_active = 1"),
            (course_code,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_student_session_attendance(student_id, session_id):
    """Get a student's attendance record for a specific session."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("SELECT * FROM attendance WHERE student_id = ? AND session_id = ?"),
            (student_id, session_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# ============================================================================
# Analytics Functions
# ============================================================================


def get_attendance_trend(user_id, course_code=None, limit=10):
    """Get attendance rate per session for last N sessions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if course_code:
            cursor.execute(
                _q("""SELECT cs.id, cs.course_code, cs.start_time,
                          COUNT(DISTINCT a.student_id) as attended,
                          (SELECT COUNT(*) FROM students WHERE is_enrolled = 1
                           AND courses LIKE '%' || cs.course_code || '%') as total
                   FROM class_sessions cs
                   LEFT JOIN attendance a ON cs.id = a.session_id
                   WHERE cs.user_id = ? AND cs.is_active = 0 AND cs.course_code = ?
                   GROUP BY cs.id, cs.course_code, cs.start_time
                   ORDER BY cs.start_time DESC
                   LIMIT ?"""),
                (user_id, course_code, limit),
            )
        else:
            cursor.execute(
                _q("""SELECT cs.id, cs.course_code, cs.start_time,
                          COUNT(DISTINCT a.student_id) as attended,
                          (SELECT COUNT(*) FROM students WHERE is_enrolled = 1
                           AND courses LIKE '%' || cs.course_code || '%') as total
                   FROM class_sessions cs
                   LEFT JOIN attendance a ON cs.id = a.session_id
                   WHERE cs.user_id = ? AND cs.is_active = 0
                   GROUP BY cs.id, cs.course_code, cs.start_time
                   ORDER BY cs.start_time DESC
                   LIMIT ?"""),
                (user_id, limit),
            )
        sessions = cursor.fetchall()

        result = []
        for s in sessions:
            total = s["total"] if s["total"] > 0 else 1
            rate = round((s["attended"] / total) * 100, 1)
            result.append(
                {
                    "session_id": s["id"],
                    "course_code": s["course_code"],
                    "date": s["start_time"],
                    "attended": s["attended"],
                    "total": total,
                    "rate": rate,
                }
            )
        return list(reversed(result))


def get_student_leaderboard(user_id, course_code=None, limit=50):
    """Get students ranked by attendance rate, scoped to lecturer's sessions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if course_code:
            cursor.execute(
                _q("SELECT COUNT(*) as cnt FROM class_sessions WHERE user_id = ? AND course_code = ? AND is_active = 0"),
                (user_id, course_code),
            )
            total_sessions = cursor.fetchone()["cnt"]

            cursor.execute(
                _q("""SELECT s.student_id, s.name, s.level,
                          COUNT(a.id) as attended
                   FROM students s
                   LEFT JOIN attendance a ON s.student_id = a.student_id AND a.course_code = ?
                   WHERE s.is_enrolled = 1 AND s.courses LIKE ?
                   GROUP BY s.student_id, s.name, s.level
                   ORDER BY attended DESC
                   LIMIT ?"""),
                (course_code, f"%{course_code}%", limit),
            )
            students = cursor.fetchall()
        else:
            cursor.execute(
                _q("""SELECT s.student_id, s.name, s.level,
                          COUNT(a.id) as attended,
                          (SELECT COUNT(*) FROM class_sessions cs
                           WHERE cs.user_id = ? AND cs.is_active = 0
                           AND s.courses LIKE '%' || cs.course_code || '%') as total_sessions
                   FROM students s
                   LEFT JOIN attendance a ON s.student_id = a.student_id
                       AND a.session_id IN (SELECT id FROM class_sessions WHERE user_id = ?)
                   WHERE s.is_enrolled = 1
                   AND EXISTS (SELECT 1 FROM class_sessions cs
                               WHERE cs.user_id = ? AND cs.is_active = 0
                               AND s.courses LIKE '%' || cs.course_code || '%')
                   GROUP BY s.student_id, s.name, s.level
                   ORDER BY attended DESC
                   LIMIT ?"""),
                (user_id, user_id, user_id, limit),
            )
            students = cursor.fetchall()

            result = []
            for st in students:
                total = st["total_sessions"]
                rate = (
                    round((st["attended"] / total) * 100, 1)
                    if total > 0
                    else 0
                )
                result.append(
                    {
                        "student_id": st["student_id"],
                        "name": st["name"],
                        "level": st["level"],
                        "attended": st["attended"],
                        "total_sessions": total,
                        "rate": rate,
                    }
                )
            return result

        result = []
        for st in students:
            rate = (
                round((st["attended"] / total_sessions) * 100, 1)
                if total_sessions > 0
                else 0
            )
            result.append(
                {
                    "student_id": st["student_id"],
                    "name": st["name"],
                    "level": st["level"],
                    "attended": st["attended"],
                    "total_sessions": total_sessions,
                    "rate": rate,
                }
            )
        return result


def get_lecturer_courses(user_id):
    """Get course codes from lecturer settings, student enrollments, and past sessions.

    Priority order: lecturer's own courses first, then student enrollments,
    then past session courses. Duplicates are removed preserving priority order.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        courses = []
        seen = set()

        # 1. Lecturer's own configured courses (highest priority)
        cursor.execute(
            _q("SELECT courses FROM users WHERE id = ?"), (user_id,)
        )
        user = cursor.fetchone()
        if user and user["courses"]:
            try:
                lecturer_courses = json.loads(user["courses"])
                for c in lecturer_courses:
                    if c and c not in seen:
                        courses.append(c)
                        seen.add(c)
            except (json.JSONDecodeError, TypeError):
                pass

        # 2. Courses from enrolled students
        cursor.execute(
            "SELECT DISTINCT courses FROM students WHERE is_enrolled = 1 AND courses IS NOT NULL AND courses != ''"
        )
        rows = cursor.fetchall()
        for row in rows:
            try:
                student_courses = json.loads(row["courses"])
                for c in student_courses:
                    if c and c not in seen:
                        courses.append(c)
                        seen.add(c)
            except (json.JSONDecodeError, TypeError):
                pass

        # 3. Past session courses
        cursor.execute(
            _q("SELECT DISTINCT course_code FROM class_sessions WHERE user_id = ? ORDER BY course_code"),
            (user_id,),
        )
        session_rows = cursor.fetchall()
        for row in session_rows:
            c = row["course_code"]
            if c and c not in seen:
                courses.append(c)
                seen.add(c)

        return courses


def get_recent_session_courses(user_id, limit=2):
    """Get the most recently used course codes for quick-start."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _q("""SELECT course_code, MAX(start_time) as last_used
               FROM class_sessions
               WHERE user_id = ?
               GROUP BY course_code
               ORDER BY last_used DESC
               LIMIT ?"""),
            (user_id, limit),
        )
        rows = cursor.fetchall()
        return [row["course_code"] for row in rows]


def search_all_course_codes(query, student_level=None, limit=8):
    """Search all unique course codes in the system by prefix."""
    query = (query or '').strip().upper()
    if not query:
        return []

    seen = set()
    all_codes = []

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. From students
        cursor.execute(
            "SELECT DISTINCT courses FROM students "
            "WHERE courses IS NOT NULL AND courses != ''"
        )
        for row in cursor.fetchall():
            try:
                for c in json.loads(row['courses']):
                    if c and c not in seen:
                        all_codes.append(c)
                        seen.add(c)
            except (json.JSONDecodeError, TypeError):
                pass

        # 2. From class sessions
        cursor.execute("SELECT DISTINCT course_code FROM class_sessions")
        for row in cursor.fetchall():
            c = row['course_code']
            if c and c not in seen:
                all_codes.append(c)
                seen.add(c)

        # 3. From lecturers
        cursor.execute(
            "SELECT courses FROM users WHERE courses IS NOT NULL AND courses != ''"
        )
        for row in cursor.fetchall():
            try:
                for c in json.loads(row['courses']):
                    if c and c not in seen:
                        all_codes.append(c)
                        seen.add(c)
            except (json.JSONDecodeError, TypeError):
                pass

    # Filter by prefix
    matches = [c for c in all_codes if c.upper().startswith(query)]

    # Sort: level-matching first (if student_level provided), then alphabetical
    if student_level:
        level_digit = str(student_level)[0] if student_level else None
        def sort_key(code):
            level_match = 0 if (len(code) >= 4 and code[3] == level_digit) else 1
            return (level_match, code)
        matches.sort(key=sort_key)
    else:
        matches.sort()

    return matches[:limit]


if __name__ == "__main__":
    # Test database operations
    logger.info("Testing database module...")

    # Initialize database
    init_database()
