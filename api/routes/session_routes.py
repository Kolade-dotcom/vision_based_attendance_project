from flask import Blueprint
from api.controllers.session_controller import start_session_logic, end_session_logic, get_active_session_logic, get_history_logic, export_session_logic

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
    # Pass session_id explicitly if logic expects it, or use logic argument
    # Controller logic uses request.args or expects session_id argument?
    # My controller plan for export wasn't fully detailed in code yet, let's check controller.
    # Ah, I haven't implemented export_session_logic in controller.py yet.
    # I should add the stub or implementation in controller first or now.
    # For now, I'll map it to the logic function which I will define/update.
    return export_session_logic(session_id)
