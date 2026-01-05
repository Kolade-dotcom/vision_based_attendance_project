from flask import jsonify, request
import db_helper

def get_attendance_logic():
    """Business logic for fetching current session's attendance."""
    try:
        # Get attendance for the currently active session only
        attendance = db_helper.get_attendance_for_active_session()
        return jsonify(attendance)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_statistics_logic():
    """Business logic for calculating system statistics."""
    try:
        course_code = request.args.get('course')
        level = request.args.get('level')
        
        stats = db_helper.get_statistics(course_code=course_code, level=level)
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

