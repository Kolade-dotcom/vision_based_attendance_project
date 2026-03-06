from flask import Blueprint, render_template, session, redirect, request
import db_helper
from api.controllers.portal_auth_controller import student_login_required, student_enrollment_required

portal_bp = Blueprint('portal', __name__, url_prefix='/portal')

@portal_bp.route('/login')
def login():
    return render_template('portal/login.html')

@portal_bp.route('/enroll')
@student_login_required
def enroll():
    recapture = request.args.get('recapture', '0') == '1'
    student = db_helper.get_student_by_matric(session['student_id'])
    is_enrolled = bool(student and student.get('is_enrolled'))
    return render_template('portal/enroll.html', recapture=recapture, is_enrolled=is_enrolled)

@portal_bp.route('/')
@student_enrollment_required
def home():
    return render_template('portal/home.html')

@portal_bp.route('/attendance')
@student_enrollment_required
def attendance():
    return render_template('portal/attendance.html')

@portal_bp.route('/profile')
@student_enrollment_required
def profile():
    return render_template('portal/profile.html')
