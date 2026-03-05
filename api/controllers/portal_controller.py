from flask import jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import db_helper
import json
import base64
import logging

logger = logging.getLogger(__name__)

def get_home_data_logic(student_id):
    """Get student home page data."""
    student = db_helper.get_student_by_matric(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    courses = json.loads(student['courses']) if student.get('courses') else []
    stats = db_helper.get_student_attendance_stats(student_id)

    today_attendance = []
    for course in courses:
        active = db_helper.get_active_session_by_course(course)
        if active:
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
        'courses': courses,
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


def process_capture_logic(data):
    """Process captured face frames and return an aggregated encoding."""
    from face_processor import process_multiple_face_images

    frames = data.get('frames', [])
    if not frames or len(frames) < 7:
        return jsonify({'error': 'At least 7 face frames required'}), 400

    result = process_multiple_face_images(frames)

    if result['status'] == 'error':
        return jsonify(result), 400

    return jsonify({
        'status': 'success',
        'face_encoding': result['face_encoding'],
        'frames_processed': result.get('image_count', 0)
    })
