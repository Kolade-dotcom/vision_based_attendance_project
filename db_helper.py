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
    
    with get_db_connection() as conn:
        conn.executescript(schema)
        conn.commit()
    
    print("Database initialized successfully!")


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
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if student exists
        cursor.execute("SELECT id, name FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            print(f"Error: Student {student_id} not found.")
            return None
            
        cursor.execute(
            """
            INSERT INTO attendance (student_id, timestamp, status, course_code, level)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, datetime.now().isoformat(), status, course_code, level)
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

