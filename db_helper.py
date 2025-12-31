"""
Database Helper Module
Handles all SQLite database operations for the attendance system.
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager
import os

# Database file path
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'attendance.db')


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Ensures connections are properly closed.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize the database with the schema."""
    schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
    
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    with get_db_connection() as conn:
        conn.executescript(schema)
        conn.commit()
    
    print("Database initialized successfully!")


def add_student(student_id, name, email=None, face_encoding=None):
    """
    Add a new student to the database.
    
    Args:
        student_id: Unique student identifier
        name: Student's full name
        email: Optional email address
        face_encoding: Optional serialized face encoding
    
    Returns:
        int: The row ID of the inserted student
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            '''
            INSERT INTO students (student_id, name, email, face_encoding, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (student_id, name, email, face_encoding, datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid


def get_student(student_id):
    """
    Retrieve a student by their ID.
    
    Args:
        student_id: The student's unique identifier
    
    Returns:
        dict: Student data or None if not found
    """
    with get_db_connection() as conn:
        result = conn.execute(
            'SELECT * FROM students WHERE student_id = ?',
            (student_id,)
        ).fetchone()
        
        return dict(result) if result else None


def get_all_students():
    """
    Retrieve all students from the database.
    
    Returns:
        list: List of student dictionaries
    """
    with get_db_connection() as conn:
        results = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
        return [dict(row) for row in results]


def record_attendance(student_id, status='present'):
    """
    Record attendance for a student.
    
    Args:
        student_id: The student's unique identifier
        status: Attendance status ('present', 'late', 'absent')
    
    Returns:
        int: The row ID of the attendance record
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            '''
            INSERT INTO attendance (student_id, timestamp, status)
            VALUES (?, ?, ?)
            ''',
            (student_id, datetime.now().isoformat(), status)
        )
        conn.commit()
        return cursor.lastrowid


def get_attendance_today(student_id=None):
    """
    Get today's attendance records.
    
    Args:
        student_id: Optional filter by student
    
    Returns:
        list: List of attendance records
    """
    today = datetime.now().date().isoformat()
    
    with get_db_connection() as conn:
        if student_id:
            results = conn.execute(
                '''
                SELECT a.*, s.name as student_name 
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE date(a.timestamp) = ? AND a.student_id = ?
                ORDER BY a.timestamp DESC
                ''',
                (today, student_id)
            ).fetchall()
        else:
            results = conn.execute(
                '''
                SELECT a.*, s.name as student_name 
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE date(a.timestamp) = ?
                ORDER BY a.timestamp DESC
                ''',
                (today,)
            ).fetchall()
        
        return [dict(row) for row in results]


if __name__ == '__main__':
    # Test database operations
    print("Testing database module...")
    
    # Initialize database
    init_database()
    
    # Add a test student
    add_student('STU001', 'Test Student', 'test@example.com')
    
    # Retrieve the student
    student = get_student('STU001')
    print(f"Retrieved student: {student}")
    
    # Record attendance
    record_attendance('STU001', 'present')
    
    # Get today's attendance
    attendance = get_attendance_today()
    print(f"Today's attendance: {attendance}")
