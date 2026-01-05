"""
Camera Module
Handles OpenCV webcam capture and face recognition logic.
"""

import cv2
import numpy as np

# Uncomment when face_recognition is installed
import face_recognition


class Camera:
    """Handles webcam capture and frame processing with optimized face detection."""
    
    def __init__(self, camera_index=0, scale_factor=0.25, frame_skip=2):
        """
        Initialize the camera with detection optimizations.
        
        Args:
            camera_index: Index of the camera device (default: 0 for primary webcam)
            scale_factor: Resize factor for detection (default: 0.25 = 25% size)
            frame_skip: Process every Nth frame (default: 2)
        """
        self.camera_index = camera_index
        self.video_capture = None
        
        # Optimization parameters
        self.scale_factor = scale_factor
        self.frame_skip = frame_skip
        self.frame_count = 0
        self.cached_faces = []
        
        # Cache Haar Cascade classifier (load once, not per frame)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    
    def start(self):
        """Start the video capture."""
        if self.video_capture is not None and self.video_capture.isOpened():
            return True # Already started

        self.video_capture = cv2.VideoCapture(self.camera_index)
        if not self.video_capture.isOpened():
            raise RuntimeError(f"Could not open camera at index {self.camera_index}")
        
        # Reset frame counter on start
        self.frame_count = 0
        self.cached_faces = []
        return True
    
    def stop(self):
        """Stop the video capture and release resources."""
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None
        self.cached_faces = []
    
    def get_frame(self):
        """
        Capture a single frame from the camera.
        
        Returns:
            numpy.ndarray: The captured frame, or None if capture failed
        """
        if self.video_capture is None or not self.video_capture.isOpened():
            return None
        
        ret, frame = self.video_capture.read()
        if not ret:
            return None
        
        return frame
    
    def detect_faces_optimized(self, frame):
        """
        Detect faces with performance optimizations.
        
        - Resizes frame to scale_factor before processing
        - Skips frames based on frame_skip setting
        - Caches and returns previous detections for skipped frames
        - Scales bounding boxes back to original size
        
        Args:
            frame: Full-resolution numpy.ndarray image
        
        Returns:
            list: List of (x, y, w, h) tuples scaled to original frame size
        """
        self.frame_count += 1
        
        # Skip frames: return cached faces for non-processed frames
        if self.frame_count % self.frame_skip != 0:
            return self.cached_faces
        
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces on smaller frame
        faces_small = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(20, 20)  # Smaller min size for scaled frame
        )
        
        # Scale bounding boxes back to original frame size
        scale = 1.0 / self.scale_factor
        self.cached_faces = [
            (int(x * scale), int(y * scale), int(w * scale), int(h * scale))
            for (x, y, w, h) in faces_small
        ]
        
        return self.cached_faces
    
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

# Global Singleton Instance
_camera_instance = None

def get_camera():
    """Get or create the global camera instance."""
    global _camera_instance
    if _camera_instance is None:
        _camera_instance = Camera()
    return _camera_instance


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
    
    cam = get_camera()
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
