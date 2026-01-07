from flask import Flask, render_template, jsonify, request, Response, session
import cv2
import os
import db_helper
from api.routes.student_routes import student_bp
from api.routes.attendance_routes import attendance_bp
from api.routes.auth_routes import auth_bp
from api.routes.session_routes import session_bp
from api.routes.face_capture_routes import face_capture_bp
from api.controllers.auth_controller import login_required
from api.controllers.face_capture_controller import get_user_capture_session
from camera import get_camera, draw_face_boxes, FaceDetector
import face_recognition
import pickle
import numpy as np


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
app.register_blueprint(face_capture_bp, url_prefix='/api')


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

def gen_frames(user_id):
    """Video streaming generator function with face recognition."""
    camera = get_camera()
    # Tuned for responsiveness (skip_frames=1) and stability (smoothing_window=5)
    detector = FaceDetector(model="hog", scale=0.5, skip_frames=1, smoothing_window=5)
    
    # Load known faces from DB once per stream connection
    known_face_encodings = []
    known_face_names = []
    known_student_ids = []
    
    try:
        students = db_helper.get_all_student_encodings()
        for student in students:
            if student['face_encoding']:
                try:
                    # Deserialize bytes to numpy array
                    encoding = pickle.loads(student['face_encoding'])
                    known_face_encodings.append(encoding)
                    known_face_names.append(student['name'])
                    known_student_ids.append(student['student_id'])
                except Exception as e:
                    print(f"Error loading encoding for {student['student_id']}: {e}")
    except Exception as e:
        print(f"Error fetching student encodings: {e}")
    
    print(f"Loaded {len(known_face_encodings)} face encodings for recognition.")
    
    # Ensure camera is started (if not already by session start)
    # Usually session start handles it, but safety check:
    camera.start()
    
    while True:
        frame = camera.get_frame()
        if frame is None:
            # If camera is stopped (session ended) or error, we break
            break
        
        # Detect faces using advanced HOG-based detector with tracking
        faces = detector.detect(frame)
        
        # Recognition
        face_names = []
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get active session for this user to mark attendance
        # We check this periodically or every frame?
        # For efficiency, maybe we assume the session started by this user is target.
        # But we need course code for record_attendance.
        active_session = db_helper.get_active_session(user_id)
        
        if active_session and known_face_encodings:
            # We have faces (x, y, w, h). face_recognition needs (top, right, bottom, left)
            # detector.detect returns (x, y, w, h)
            face_locations_for_rec = []
            for (x, y, w, h) in faces:
                face_locations_for_rec.append((y, x + w, y + h, x))
            
            # Encode faces in current frame
            # Use small frame or original? detector scales internally but returns original coords.
            # face_recognition is slow on large images.
            # Optimization: Resize frame for recognition like detection does.
            # For now, let's use the full frame but maybe skip frames for recognition?
            # detector skips frames. If we only recognize on detected frames...
            
            # Real-time recognition is heavy. Let's do it directly.
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations_for_rec)

            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5)
                name = "Unknown"
                student_id = None

                if True in matches:
                    first_match_index = matches.index(True)
                    # Better: use face_distance to find best match
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
                        student_id = known_student_ids[best_match_index]
                        
                        # Mark Attendance
                        db_helper.record_attendance(
                            student_id, 
                            status='present', 
                            course_code=active_session['course_code']
                        )
                
                face_names.append(name)
        
        # Draw boxes and names
        # draw_face_boxes only draws boxes. We need custom drawing for names.
        # frame = draw_face_boxes(frame, faces) # Replacing this to add names
        
        for (x, y, w, h), name in zip(faces, face_names if active_session else [""]*len(faces)):
            color = (0, 255, 0) if name and name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            if name:
                cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # If no recognition (no session), just draw boxes (fallback)
        if not active_session:
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
    user_id = session.get('user_id')
    return Response(gen_frames(user_id), mimetype='multipart/x-mixed-replace; boundary=frame')


# ============================================================================
# Enrollment Face Capture Video Feed
# ============================================================================

def gen_enrollment_frames(capture_session):
    """Video streaming generator with guided face capture overlay."""
    camera = get_camera()
    
    # Ensure camera is started
    camera.start()
    
    while True:
        frame = camera.get_frame()
        if frame is None:
            # Camera might not be ready yet, yield placeholder or retry
            import time
            time.sleep(0.1)
            continue
        
        # Process frame with guided capture
        annotated_frame, status = capture_session.process_frame(frame)
        
        # Add instruction overlay
        instruction = status.get('instruction', '')
        feedback = status.get('feedback', '')
        progress = status.get('progress', '0/21')
        
        # Draw semi-transparent overlay at top
        overlay = annotated_frame.copy()
        cv2.rectangle(overlay, (0, 0), (annotated_frame.shape[1], 80), (0, 0, 0), -1)
        annotated_frame = cv2.addWeighted(overlay, 0.5, annotated_frame, 0.5, 0)
        
        # Draw text
        cv2.putText(annotated_frame, instruction, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(annotated_frame, feedback, (10, 55), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(annotated_frame, f"Progress: {progress}", (10, 75), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Encode frame
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Stop if capture is complete
        if status.get('is_complete'):
            camera.stop()
            break


@app.route('/enrollment_video_feed')
@login_required
def enrollment_video_feed():
    """Video streaming route for enrollment with guided face capture."""
    # Get capture session BEFORE entering generator (to access Flask session context)
    capture_session = get_user_capture_session()
    return Response(gen_enrollment_frames(capture_session), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
