"""
Database Helper Module
Handles all SQLite database operations for the attendance system.
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager
import os
import json

# Database file path
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'attendance.db')


@contextmanager
def get_db_connection():
    """Context manager for database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize the database with schema."""
    schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
    
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    # Add users table schema if not in file (or just execute it here for simplicity since we can't easily edit sql file dynamically and reliably without wiping)
    # Actually, we should probably append to the schema file or just run the create statement here.
    users_schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """

    with get_db_connection() as conn:
        conn.executescript(schema)
        conn.execute(users_schema)
        conn.commit()
    
    
    # Create sessions table
    sessions_schema = """
    CREATE TABLE IF NOT EXISTS class_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_code TEXT NOT NULL,
        scheduled_start TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT,
        is_active INTEGER DEFAULT 1
    );
    """
    
    with get_db_connection() as conn:
        conn.executescript(schema)
        conn.execute(users_schema)
        conn.execute(sessions_schema)
        
        # Check if session_id exists in attendance table, if not add it
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(attendance)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'session_id' not in columns:
            try:
                conn.execute("ALTER TABLE attendance ADD COLUMN session_id INTEGER")
            except sqlite3.OperationalError:
                pass # Already exists
                
        conn.commit()
    
    print("Database initialized successfully!")

def create_session(course_code, scheduled_start):
    """
    Start a new class session.
    Ensures only one active session per course exists (or potentially global, but requirements imply per course).
    """
    # Deactivate any existing active session for this course first (just in case)
    start_time = datetime.now().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # End other sessions for this course
        cursor.execute(
            "UPDATE class_sessions SET is_active = 0, end_time = ? WHERE course_code = ? AND is_active = 1",
            (start_time, course_code)
        )
        
        cursor.execute(
            """
            INSERT INTO class_sessions (course_code, scheduled_start, start_time, is_active)
            VALUES (?, ?, ?, 1)
            """,
            (course_code, scheduled_start, start_time)
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

def get_active_session(course_code=None):
    """Get the currently active session, optionally filtered by course."""
    query = "SELECT * FROM class_sessions WHERE is_active = 1"
    params = []
    
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
        active_session_query = "SELECT id FROM class_sessions WHERE is_active = 1"
        active_params = []
        if course_code:
            active_session_query += " AND course_code = ?"
            active_params.append(course_code)
            
        cursor.execute(active_session_query + " ORDER BY start_time DESC LIMIT 1", active_params)
        if session_row:
            session_id = session_row['id']
            # Check for late status if scheduled_start is set
            if session_row['scheduled_start']:
                scheduled_time = datetime.fromisoformat(session_row['scheduled_start'])
                current_time = datetime.now()
                # Late threshold: 15 minutes (or configurable)
                # But for now let's just say if current > scheduled, it's late? 
                # Usually there's a grace period. Let's assume 15 mins.
                if (current_time - scheduled_time).total_seconds() > 900: # 15 mins
                    status = 'late'
        
        # Check if student exists
        cursor.execute("SELECT id, name FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            print(f"Error: Student {student_id} not found.")
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




if __name__ == '__main__':
    # Test database operations
    print("Testing database module...")
    
    # Initialize database
    init_database()

