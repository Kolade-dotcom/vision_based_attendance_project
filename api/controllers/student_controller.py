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

def update_student_logic(current_student_id, data):
    """Business logic for updating a student."""
    if not current_student_id:
        return jsonify({'error': 'Student ID is required'}), 400
        
    try:
        new_student_id = data.get('student_id', current_student_id) # Default to current if not provided
        name = data.get('name')
        level = data.get('level')
        courses = data.get('courses', [])
        
        success = db_helper.update_student(current_student_id, new_student_id, name, level, courses)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Student updated successfully'}), 200
        else:
            return jsonify({'error': 'Update failed (Student not found or new ID exists)'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def delete_student_logic(student_id):
    """Business logic for deleting a student."""
    if not student_id:
        return jsonify({'error': 'Student ID is required'}), 400
        
    try:
        success = db_helper.delete_student(student_id)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Student deleted successfully'}), 200
        else:
            return jsonify({'error': 'Student not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
