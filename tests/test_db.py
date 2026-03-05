import pytest
import json


# ============================================================================
# Student Portal Auth & Profile Tests
# ============================================================================


def test_create_student_account(db):
    student_id = db.create_student_account("125/22/1/0178", "John Doe", "john@uni.edu", "hashed_pw")
    assert student_id is not None
    student = db.get_student_by_matric("125/22/1/0178")
    assert student is not None
    assert student["name"] == "John Doe"
    assert student["is_enrolled"] == 0
    assert student["password_hash"] == "hashed_pw"


def test_update_student_enrollment(db):
    db.create_student_account("125/22/1/0179", "Jane Doe", "jane@uni.edu", "hashed_pw")
    db.update_student_enrollment("125/22/1/0179", b"fake_encoding", "400", ["MTE411", "MTE412"])
    student = db.get_student_by_matric("125/22/1/0179")
    assert student["is_enrolled"] == 1
    assert student["level"] == "400"


def test_get_student_attendance_stats_empty(db):
    db.create_student_account("125/22/1/0180", "Bob", "bob@uni.edu", "hashed_pw")
    stats = db.get_student_attendance_stats("125/22/1/0180")
    assert stats["total_sessions"] == 0
    assert stats["attendance_rate"] == 0


# ============================================================================
# Original Tests
# ============================================================================


def test_add_and_get_student(db):
    # Using matric number format as requested
    student_id = "125/22/1/0178"
    name = "Test Student"
    email = "test@example.com"
    level = "400"
    courses = ["MTE411", "MTE412"]
    
    # Updated to accept level and courses
    row_id = db.add_student(student_id, name, email, level=level, courses=courses)
    assert row_id is not None
    
    student = db.get_student(student_id)
    assert student is not None
    assert student['student_id'] == student_id
    assert student['name'] == name
    assert student['level'] == level
    
    # Verify courses are stored/retrieved correctly
    stored_courses = json.loads(student['courses'])
    assert "MTE411" in stored_courses
    assert "MTE412" in stored_courses

def test_get_all_students(db):
    db.add_student("125/22/1/0001", "Student One", level="100", courses=[])
    db.add_student("125/22/1/0002", "Student Two", level="200", courses=[])
    
    students = db.get_all_students()
    assert len(students) == 2

def test_record_attendance_detailed(db):
    student_id = "125/22/1/0178"
    db.add_student(student_id, "Test Student", level="400", courses=["MTE411"])
    
    # Record attendance with specific course and level context
    # format: MTE411 (400 Level)
    course_code = "MTE411"
    level = "400"
    
    row_id = db.record_attendance(student_id, "present", course_code=course_code, level=level)
    assert row_id is not None
    
    # Verify filtering
    attendance = db.get_attendance_today(course_code="MTE411", level="400")
    assert len(attendance) == 1
    assert attendance[0]['student_id'] == student_id
    assert attendance[0]['course_code'] == course_code
    assert attendance[0]['level'] == level

def test_attendance_filtering(db):
    student_id = "125/22/1/0178"

    db.add_student(student_id, "Test Student", level="400", courses=["MTE411", "MTE413"])
    
    # Record one entry for MTE411
    db.record_attendance(student_id, "present", course_code="MTE411", level="400")
    
    # Record one entry for MTE413
    db.record_attendance(student_id, "present", course_code="MTE413", level="400")
    
    # Check total
    all_attendance = db.get_attendance_today()
    assert len(all_attendance) == 2
    
    # Check filter
    mte411_attendance = db.get_attendance_today(course_code="MTE411")
    assert len(mte411_attendance) == 1
    assert mte411_attendance[0]['course_code'] == "MTE411"

