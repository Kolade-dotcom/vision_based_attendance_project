from flask import Blueprint
from api.controllers.attendance_controller import get_attendance_logic, get_statistics_logic

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/attendance/today', methods=['GET'])
def get_attendance():
    return get_attendance_logic()

@attendance_bp.route('/statistics', methods=['GET'])
def get_statistics():
    return get_statistics_logic()
