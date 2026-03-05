"""
Face Processor Module
Handles processing of uploaded face images for self-enrollment.
"""

import base64
import numpy as np
import cv2
import face_recognition


def process_face_image(image_base64):
    """
    Process a base64-encoded image and generate face encoding.
    
    Args:
        image_base64: Base64-encoded image string (with or without data URI prefix)
    
    Returns:
        dict: {
            'status': 'success' | 'error',
            'face_encoding': base64_encoded_bytes (if success),
            'error': error message (if error)
        }
    """
    try:
        # Remove data URI prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_base64)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        
        # Decode image
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return {
                'status': 'error',
                'error': 'Could not decode image'
            }
        
        # Horizontal flip for mirror consistency (matching dashboard/enrollment feed)
        image = cv2.flip(image, 1)
        
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_image, model='hog')
        
        if len(face_locations) == 0:
            return {
                'status': 'error',
                'error': 'No face detected in image. Please ensure your face is clearly visible.'
            }
        
        if len(face_locations) > 1:
            return {
                'status': 'error',
                'error': 'Multiple faces detected. Please ensure only one face is in the frame.'
            }
        
        # Get face encoding
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        if len(face_encodings) == 0:
            return {
                'status': 'error',
                'error': 'Could not generate face encoding. Please try again with better lighting.'
            }
        
        # Serialize the encoding
        encoding_bytes = face_encodings[0].tobytes()
        encoding_b64 = base64.b64encode(encoding_bytes).decode('utf-8')
        
        return {
            'status': 'success',
            'face_encoding': encoding_b64
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': f'Error processing image: {str(e)}'
        }


def validate_face_quality(image_base64):
    """
    Validate face image quality without generating encoding.
    Used for real-time feedback during capture.
    
    Args:
        image_base64: Base64-encoded image string
    
    Returns:
        dict: {
            'status': 'success' | 'error',
            'face_detected': bool,
            'face_count': int,
            'message': feedback message
        }
    """
    try:
        # Remove data URI prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_base64)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        
        # Decode image
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return {
                'status': 'error',
                'face_detected': False,
                'face_count': 0,
                'message': 'Could not decode image'
            }
        
        # Horizontal flip for mirror consistency
        image = cv2.flip(image, 1)
        
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces (using faster model for real-time feedback)
        face_locations = face_recognition.face_locations(rgb_image, model='hog')
        
        face_count = len(face_locations)
        
        if face_count == 0:
            return {
                'status': 'success',
                'face_detected': False,
                'face_count': 0,
                'message': 'No face detected. Please position your face in the frame.'
            }
        
        if face_count > 1:
            return {
                'status': 'success',
                'face_detected': True,
                'face_count': face_count,
                'message': 'Multiple faces detected. Please ensure only one face is visible.'
            }
        
        # Check face size (ensure it's large enough)
        top, right, bottom, left = face_locations[0]
        face_height = bottom - top
        face_width = right - left
        
        image_height, image_width = rgb_image.shape[:2]
        
        face_area_ratio = (face_height * face_width) / (image_height * image_width)
        
        if face_area_ratio < 0.05:
            return {
                'status': 'success',
                'face_detected': True,
                'face_count': 1,
                'message': 'Face too small. Please move closer to the camera.'
            }
        
        if face_area_ratio > 0.6:
            return {
                'status': 'success',
                'face_detected': True,
                'face_count': 1,
                'message': 'Face too close. Please move back slightly.'
            }
        
        return {
            'status': 'success',
            'face_detected': True,
            'face_count': 1,
            'message': 'Face detected. Ready to capture.'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'face_detected': False,
            'face_count': 0,
            'message': f'Error: {str(e)}'
        }


def process_multiple_face_images(images_base64):
    """
    Process multiple base64-encoded images and generate an averaged face encoding.
    This implements the same aggregation logic as the server-side GuidedFaceCapture.
    
    Args:
        images_base64: List of base64-encoded image strings
    
    Returns:
        dict: {
            'status': 'success' | 'error',
            'face_encoding': base64_encoded_bytes (if success),
            'image_count': number of images successfully processed,
            'error': error message (if error)
        }
    """
    import logging
    logger = logging.getLogger(__name__)

    encodings = []
    failed_count = 0

    for i, image_base64 in enumerate(images_base64):
        try:
            # Remove data URI prefix if present
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]

            # Decode base64 to bytes
            image_bytes = base64.b64decode(image_base64)
            logger.info(f"Image {i}: {len(image_bytes)} bytes after b64 decode")

            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)

            # Decode image
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                logger.warning(f"Image {i}: cv2.imdecode returned None")
                failed_count += 1
                continue

            logger.info(f"Image {i}: decoded to {image.shape}")

            # Horizontal flip for mirror consistency
            image = cv2.flip(image, 1)

            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect faces
            face_locations = face_recognition.face_locations(rgb_image, model='hog')
            logger.info(f"Image {i}: {len(face_locations)} face(s) detected")

            if len(face_locations) != 1:
                failed_count += 1
                continue

            # Get face encoding
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

            if len(face_encodings) > 0:
                encodings.append(np.array(face_encodings[0]))
            else:
                logger.warning(f"Image {i}: face_encodings returned empty")
                failed_count += 1

        except Exception as e:
            logger.error(f"Error processing image {i}: {e}")
            failed_count += 1
            continue
    
    if len(encodings) < 3:
        return {
            'status': 'error',
            'error': f'Could not extract enough face encodings. Only {len(encodings)} of {len(images_base64)} images were valid. Please ensure proper lighting and face visibility.',
            'image_count': len(encodings)
        }
    
    # Average all encodings for robustness (same as GuidedFaceCapture)
    avg_encoding = np.mean(encodings, axis=0)
    
    # Serialize the averaged encoding
    encoding_bytes = avg_encoding.tobytes()
    encoding_b64 = base64.b64encode(encoding_bytes).decode('utf-8')
    
    return {
        'status': 'success',
        'face_encoding': encoding_b64,
        'image_count': len(encodings)
    }


def validate_pose_from_image(image_base64, expected_pose):
    """
    Validate if the face in an image matches the expected pose.
    Uses the same pose validation logic as server-side GuidedFaceCapture.
    
    Args:
        image_base64: Base64-encoded image string
        expected_pose: One of 'center', 'left', 'right', 'up', 'down', 'smile', 'neutral'
    
    Returns:
        dict: {
            'status': 'success' | 'error',
            'pose_valid': bool,
            'message': feedback message
        }
    """
    try:
        # Remove data URI prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return {'status': 'error', 'pose_valid': False, 'message': 'Could not decode image'}
        
        # Horizontal flip for mirror consistency
        image = cv2.flip(image, 1)
        
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_image, model='hog')
        
        if len(face_locations) == 0:
            return {'status': 'success', 'pose_valid': False, 'message': 'No face detected'}
        
        if len(face_locations) > 1:
            return {'status': 'success', 'pose_valid': False, 'message': 'Multiple faces detected'}
        
        # Get face landmarks for pose validation
        landmarks_list = face_recognition.face_landmarks(rgb_image, face_locations)
        
        if not landmarks_list:
            return {'status': 'success', 'pose_valid': False, 'message': 'Could not detect face landmarks'}
        
        landmarks = landmarks_list[0]
        
        # Validate pose using landmarks (same logic as GuidedFaceCapture.validate_pose)
        pose_result = _validate_pose(landmarks, expected_pose)
        
        return {
            'status': 'success',
            'pose_valid': pose_result['is_valid'],
            'message': pose_result['message']
        }
        
    except Exception as e:
        return {'status': 'error', 'pose_valid': False, 'message': f'Error: {str(e)}'}


def _validate_pose(landmarks, stage_name):
    """
    Validate if the current face pose matches the required stage using landmarks.
    Ported from GuidedFaceCapture.validate_pose().
    """
    # Get key points
    nose_bridge = landmarks['nose_bridge']
    nose_tip = landmarks['nose_tip']
    chin = landmarks['chin']
    left_eye = landmarks['left_eye']
    right_eye = landmarks['right_eye']
    top_lip = landmarks['top_lip']
    
    # Calculate face center X (approximate using eyes)
    left_eye_center = np.mean(left_eye, axis=0)
    right_eye_center = np.mean(right_eye, axis=0)
    face_center_x = (left_eye_center[0] + right_eye_center[0]) / 2
    
    # Calculate nose deviations
    nose_x = np.mean(nose_tip, axis=0)[0]
    nose_y = np.mean(nose_tip, axis=0)[1]
    
    # Horizontal deviation (Yaw) - normalized by eye distance
    eye_dist = np.linalg.norm(np.array(right_eye_center) - np.array(left_eye_center))
    if eye_dist == 0:
        return {'is_valid': False, 'message': 'Cannot calculate pose'}
    
    yaw_ratio = (nose_x - face_center_x) / eye_dist
    
    # Vertical deviation (Pitch)
    chin_y = np.mean(chin, axis=0)[1]
    eye_y = (left_eye_center[1] + right_eye_center[1]) / 2
    face_height = chin_y - eye_y
    
    if face_height == 0:
        return {'is_valid': False, 'message': 'Cannot calculate pose'}
    
    pitch_ratio = (nose_y - eye_y) / face_height
    
    # Thresholds (relaxed for webcam usage)
    YAW_THRESHOLD = 0.20
    PITCH_UP_THRESHOLD = 0.45
    PITCH_DOWN_THRESHOLD = 0.50
    
    if stage_name == 'center' or stage_name == 'neutral':
        if abs(yaw_ratio) > YAW_THRESHOLD:
            direction = "right" if yaw_ratio > 0 else "left"
            return {'is_valid': False, 'message': f'Face straight ahead (looking {direction})'}
        return {'is_valid': True, 'message': 'Good center pose'}
        
    elif stage_name == 'left':
        if yaw_ratio > -0.05:
            return {'is_valid': False, 'message': 'Turn head slightly left'}
        return {'is_valid': True, 'message': 'Good left pose'}
        
    elif stage_name == 'right':
        if yaw_ratio < 0.05:
            return {'is_valid': False, 'message': 'Turn head slightly right'}
        return {'is_valid': True, 'message': 'Good right pose'}
        
    elif stage_name == 'up':
        if pitch_ratio > PITCH_UP_THRESHOLD:
            return {'is_valid': False, 'message': 'Tilt chin up slightly'}
        return {'is_valid': True, 'message': 'Good up pose'}
        
    elif stage_name == 'down':
        if pitch_ratio < PITCH_DOWN_THRESHOLD:
            return {'is_valid': False, 'message': 'Look down slightly'}
        return {'is_valid': True, 'message': 'Good down pose'}
        
    elif stage_name == 'smile':
        # Check mouth width / face width ratio
        mouth_left = top_lip[0]
        mouth_right = top_lip[6]
        mouth_width = np.sqrt((mouth_right[0] - mouth_left[0])**2 + (mouth_right[1] - mouth_left[1])**2)
        
        jaw_width = np.sqrt((chin[16][0] - chin[0][0])**2 + (chin[16][1] - chin[0][1])**2)
        
        if jaw_width == 0:
            return {'is_valid': False, 'message': 'Cannot detect smile'}
        
        smile_ratio = mouth_width / jaw_width
        
        if smile_ratio < 0.38:
            return {'is_valid': False, 'message': 'Please smile!'}
        return {'is_valid': True, 'message': 'Nice smile!'}
        
    return {'is_valid': True, 'message': 'Pose valid'}
