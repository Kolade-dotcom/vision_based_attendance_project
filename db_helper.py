"""
Database Helper Module
Handles all SQLite database operations for the attendance system.
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager
import os
import json

# Database file path (can be overridden for testing)
_DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'attendance.db')

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
    schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
    
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if class_sessions table exists and needs migration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='class_sessions'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check if user_id column exists
            cursor.execute("PRAGMA table_info(class_sessions)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'user_id' not in columns:
                # Add column with default value for existing records
                conn.execute("ALTER TABLE class_sessions ADD COLUMN user_id INTEGER DEFAULT 1")
                print("Migration: Added user_id column to class_sessions")
        
        # Now execute the schema (CREATE IF NOT EXISTS won't modify existing tables)
        conn.executescript(schema)
        conn.commit()
    
    print("Database initialized successfully!")

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
            (start_time, user_id)
        )
        
        cursor.execute(
            """
            INSERT INTO class_sessions (user_id, course_code, scheduled_start, start_time, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (user_id, course_code, start_time, start_time)
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
            (end_time, session_id)
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
                (email, password_hash, name)
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
            cursor.execute("SELECT 1 FROM students WHERE student_id = ?", (new_student_id,))
            if cursor.fetchone():
                return False # New ID already exists
                
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
                    (new_student_id, name, level, courses_json, current_student_id)
                )
                
                if cursor.rowcount > 0:
                    cursor.execute(
                        "UPDATE attendance SET student_id = ? WHERE student_id = ?",
                        (new_student_id, current_student_id)
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
                (name, level, courses_json, current_student_id)
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


def add_student(student_id, name, email=None, level=None, courses=None, face_encoding=None):
    """
    Add a new student to the database.
    
    Args:
        student_id (str): Unique Matric Number/ID
        name (str): Full Name
        email (str, optional): Email address
        level (str, optional): Student Level (e.g. "400")
        courses (list, optional): List of course codes
        face_encoding (bytes, optional): Serialized face encoding
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
                INSERT INTO students (student_id, name, email, level, courses, face_encoding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (student_id, name, email, level, courses_json, face_encoding, datetime.now().isoformat())
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Error: Student ID {student_id} already exists.")
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


def get_all_students():
    """Get a list of all enrolled students."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, email, level, courses, created_at FROM students")
        return [dict(row) for row in cursor.fetchall()]


def get_all_student_encodings():
    """
    Get all students' face encodings.
    
    Returns:
        list: List of dicts with 'student_id', 'name', and 'face_encoding' (bytes)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, face_encoding FROM students WHERE face_encoding IS NOT NULL")
        return [dict(row) for row in cursor.fetchall()]


def record_attendance(student_id, status='present', course_code=None, level=None):
    """
    Record attendance for a student.
    
    Args:
        student_id (str): Student ID
        status (str): Attendance status
        course_code (str, optional): Course context for this attendance
        level (str, optional): Level context
    """
    
    # Determine session_id if active
    session_id = None
    # We need to find if there is an active session for this course
    # To avoid circular imports or redundant calls, we can implement lightweight check here or call get_active_session logic
    # Ideally reuse get_active_session but we are in same file.
    
    # We can't easily call get_active_session because I defined it below originally? 
    # Ah I am inserting create_session ABOVE. So get_active_session is available if I order it right.
    # Wait, python allows calling functions defined later? No.
    # I should have placed them carefully.
    # Let's just implement the logic inline or rely on global scope if defined above.
    # Let's assume get_active_session IS available because I inserted it at line 51 (above this function which is at 223).
    
    # However, Python functions find globals at runtime, so as long as it's defined in module it's fine.
    
    # But wait, I need to fetch it.
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check active session
        active_session_query = "SELECT id, start_time FROM class_sessions WHERE is_active = 1"
        active_params = []
        if course_code:
            active_session_query += " AND course_code = ?"
            active_params.append(course_code)
            
        cursor.execute(active_session_query + " ORDER BY start_time DESC LIMIT 1", active_params)
        session_row = cursor.fetchone()
        if session_row:
            session_id = session_row['id']
            # Check for late status based on session start_time
            # Grace period: students arriving within 15 minutes of session start are "present"
            # After 15 minutes from session start, they are marked "late"
            if session_row['start_time']:
                session_start = datetime.fromisoformat(session_row['start_time'])
                current_time = datetime.now()
                grace_period_seconds = 900  # 15 minutes grace period
                if (current_time - session_start).total_seconds() > grace_period_seconds:
                    status = 'late'
        
        # Check if student exists
        cursor.execute("SELECT id, name, level FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            print(f"Error: Student {student_id} not found.")
            return None
            
        # If level is not passed, use student's level
        if not level and student['level']:
            level = student['level']
            
        # Check for existing attendance in this session to prevent duplicates
        if session_id:
            cursor.execute(
                "SELECT 1 FROM attendance WHERE session_id = ? AND student_id = ?", 
                (session_id, student_id)
            )
            if cursor.fetchone():
                # Already marked present
                return None

        cursor.execute(
            """
            INSERT INTO attendance (student_id, timestamp, status, course_code, level, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (student_id, datetime.now().isoformat(), status, course_code, level, session_id)
        )
        conn.commit()
        return cursor.lastrowid

def get_attendance_today(course_code=None, level=None):
    """
    Get all attendance records for today, optionally filtered.
    """
    start_of_day = datetime.now().strftime('%Y-%m-%dT00:00:00')
    
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
    start_of_day = datetime.now().strftime('%Y-%m-%dT00:00:00')
    
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
        cursor.execute(f"SELECT COUNT(*) FROM attendance {where_clause} AND status = 'present'", params)
        present_count = cursor.fetchone()[0]
        
        # Total late
        cursor.execute(f"SELECT COUNT(*) FROM attendance {where_clause} AND status = 'late'", params)
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
            'present_today': present_count,
            'late_today': late_count,
            'total_students': total_students
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
            (user_id,)
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
            (session_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_attendance_for_active_session():
    """
    Get attendance records for the currently active session.
    
    Returns:
        list: List of attendance record dictionaries, or empty list if no active session.
    """
    active_session = get_active_session()
    if not active_session:
        return []
    
    return get_session_attendance(active_session['id'])


if __name__ == '__main__':
    # Test database operations
    print("Testing database module...")
    
    # Initialize database
    init_database()

