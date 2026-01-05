from flask import jsonify, request
import db_helper
from camera import get_camera

def start_session_logic():
    """
    Start a new session.
    Expects JSON: { "course_code": "...", "scheduled_start": "..." }
    """
    try:
        data = request.get_json()
        course_code = data.get('course_code')
        scheduled_start = data.get('scheduled_start')
        
        if not course_code or not scheduled_start:
            return jsonify({'error': 'Missing course_code or scheduled_start'}), 400
            
        session_id = db_helper.create_session(course_code, scheduled_start)
        
        # Start Camera
        try:
            get_camera().start()
        except Exception as cam_err:
            print(f"Warning: Camera failed to start: {cam_err}")
            
        return jsonify({'message': 'Session started', 'session_id': session_id, 'course_code': course_code, 'status': 'active'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def end_session_logic():
    """
    End a session.
    Expects JSON: { "session_id": "..." }
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400
            
        success = db_helper.end_session(session_id)
        if success:
            # Stop Camera
            get_camera().stop()
            return jsonify({'message': 'Session ended', 'status': 'inactive'}), 200
        else:
            return jsonify({'error': 'Session not found or already inactive'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_active_session_logic():
    """Get active session for a course (optional query param)."""
    try:
        course_code = request.args.get('course_code')
        session = db_helper.get_active_session(course_code)
        if session:
            return jsonify(session), 200
        return jsonify({'message': 'No active session'}), 200 # Or 404? 200 with null is often easier for FE
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_history_logic():
    """Get session history."""
    try:
        history = db_helper.get_session_history()
        return jsonify(history), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def export_session_logic(session_id):
    """Export session attendance to CSV."""
    try:
        records = db_helper.get_session_attendance(session_id)
        
        # Simple CSV generation
        import csv
        import io
        from flask import make_response
        
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['Student ID', 'Name', 'Time', 'Status', 'Course'])
        
        for r in records:
            cw.writerow([
                r['student_id'],
                r['student_name'],
                r['timestamp'],
                r['status'],
                r['course_code']
            ])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=session_{session_id}.csv"
        output.headers["Content-type"] = "text/csv"
        return output
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_session_attendance_logic(session_id):
    """Get attendance records for a specific session (for viewing)."""
    try:
        records = db_helper.get_session_attendance(session_id)
        return jsonify(records), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def delete_session_logic(session_id):
    """Delete a session and its attendance records."""
    try:
        success = db_helper.delete_session(session_id)
        if success:
            return jsonify({'message': 'Session deleted'}), 200
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
