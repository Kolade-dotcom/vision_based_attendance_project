"""
TDD Test Suite for GuidedFaceCapture class.
Tests written BEFORE implementation (Red phase of Red-Green-Refactor).
"""
import pytest
import numpy as np


# --- Instantiation Tests ---

def test_guided_face_capture_instantiation_defaults():
    """GuidedFaceCapture should instantiate with default parameters."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    
    assert capture is not None
    assert capture.current_stage_index == 0
    assert capture.frames_per_pose == 3
    assert len(capture.stages) == 7
    assert capture.is_complete() is False


def test_guided_face_capture_custom_frames_per_pose():
    """GuidedFaceCapture should accept custom frames_per_pose."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture(frames_per_pose=5)
    
    assert capture.frames_per_pose == 5


def test_stages_in_expected_order():
    """Capture stages should follow the defined order."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    expected_stages = ['center', 'left', 'right', 'up', 'down', 'smile', 'neutral']
    
    assert [s['name'] for s in capture.stages] == expected_stages


# --- Current Stage Tests ---

def test_initial_stage_is_center():
    """Initial capture stage should be 'center'."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    
    assert capture.get_current_stage()['name'] == 'center'


def test_get_current_instruction_returns_string():
    """Should return instruction text for current stage."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    instruction = capture.get_current_instruction()
    
    assert isinstance(instruction, str)
    assert len(instruction) > 0


# --- Lighting Analysis Tests ---

def test_dark_frame_detected_as_poor_lighting():
    """Very dark frames should be flagged as poor lighting."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    dark_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    quality = capture.analyze_lighting(dark_frame)
    
    assert quality['is_adequate'] is False


def test_medium_brightness_frame_acceptable():
    """Adequately lit frames should pass lighting check."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    bright_frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    
    quality = capture.analyze_lighting(bright_frame)
    
    assert quality['is_adequate'] is True


def test_overexposed_frame_detected():
    """Very bright/overexposed frames should be flagged."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    overexposed = np.full((480, 640, 3), 250, dtype=np.uint8)
    
    quality = capture.analyze_lighting(overexposed)
    
    assert quality['is_adequate'] is False


# --- Face Position Validation Tests ---

def test_centered_face_is_valid():
    """Face in center of frame should be valid."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    frame_width, frame_height = 640, 480
    face_box = (220, 140, 200, 200)  # Roughly centered
    
    result = capture.validate_face_position(face_box, frame_width, frame_height)
    
    assert result['is_valid'] is True


def test_face_too_far_left_invalid():
    """Face on far left edge should be invalid."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    frame_width, frame_height = 640, 480
    face_box = (10, 140, 100, 100)
    
    result = capture.validate_face_position(face_box, frame_width, frame_height)
    
    assert result['is_valid'] is False
    assert 'right' in result['message'].lower()


def test_face_too_small_invalid():
    """Face that is too small should be invalid."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    frame_width, frame_height = 640, 480
    face_box = (270, 200, 50, 50)  # Only ~8% of frame width
    
    result = capture.validate_face_position(face_box, frame_width, frame_height)
    
    assert result['is_valid'] is False
    assert 'closer' in result['message'].lower()


# --- Blur Detection Tests ---

def test_sharp_image_passes_blur_check():
    """Sharp image with edges should pass blur check."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    sharp = np.zeros((480, 640, 3), dtype=np.uint8)
    sharp[::20, :, :] = 255  # Horizontal lines
    sharp[:, ::20, :] = 255  # Vertical lines
    
    result = capture.check_blur(sharp)
    
    assert result['is_sharp'] == True


def test_uniform_image_fails_blur_check():
    """Completely uniform (blurry) image should fail."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    blurry = np.full((480, 640, 3), 128, dtype=np.uint8)
    
    result = capture.check_blur(blurry)
    
    assert result['is_sharp'] == False


# --- Frame Processing Tests ---

def test_process_frame_returns_tuple():
    """process_frame should return (annotated_frame, status_dict)."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    result = capture.process_frame(frame)
    
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_process_frame_status_contains_required_fields():
    """Status dict should contain all required fields."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    _, status = capture.process_frame(frame)
    
    required_fields = ['stage', 'instruction', 'progress', 'is_complete', 'face_detected', 'feedback']
    for field in required_fields:
        assert field in status


def test_no_face_gives_appropriate_feedback():
    """When no face detected, feedback should indicate this."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    _, status = capture.process_frame(blank_frame)
    
    assert status['face_detected'] is False


# --- Stage Progression Tests ---

def test_advance_stage_increments_index():
    """advance_stage should move to next stage."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    initial_index = capture.current_stage_index
    
    capture.advance_stage()
    
    assert capture.current_stage_index == initial_index + 1


def test_cannot_advance_past_last_stage():
    """Should not advance beyond the last stage."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    
    for _ in range(10):
        capture.advance_stage()
    
    assert capture.current_stage_index == len(capture.stages) - 1


def test_is_complete_after_all_stages_finished():
    """is_complete should return True after all stages finished."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    
    # Mark all stages as having enough frames
    for stage in capture.stages:
        stage['frames_captured'] = capture.frames_per_pose
    capture.current_stage_index = len(capture.stages) - 1
    capture.advance_stage()
    
    assert capture.is_complete() is True


# --- Encoding Tests ---

def test_encodings_list_initially_empty():
    """Encodings list should be empty on init."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    
    assert len(capture.encodings) == 0


def test_add_encoding_stores_data():
    """add_encoding should store the encoding."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    mock_encoding = np.random.rand(128)
    
    capture.add_encoding(mock_encoding)
    
    assert len(capture.encodings) == 1


def test_get_aggregated_encoding_returns_bytes():
    """get_aggregated_encoding should return serialized bytes."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    for _ in range(3):
        capture.add_encoding(np.random.rand(128))
    
    result = capture.get_aggregated_encoding()
    
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_aggregated_encoding_is_average():
    """Aggregated encoding should be the mean of all encodings."""
    from face_capture import GuidedFaceCapture
    import pickle
    
    capture = GuidedFaceCapture()
    
    enc1 = np.array([1.0] * 128)
    enc2 = np.array([3.0] * 128)
    capture.add_encoding(enc1)
    capture.add_encoding(enc2)
    
    result_bytes = capture.get_aggregated_encoding()
    result = pickle.loads(result_bytes)
    
    expected = np.array([2.0] * 128)
    np.testing.assert_array_almost_equal(result, expected)


# --- Reset Tests ---

def test_reset_clears_state():
    """reset should clear all captured data and return to start."""
    from face_capture import GuidedFaceCapture
    
    capture = GuidedFaceCapture()
    
    capture.current_stage_index = 3
    capture.add_encoding(np.random.rand(128))
    
    capture.reset()
    
    assert capture.current_stage_index == 0
    assert len(capture.encodings) == 0
    assert capture.is_complete() is False
