import functools
from flask import session, redirect, url_for, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import db_helper

def login_required(view):
    """Decorator to require login for views."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

def login_logic(data):
    """Handle login request."""
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
        
    user = db_helper.get_user_by_email(email)
    
    if user and check_password_hash(user['password_hash'], password):
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        return jsonify({'status': 'success', 'message': 'Logged in successfully'}), 200
    
    return jsonify({'error': 'Invalid email or password'}), 401

def signup_logic(data):
    """Handle signup request (Admin creation)."""
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if not email or not password or not name:
        return jsonify({'error': 'All fields are required'}), 400
        
    # Check if user exists
    if db_helper.get_user_by_email(email):
        return jsonify({'error': 'Email already registered'}), 409
        
    password_hash = generate_password_hash(password)
    user_id = db_helper.create_user(email, password_hash, name)
    
    if user_id:
        session.clear()
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        return jsonify({'status': 'success', 'message': 'Account created successfully'}), 201
        
    return jsonify({'error': 'Failed to create account'}), 500

def logout_logic():
    """Handle logout."""
    session.clear()
    return redirect(url_for('login'))
