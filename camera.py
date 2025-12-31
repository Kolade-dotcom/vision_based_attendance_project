"""
Camera Module
Handles OpenCV webcam capture and face recognition logic.
"""

import cv2
import numpy as np

# Uncomment when face_recognition is installed
# import face_recognition


class Camera:
    """Handles webcam capture and frame processing."""
    
    def __init__(self, camera_index=0):
        """
        Initialize the camera.
        
        Args:
            camera_index: Index of the camera device (default: 0 for primary webcam)
        """
        self.camera_index = camera_index
        self.video_capture = None
    
    def start(self):
        """Start the video capture."""
        self.video_capture = cv2.VideoCapture(self.camera_index)
        if not self.video_capture.isOpened():
            raise RuntimeError(f"Could not open camera at index {self.camera_index}")
        return True
    
    def stop(self):
        """Stop the video capture and release resources."""
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None
    
    def get_frame(self):
        """
        Capture a single frame from the camera.
        
        Returns:
            numpy.ndarray: The captured frame, or None if capture failed
        """
        if self.video_capture is None:
            return None
        
        ret, frame = self.video_capture.read()
        if not ret:
            return None
        
        return frame
    
    def get_frame_bytes(self):
        """
        Get frame as JPEG bytes for streaming.
        
        Returns:
            bytes: JPEG-encoded frame data
        """
        frame = self.get_frame()
        if frame is None:
            return None
        
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return None
        
        return buffer.tobytes()


def detect_faces(frame):
    """
    Detect faces in a frame using OpenCV's Haar Cascade.
    
    Args:
        frame: numpy.ndarray image
    
    Returns:
        list: List of (x, y, w, h) tuples for each detected face
    """
    # Load the cascade classifier
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    
    # Convert to grayscale for detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    
    return faces


def draw_face_boxes(frame, faces, color=(0, 255, 0), thickness=2):
    """
    Draw bounding boxes around detected faces.
    
    Args:
        frame: The image to draw on
        faces: List of (x, y, w, h) face locations
        color: BGR color tuple (default: green)
        thickness: Line thickness in pixels
    
    Returns:
        numpy.ndarray: Frame with face boxes drawn
    """
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
    
    return frame


if __name__ == '__main__':
    # Test camera functionality
    print("Testing camera module...")
    
    cam = Camera()
    try:
        cam.start()
        print("Camera started successfully!")
        
        # Capture a test frame
        frame = cam.get_frame()
        if frame is not None:
            print(f"Frame captured: {frame.shape}")
            
            # Try face detection
            faces = detect_faces(frame)
            print(f"Faces detected: {len(faces)}")
        else:
            print("Failed to capture frame")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cam.stop()
        print("Camera stopped")
