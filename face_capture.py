"""
Guided Face Capture Module
Implements KYC-style multi-pose face capture for robust face encoding.
"""

import cv2
import numpy as np
import pickle
import face_recognition


class GuidedFaceCapture:
    """
    Guides users through a multi-pose face capture process for enrollment.
    
    Captures multiple frames at different poses (center, left, right, up, down,
    smile, neutral) to create a robust face encoding for recognition.
    """
    
    STAGES = [
        {'name': 'center', 'instruction': 'Look straight at the camera'},
        {'name': 'left', 'instruction': 'Turn your head slightly to the left'},
        {'name': 'right', 'instruction': 'Turn your head slightly to the right'},
        {'name': 'up', 'instruction': 'Tilt your chin up slightly'},
        {'name': 'down', 'instruction': 'Look slightly downward'},
        {'name': 'smile', 'instruction': 'Give a natural smile'},
        {'name': 'neutral', 'instruction': 'Relax your face'},
    ]
    
    # Quality thresholds
    MIN_BRIGHTNESS = 40
    MAX_BRIGHTNESS = 220
    MIN_FACE_RATIO = 0.15  # Face width must be >= 15% of frame width
    BLUR_THRESHOLD = 5.0  # Laplacian variance threshold (very lenient for webcams)
    
    def __init__(self, frames_per_pose=3):
        """
        Initialize the guided face capture.
        
        Args:
            frames_per_pose: Number of valid frames to capture per pose stage.
        """
        self.frames_per_pose = frames_per_pose
        self.current_stage_index = 0
        self.encodings = []
        self._completed = False
        
        # Deep copy stages with frame counters
        self.stages = []
        for stage in self.STAGES:
            self.stages.append({
                'name': stage['name'],
                'instruction': stage['instruction'],
                'frames_captured': 0,
            })
    
    def get_current_stage(self):
        """Get the current capture stage."""
        if self.current_stage_index < len(self.stages):
            return self.stages[self.current_stage_index]
        return self.stages[-1]
    
    def get_current_instruction(self):
        """Get the instruction text for the current stage."""
        return self.get_current_stage()['instruction']
    
    def analyze_lighting(self, frame):
        """
        Analyze frame lighting quality.
        
        Args:
            frame: BGR numpy array
        
        Returns:
            dict with 'is_adequate' (bool) and 'message' (str)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        
        if mean_brightness < self.MIN_BRIGHTNESS:
            return {
                'is_adequate': False,
                'message': 'Too dark - please improve lighting',
                'brightness': mean_brightness,
            }
        
        if mean_brightness > self.MAX_BRIGHTNESS:
            return {
                'is_adequate': False,
                'message': 'Too bright - reduce lighting or move away from window',
                'brightness': mean_brightness,
            }
        
        return {
            'is_adequate': True,
            'message': 'Lighting is good',
            'brightness': mean_brightness,
        }
    
    def validate_face_position(self, face_box, frame_width, frame_height):
        """
        Validate face position and size within frame.
        
        Args:
            face_box: Tuple (x, y, w, h) of face bounding box
            frame_width: Width of the frame
            frame_height: Height of the frame
        
        Returns:
            dict with 'is_valid' (bool) and 'message' (str)
        """
        x, y, w, h = face_box
        face_center_x = x + w / 2
        face_center_y = y + h / 2
        
        # Check face size (must be >= MIN_FACE_RATIO of frame width)
        face_ratio = w / frame_width
        if face_ratio < self.MIN_FACE_RATIO:
            return {
                'is_valid': False,
                'message': 'Move closer to the camera',
            }
        
        # Check horizontal position (center 60% of frame)
        left_bound = frame_width * 0.2
        right_bound = frame_width * 0.8
        
        if face_center_x < left_bound:
            return {
                'is_valid': False,
                'message': 'Move to the right',
            }
        
        if face_center_x > right_bound:
            return {
                'is_valid': False,
                'message': 'Move to the left',
            }
        
        # Check vertical position (center 60% of frame)
        top_bound = frame_height * 0.2
        bottom_bound = frame_height * 0.8
        
        if face_center_y < top_bound:
            return {
                'is_valid': False,
                'message': 'Move down',
            }
        
        if face_center_y > bottom_bound:
            return {
                'is_valid': False,
                'message': 'Move up',
            }
        
        return {
            'is_valid': True,
            'message': 'Position is good',
        }
    
    def check_blur(self, frame):
        """
        Check if frame is too blurry using Laplacian variance.
        
        Args:
            frame: BGR numpy array
        
        Returns:
            dict with 'is_sharp' (bool) and 'variance' (float)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        return {
            'is_sharp': laplacian_var >= self.BLUR_THRESHOLD,
            'variance': laplacian_var,
            'message': 'Image is sharp' if laplacian_var >= self.BLUR_THRESHOLD else 'Image is blurry - hold still',
        }
    
    def validate_pose(self, landmarks, stage_name):
        """
        Validate if the current face pose matches the required stage using landmarks.
        
        Args:
            landmarks: dict of face landmarks (chin, nose_bridge, etc.)
            stage_name: str name of the stage (center, left, right, up, down, smile)
            
        Returns:
            dict with 'is_valid' (bool) and 'message' (str)
        """
        # Get key points
        nose_bridge = landmarks['nose_bridge']
        nose_tip = landmarks['nose_tip']
        chin = landmarks['chin']
        left_eye = landmarks['left_eye']
        right_eye = landmarks['right_eye']
        top_lip = landmarks['top_lip']
        bottom_lip = landmarks['bottom_lip']
        
        # Calculate face center X (approximate using eyes)
        left_eye_center = np.mean(left_eye, axis=0)
        right_eye_center = np.mean(right_eye, axis=0)
        face_center_x = (left_eye_center[0] + right_eye_center[0]) / 2
        
        # Calculate nose deviations
        nose_x = np.mean(nose_tip, axis=0)[0]
        nose_y = np.mean(nose_tip, axis=0)[1]
        
        # Horizontal deviation (Yaw)
        # Normalized by eye distance to account for scale
        eye_dist = np.linalg.norm(right_eye_center - left_eye_center)
        yaw_ratio = (nose_x - face_center_x) / eye_dist
        
        # Vertical deviation (Pitch)
        # Use nose bridge top vs nose tip relationship 
        # But easier: relative vertical position of nose tip between eyes and chin
        chin_y = np.mean(chin, axis=0)[1]
        eye_y = (left_eye_center[1] + right_eye_center[1]) / 2
        face_height = chin_y - eye_y
        pitch_ratio = (nose_y - eye_y) / face_height
        
        # Thresholds (tuned empirically - relaxed for typical webcam usage)
        YAW_THRESHOLD = 0.20  # More lenient for center pose
        PITCH_UP_THRESHOLD = 0.45  # Lower value means nose is higher (closer to eyes) - relaxed
        PITCH_DOWN_THRESHOLD = 0.50 # Higher value means nose is lower (closer to chin) - relaxed
        
        if stage_name == 'center' or stage_name == 'neutral':
            if abs(yaw_ratio) > YAW_THRESHOLD:
                direction = "left" if yaw_ratio > 0 else "right" # Inverted? Let's verify.
                # If nose is to the right of center (img coords), user is looking right.
                return {'is_valid': False, 'message': f'Face straight ahead (looking {direction})'}
            return {'is_valid': True, 'message': 'Good center pose'}
            
        elif stage_name == 'left':
            # User looks left -> Nose moves LEFT in image (smaller X)
            if yaw_ratio > -0.03: # Relaxed - just need slight turn
                return {'is_valid': False, 'message': 'Turn head slightly left'}
            return {'is_valid': True, 'message': 'Good left pose'}
            
        elif stage_name == 'right':
            # User looks right -> Nose moves RIGHT in image (larger X)
            if yaw_ratio < 0.03: # Relaxed - just need slight turn
                return {'is_valid': False, 'message': 'Turn head slightly right'}
            return {'is_valid': True, 'message': 'Good right pose'}
            
        elif stage_name == 'up':
            # User looks up -> Nose moves UP (smaller Y relative to face)
            # pitch_ratio decreases
            if pitch_ratio > PITCH_UP_THRESHOLD:
                return {'is_valid': False, 'message': 'Tilt chin up slightly'}
            return {'is_valid': True, 'message': 'Good up pose'}
            
        elif stage_name == 'down':
            # User looks down -> Nose moves DOWN (larger Y)
            if pitch_ratio < PITCH_DOWN_THRESHOLD:
                return {'is_valid': False, 'message': 'Look down slightly'}
            return {'is_valid': True, 'message': 'Good down pose'}
            
        elif stage_name == 'smile':
            # Check mouth width / face width ratio
            mouth_left = top_lip[0]
            mouth_right = top_lip[6]
            mouth_width = np.linalg.norm(np.array(mouth_width_vector := (mouth_right[0] - mouth_left[0], mouth_right[1] - mouth_left[1])))
            
            # Use jaw width as reference
            jaw_width = np.linalg.norm(np.array(chin[16]) - np.array(chin[0]))
            smile_ratio = mouth_width / jaw_width
            
            if smile_ratio < 0.38: # Typical neutral is around 0.3-0.35
                return {'is_valid': False, 'message': 'Please smile!'}
            return {'is_valid': True, 'message': 'Nice smile!'}
            
        return {'is_valid': True, 'message': 'Pose valid'}

    def process_frame(self, frame):
        """
        Process a frame: detect face, check quality, capture encoding if valid.
        
        Args:
            frame: BGR numpy array from camera
        
        Returns:
            tuple: (annotated_frame, status_dict)
        """
        annotated = frame.copy()
        frame_height, frame_width = frame.shape[:2]
        
        # Default status
        status = {
            'stage': self.get_current_stage()['name'],
            'stage_index': self.current_stage_index,
            'instruction': self.get_current_instruction(),
            'progress': f"{sum(s['frames_captured'] for s in self.stages)}/{len(self.stages) * self.frames_per_pose}",
            'is_complete': self.is_complete(),
            'face_detected': False,
            'feedback': '',
            'quality_ok': False,
        }
        
        if self._completed:
            status['feedback'] = 'Capture complete!'
            return annotated, status
        
        # Check lighting first
        lighting = self.analyze_lighting(frame)
        if not lighting['is_adequate']:
            status['feedback'] = lighting['message']
            return annotated, status
        
        # Convert to RGB for face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame, model='hog')
        
        if len(face_locations) == 0:
            status['feedback'] = 'No face detected - please face the camera'
            return annotated, status
        
        if len(face_locations) > 1:
            status['feedback'] = 'Multiple faces detected - only one person please'
            status['face_detected'] = True
            # Draw all faces in yellow
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(annotated, (left, top), (right, bottom), (0, 255, 255), 2)
            return annotated, status
        
        # Single face detected
        status['face_detected'] = True
        top, right, bottom, left = face_locations[0]
        face_box = (left, top, right - left, bottom - top)
        
        # Validate position
        position = self.validate_face_position(face_box, frame_width, frame_height)
        if not position['is_valid']:
            status['feedback'] = position['message']
            cv2.rectangle(annotated, (left, top), (right, bottom), (0, 165, 255), 2)  # Orange
            return annotated, status
        
        # Check blur
        blur = self.check_blur(frame)
        if not blur['is_sharp']:
            status['feedback'] = blur['message']
            cv2.rectangle(annotated, (left, top), (right, bottom), (0, 165, 255), 2)  # Orange
            return annotated, status
            
        # --- POSE VALIDATION ---
        # Get landmarks for pose checking
        landmarks_list = face_recognition.face_landmarks(rgb_frame, face_locations)
        if landmarks_list:
            pose_check = self.validate_pose(landmarks_list[0], status['stage'])
            if not pose_check['is_valid']:
                status['feedback'] = pose_check['message']
                cv2.rectangle(annotated, (left, top), (right, bottom), (0, 165, 255), 2) # Orange
                return annotated, status
        
        # All checks passed - capture encoding
        status['quality_ok'] = True
        status['feedback'] = f"Hold still... {self.get_current_instruction()}"
        cv2.rectangle(annotated, (left, top), (right, bottom), (0, 255, 0), 2)  # Green
        
        # Get face encoding
        encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        if encodings:
            self.add_encoding(encodings[0])
            current_stage = self.get_current_stage()
            current_stage['frames_captured'] += 1
            
            # Check if this stage is complete
            if current_stage['frames_captured'] >= self.frames_per_pose:
                self.advance_stage()
        
        # Update progress in status
        status['progress'] = f"{sum(s['frames_captured'] for s in self.stages)}/{len(self.stages) * self.frames_per_pose}"
        status['is_complete'] = self.is_complete()
        
        if status['is_complete']:
            status['feedback'] = 'Face capture complete!'
        
        return annotated, status
    
    def advance_stage(self):
        """Advance to the next capture stage."""
        if self.current_stage_index < len(self.stages) - 1:
            self.current_stage_index += 1
        else:
            # All stages complete
            self._completed = True
    
    def is_complete(self):
        """Check if all stages have been captured."""
        if self._completed:
            return True
        
        # Check if all stages have required frames
        for stage in self.stages:
            if stage['frames_captured'] < self.frames_per_pose:
                return False
        
        self._completed = True
        return True
    
    def add_encoding(self, encoding):
        """Add a face encoding to the collection."""
        self.encodings.append(np.array(encoding))
    
    def get_aggregated_encoding(self):
        """
        Get the aggregated (averaged) face encoding from all captures.
        
        Returns:
            bytes: Pickled numpy array of the average encoding
        """
        if not self.encodings:
            return b''
        
        # Average all encodings for robustness
        avg_encoding = np.mean(self.encodings, axis=0)
        return pickle.dumps(avg_encoding)
    
    def reset(self):
        """Reset capture state to start fresh."""
        self.current_stage_index = 0
        self.encodings = []
        self._completed = False
        
        for stage in self.stages:
            stage['frames_captured'] = 0
    
    def get_progress_percentage(self):
        """Get capture progress as a percentage."""
        total_needed = len(self.stages) * self.frames_per_pose
        total_captured = sum(s['frames_captured'] for s in self.stages)
        return int((total_captured / total_needed) * 100) if total_needed > 0 else 0
