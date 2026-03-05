from flask import Blueprint, request, session, jsonify
from api.controllers.portal_auth_controller import (
    student_login_logic, student_signup_logic, student_logout_logic,
    student_login_required, student_enrollment_required
)
from api.controllers.portal_controller import (
    get_home_data_logic, get_attendance_logic, get_profile_logic,
    update_profile_logic, update_face_logic, change_password_logic,
    complete_enrollment_logic
)

portal_api_bp = Blueprint('portal_api', __name__, url_prefix='/api/portal')

@portal_api_bp.route('/auth/login', methods=['POST'])
def login():
    return student_login_logic(request.json)

@portal_api_bp.route('/auth/signup', methods=['POST'])
def signup():
    return student_signup_logic(request.json)

@portal_api_bp.route('/auth/logout')
def logout():
    return student_logout_logic()

@portal_api_bp.route('/home', methods=['GET'])
@student_enrollment_required
def home_data():
    return get_home_data_logic(session['student_id'])

@portal_api_bp.route('/attendance', methods=['GET'])
@student_enrollment_required
def attendance():
    course = request.args.get('course')
    return get_attendance_logic(session['student_id'], course)

@portal_api_bp.route('/profile', methods=['GET'])
@student_login_required
def get_profile():
    return get_profile_logic(session['student_id'])

@portal_api_bp.route('/profile', methods=['PUT'])
@student_login_required
def update_profile():
    return update_profile_logic(session['student_id'], request.json)

@portal_api_bp.route('/face', methods=['PUT'])
@student_login_required
def update_face():
    return update_face_logic(session['student_id'], request.json)

@portal_api_bp.route('/password', methods=['PUT'])
@student_login_required
def change_password():
    return change_password_logic(session['student_id'], request.json)

@portal_api_bp.route('/enroll', methods=['POST'])
@student_login_required
def complete_enrollment():
    return complete_enrollment_logic(session['student_id'], request.json)
