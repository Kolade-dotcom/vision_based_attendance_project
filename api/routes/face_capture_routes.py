"""
Face Capture Routes
API endpoints for guided face capture during enrollment.
"""

from flask import Blueprint
from api.controllers.face_capture_controller import (
    start_capture_logic,
    capture_status_logic,
    get_face_encoding_logic,
    reset_capture_logic,
)
from api.controllers.auth_controller import login_required


face_capture_bp = Blueprint('face_capture', __name__)


@face_capture_bp.route('/start_capture', methods=['POST'])
@login_required
def start_capture():
    """Initialize or reset a face capture session."""
    return start_capture_logic()


@face_capture_bp.route('/capture_status', methods=['GET'])
@login_required
def capture_status():
    """Get current face capture progress and status."""
    return capture_status_logic()


@face_capture_bp.route('/get_face_encoding', methods=['GET'])
@login_required
def get_face_encoding():
    """Get the completed face encoding after capture is done."""
    return get_face_encoding_logic()


@face_capture_bp.route('/reset_capture', methods=['POST'])
@login_required
def reset_capture():
    """Reset the face capture session."""
    return reset_capture_logic()
