"""
Smart Vision-Based Attendance System
Flask Application Entry Point
"""

from flask import Flask, render_template, Response, jsonify, request
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')


@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html')


@app.route('/enroll')
def enroll():
    """Render the enrollment page for new students."""
    return render_template('enroll.html')


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'message': 'Attendance system is running'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
