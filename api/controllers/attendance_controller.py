from flask import jsonify, request, session as flask_session
import db_helper

def get_attendance_logic():
    """Business logic for fetching current session's attendance."""
    try:
        user_id = flask_session.get('user_id')
        if not user_id:
            print("DEBUG: No user_id in session")
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Get active session for this user
        active_session = db_helper.get_active_session(user_id)
        if not active_session:
            print(f"DEBUG: No active session for user {user_id}")
            return jsonify([])
        
        print(f"DEBUG: Found active session {active_session['id']} for course {active_session['course_code']}")
        
        # Get attendance for this session
        attendance = db_helper.get_session_attendance(active_session['id'])
        print(f"DEBUG: Found {len(attendance)} attendance records")
        return jsonify(attendance)
    except Exception as e:
        print(f"DEBUG: Error in get_attendance_logic: {e}")
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

