from flask import Blueprint
from api.controllers.attendance_controller import get_attendance_logic, get_statistics_logic, approve_attendance_logic, dismiss_attendance_logic

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/attendance/today', methods=['GET'])
def get_attendance():
    return get_attendance_logic()

@attendance_bp.route('/statistics', methods=['GET'])
def get_statistics():
    return get_statistics_logic()

@attendance_bp.route('/attendance/<int:attendance_id>/approve', methods=['PATCH'])
def approve_attendance(attendance_id):
    return approve_attendance_logic(attendance_id)

@attendance_bp.route('/attendance/<int:attendance_id>', methods=['DELETE'])
def dismiss_attendance(attendance_id):
    return dismiss_attendance_logic(attendance_id)
