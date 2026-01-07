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


class FaceDetector:
    """
    Advanced face detector using face_recognition library with HOG model.
    
    Features:
    - HOG-based detection (more robust than Haar)
    - Frame skipping for performance
    - Temporal smoothing for stable bounding boxes
    - IoU-based face tracking across frames
    """
    
    def __init__(self, model="hog", scale=0.5, skip_frames=2, smoothing_window=3):
        """
        Initialize the FaceDetector.
        
        Args:
            model: Detection model - "hog" (fast) or "cnn" (accurate, needs GPU)
            scale: Downscale factor for performance (0.5 = half size)
            skip_frames: Process every Nth frame (cache results for others)
            smoothing_window: Number of frames to average for smoothing
        """
        self.model = model
        self.scale = scale
        self.skip_frames = skip_frames
        self.smoothing_window = smoothing_window
        
        self.frame_count = 0
        self.cached_faces = []
        self.detection_history = []  # For temporal smoothing
    
    def detect(self, frame):
        """
        Detect faces in a frame.
        
        Args:
            frame: BGR numpy array from OpenCV
        
        Returns:
            list: List of (x, y, w, h) tuples for each detected face
        """
        self.frame_count += 1
        
        # Skip frames optimization
        if self.frame_count % self.skip_frames != 0:
            return self.cached_faces
        
        # Resize for performance
        small_frame = cv2.resize(frame, (0, 0), fx=self.scale, fy=self.scale)
        
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces using face_recognition (returns top, right, bottom, left)
        face_locations = face_recognition.face_locations(rgb_frame, model=self.model)
        
        # Convert to (x, y, w, h) format and scale back
        faces = []
        for (top, right, bottom, left) in face_locations:
            x = int(left / self.scale)
            y = int(top / self.scale)
            w = int((right - left) / self.scale)
            h = int((bottom - top) / self.scale)
            faces.append((x, y, w, h))
        
        # Apply temporal smoothing
        self.detection_history.append(faces)
        if len(self.detection_history) > self.smoothing_window:
            self.detection_history.pop(0)
        
        # Smooth detections if we have history
        if len(self.detection_history) >= 2:
            self.cached_faces = self._smooth_detections(self.detection_history)
        else:
            self.cached_faces = faces
        
        return self.cached_faces
    
    def _scale_boxes(self, boxes, scale_factor):
        """Scale bounding boxes back to original frame size."""
        return [
            (int(x / scale_factor), int(y / scale_factor), 
             int(w / scale_factor), int(h / scale_factor))
            for (x, y, w, h) in boxes
        ]
    
    def _calculate_iou(self, box1, box2):
        """
        Calculate Intersection over Union between two boxes.
        
        Args:
            box1, box2: Tuples of (x, y, w, h)
        
        Returns:
            float: IoU value between 0 and 1
        """
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        # Calculate intersection
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0  # No overlap
        
        intersection = (xi2 - xi1) * (yi2 - yi1)
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _smooth_detections(self, history):
        """
        Smooth face detections across multiple frames.
        
        Uses IoU to match faces across frames and averages positions.
        
        Args:
            history: List of detection lists from recent frames
        
        Returns:
            list: Smoothed face positions
        """
        if not history or not history[-1]:
            return []
        
        current_faces = history[-1]
        if len(history) < 2:
            return current_faces
        
        # Average with previous detections using IoU matching
        smoothed = []
        for face in current_faces:
            matched_positions = [face]
            
            # Find matching faces in previous frames
            for prev_faces in history[:-1]:
                best_match = None
                best_iou = 0.3  # Minimum IoU threshold
                
                for prev_face in prev_faces:
                    iou = self._calculate_iou(face, prev_face)
                    if iou > best_iou:
                        best_iou = iou
                        best_match = prev_face
                
                if best_match:
                    matched_positions.append(best_match)
            
            # Average the matched positions
            if matched_positions:
                avg_x = int(sum(f[0] for f in matched_positions) / len(matched_positions))
                avg_y = int(sum(f[1] for f in matched_positions) / len(matched_positions))
                avg_w = int(sum(f[2] for f in matched_positions) / len(matched_positions))
                avg_h = int(sum(f[3] for f in matched_positions) / len(matched_positions))
                smoothed.append((avg_x, avg_y, avg_w, avg_h))
        
        return smoothed


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
