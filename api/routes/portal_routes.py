from flask import Blueprint, render_template, session, redirect
from api.controllers.portal_auth_controller import student_login_required, student_enrollment_required

portal_bp = Blueprint('portal', __name__, url_prefix='/portal')

@portal_bp.route('/login')
def login():
    return render_template('portal/login.html')

@portal_bp.route('/enroll')
@student_login_required
def enroll():
    return render_template('portal/enroll.html')

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
