"""
Face Capture Controller
Business logic for guided face capture during enrollment.
"""

import base64
from flask import jsonify, session
from camera import get_camera
from face_capture import GuidedFaceCapture


# Global storage for enrollment capture sessions (per user)
_enrollment_captures = {}


def get_user_capture_session(user_id=None):
    """Get or create capture session for a user."""
    if user_id is None:
        user_id = session.get('user_id', 'default')
    if user_id not in _enrollment_captures:
        _enrollment_captures[user_id] = GuidedFaceCapture(frames_per_pose=3)
    return _enrollment_captures[user_id]


def start_capture_logic():
    """Initialize or reset a face capture session."""
    user_id = session.get('user_id', 'default')
    _enrollment_captures[user_id] = GuidedFaceCapture(frames_per_pose=3)
    
    # Start camera
    camera = get_camera()
    try:
        camera.start()
    except RuntimeError:
        pass  # Already started
    
    return jsonify({
        'status': 'success',
        'message': 'Capture session started',
    })


def capture_status_logic():
    """Get current face capture progress and status."""
    capture_session = get_user_capture_session()
    
    current_stage = capture_session.get_current_stage()
    
    return jsonify({
        'stage': current_stage['name'],
        'stage_index': capture_session.current_stage_index,
        'instruction': capture_session.get_current_instruction(),
        'frames_captured': current_stage.get('frames_captured', 0),
        'frames_needed': capture_session.frames_per_pose,
        'total_stages': len(capture_session.stages),
        'progress_percent': capture_session.get_progress_percentage(),
        'is_complete': capture_session.is_complete(),
    })


def get_face_encoding_logic():
    """Get the completed face encoding after capture is done."""
    capture_session = get_user_capture_session()
    
    if not capture_session.is_complete():
        return jsonify({
            'status': 'error',
            'error': 'Capture not yet complete',
        }), 400
    
    encoding_bytes = capture_session.get_aggregated_encoding()
    encoding_b64 = base64.b64encode(encoding_bytes).decode('utf-8')
    
    return jsonify({
        'status': 'success',
        'face_encoding': encoding_b64,
        'encoding_count': len(capture_session.encodings),
    })


def reset_capture_logic():
    """Reset the face capture session."""
    user_id = session.get('user_id', 'default')
    if user_id in _enrollment_captures:
        _enrollment_captures[user_id].reset()
    
    return jsonify({
        'status': 'success',
        'message': 'Capture session reset',
    })
