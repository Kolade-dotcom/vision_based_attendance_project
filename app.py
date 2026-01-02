from flask import Flask, render_template, jsonify, request
import os
import db_helper
from api.routes.student_routes import student_bp
from api.routes.attendance_routes import attendance_bp
from api.routes.auth_routes import auth_bp
from api.controllers.auth_controller import login_required

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Ensure database is initialized
db_helper.init_database()

# Register Blueprints
app.register_blueprint(student_bp, url_prefix='/api')
app.register_blueprint(attendance_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')


@app.route('/')
@login_required
def index():
    """Render the main dashboard page."""
    return render_template('index.html')


@app.route('/enroll')
@login_required
def enroll():
    """Render the enrollment page for new students."""
    return render_template('enroll.html')

@app.route('/login')
def login():
    """Render the login page."""
    return render_template('login.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'message': 'Attendance system modular API is running'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'message': 'Attendance system modular API is running'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


