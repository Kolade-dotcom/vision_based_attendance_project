from flask import Blueprint
from api.controllers.session_controller import start_session_logic, end_session_logic, get_active_session_logic, get_history_logic, export_session_logic, get_session_attendance_logic, delete_session_logic

session_bp = Blueprint('session', __name__)

@session_bp.route('/sessions/start', methods=['POST'])
def start_session():
    return start_session_logic()

@session_bp.route('/sessions/end', methods=['POST'])
def end_session():
    return end_session_logic()

@session_bp.route('/sessions/active', methods=['GET'])
def get_active_session():
    return get_active_session_logic()

@session_bp.route('/sessions/history', methods=['GET'])
def get_history():
    return get_history_logic()

@session_bp.route('/sessions/<session_id>/export', methods=['GET'])
def export_session(session_id):
    return export_session_logic(session_id)

@session_bp.route('/sessions/<session_id>/attendance', methods=['GET'])
def get_session_attendance(session_id):
    return get_session_attendance_logic(session_id)

@session_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    return delete_session_logic(session_id)
