import json
import base64
from flask import jsonify, session, request
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
        face_encoding_b64 = data.get('face_encoding')
        
        # Decode face encoding if provided
        face_encoding_bytes = None
        if face_encoding_b64:
            try:
                face_encoding_bytes = base64.b64decode(face_encoding_b64)
            except Exception:
                return jsonify({'error': 'Invalid face encoding format'}), 400
        
        # Get current user ID for created_by field
        user_id = session.get('user_id')
        
        row_id = db_helper.add_student(
            student_id, name, email, 
            level=level, courses=courses, 
            face_encoding=face_encoding_bytes,
            status='approved',  # Direct enrollment is auto-approved
            created_by=user_id
        )
        
        if row_id is None:
             return jsonify({'error': 'Student ID already exists'}), 409

        return jsonify({
            'status': 'success',
            'message': f'Student {name} enrolled successfully',
            'id': row_id,
            'student_id': student_id,
            'has_face_encoding': face_encoding_bytes is not None
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_students_logic():
    """Business logic for fetching all students."""
    try:
        # Get optional status filter from query params
        status_filter = request.args.get('status')
        
        students = db_helper.get_all_students(status_filter=status_filter)
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


# ============================================================================
# Student Approval Workflow
# ============================================================================

def approve_student_logic(student_id):
    """Approve a pending student enrollment."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not student_id:
        return jsonify({'error': 'Student ID is required'}), 400
    
    try:
        success = db_helper.approve_student(student_id, user_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Student approved successfully'
            }), 200
        else:
            return jsonify({'error': 'Student not found or not pending'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def reject_student_logic(student_id, data=None):
    """Reject a pending student enrollment."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not student_id:
        return jsonify({'error': 'Student ID is required'}), 400
    
    reason = data.get('reason') if data else None
    
    try:
        success = db_helper.reject_student(student_id, user_id, reason)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Student enrollment rejected'
            }), 200
        else:
            return jsonify({'error': 'Student not found or not pending'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_pending_count_logic():
    """Get count of pending student enrollments."""
    try:
        count = db_helper.get_pending_students_count()
        return jsonify({'count': count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
