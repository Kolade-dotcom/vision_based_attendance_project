import functools
from flask import session, redirect, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import db_helper

def student_login_required(view):
    """Decorator requiring student login."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if 'student_id' not in session:
            return redirect('/portal/login')
        return view(**kwargs)
    return wrapped

def student_enrollment_required(view):
    """Decorator requiring completed face enrollment."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if 'student_id' not in session:
            return redirect('/portal/login')
        student = db_helper.get_student_by_matric(session['student_id'])
        if not student or not student.get('is_enrolled'):
            return redirect('/portal/enroll')
        return view(**kwargs)
    return wrapped

def student_login_logic(data):
    """Handle student login."""
    matric = data.get('matric_number', '').strip()
    password = data.get('password', '')

    if not matric or not password:
        return jsonify({'error': 'Matric number and password are required'}), 400

    student = db_helper.get_student_by_matric(matric)

    if student and student.get('password_hash') and check_password_hash(student['password_hash'], password):
        session.clear()
        session['student_id'] = student['student_id']
        session['student_name'] = student['name']
        session['is_student'] = True
        return jsonify({'status': 'success', 'is_enrolled': bool(student.get('is_enrolled'))}), 200

    return jsonify({'error': 'Invalid matric number or password'}), 401

def student_signup_logic(data):
    """Handle student signup."""
    matric = data.get('matric_number', '').strip()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip() or None
    password = data.get('password', '')

    if not matric or not name or not password:
        return jsonify({'error': 'Matric number, name, and password are required'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    existing = db_helper.get_student_by_matric(matric)
    if existing:
        return jsonify({'error': 'Matric number already registered'}), 409

    password_hash = generate_password_hash(password)
    student_id = db_helper.create_student_account(matric, name, email, password_hash)

    if student_id:
        session.clear()
        session['student_id'] = matric
        session['student_name'] = name
        session['is_student'] = True
        return jsonify({'status': 'success', 'is_enrolled': False}), 201

    return jsonify({'error': 'Failed to create account'}), 500

def student_logout_logic():
    """Handle student logout."""
    session.clear()
    return redirect('/portal/login')
