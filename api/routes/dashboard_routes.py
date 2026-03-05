from flask import Blueprint, render_template, session, redirect
import functools

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def dashboard_login_required(view):
    """Decorator requiring lecturer login."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if 'user_id' not in session:
            return redirect('/dashboard/login')
        return view(**kwargs)
    return wrapped

@dashboard_bp.route('/login')
def login():
    return render_template('dashboard/login.html')

@dashboard_bp.route('/')
@dashboard_login_required
def index():
    return render_template('dashboard/index.html')

@dashboard_bp.route('/analytics')
@dashboard_login_required
def analytics():
    return render_template('dashboard/analytics.html')

@dashboard_bp.route('/settings')
@dashboard_login_required
def settings():
    return render_template('dashboard/settings.html')
