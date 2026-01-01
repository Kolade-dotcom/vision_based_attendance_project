import json
from flask import jsonify
import db_helper

def enroll_student_logic(data):
    """Business logic for student enrollment."""
    if not data or not data.get('student_id') or not data.get('name'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        student_id = data.get('student_id')
        name = data.get('name')
        email = data.get('email')
        level = data.get('level')
        courses = data.get('courses', [])
        
        row_id = db_helper.add_student(student_id, name, email, level=level, courses=courses)
        
        if row_id is None:
             return jsonify({'error': 'Student ID already exists'}), 409

        return jsonify({
            'status': 'success',
            'message': f'Student {name} enrolled successfully',
            'id': row_id,
            'student_id': student_id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_students_logic():
    """Business logic for fetching all students."""
    try:
        students = db_helper.get_all_students()
        # Parse courses JSON string back to list for API response
        for student in students:
            if student.get('courses'):
                try:
                    student['courses'] = json.loads(student['courses'])
                except:
                    student['courses'] = []
        return jsonify(students)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

