from flask import Flask, render_template, jsonify, request, Response
import cv2
import os
import db_helper
from api.routes.student_routes import student_bp
from api.routes.attendance_routes import attendance_bp
from api.routes.auth_routes import auth_bp
from api.routes.session_routes import session_bp
from api.controllers.auth_controller import login_required
from camera import get_camera, draw_face_boxes

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Ensure database is initialized
db_helper.init_database()

# Register Blueprints
app.register_blueprint(student_bp, url_prefix='/api')
app.register_blueprint(attendance_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(session_bp, url_prefix='/api')


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

def gen_frames():
    """Video streaming generator function with optimized face detection."""
    camera = get_camera()
    # Camera start is handled by session controller
    
    while True:
        frame = camera.get_frame()
        if frame is None:
            # If camera is stopped (session ended) or error, we break or yield placeholder
            break
        
        # Detect faces using optimized method (resizing, frame skip, cached classifier)
        faces = camera.detect_faces_optimized(frame)
        frame = draw_face_boxes(frame, faces)
        
        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
@login_required
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)




