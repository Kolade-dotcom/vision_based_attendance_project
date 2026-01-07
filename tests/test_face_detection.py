"""
Test suite for FaceDetector class.
TDD: These tests are written BEFORE implementation.
"""
import pytest
import numpy as np
from camera import FaceDetector


# --- Instantiation Tests ---

def test_face_detector_instantiation_default_params():
    """FaceDetector should instantiate with default parameters."""
    detector = FaceDetector()
    assert detector is not None
    assert detector.model == "hog"
    assert detector.scale == 0.5
    assert detector.skip_frames == 2


def test_face_detector_instantiation_custom_params():
    """FaceDetector should accept custom parameters."""
    detector = FaceDetector(model="cnn", scale=0.25, skip_frames=3)
    assert detector.model == "cnn"
    assert detector.scale == 0.25
    assert detector.skip_frames == 3


# --- Detection Tests ---

def test_detect_returns_list():
    """detect() should return a list (even if empty)."""
    detector = FaceDetector(model="hog", scale=0.5, skip_frames=1)
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = detector.detect(blank_frame)
    assert isinstance(result, list)


def test_detect_blank_frame_returns_empty():
    """detect() on blank frame should return empty list."""
    detector = FaceDetector(model="hog", scale=0.5, skip_frames=1)
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = detector.detect(blank_frame)
    assert result == []


# --- Bounding Box Scaling Tests ---

def test_scale_boxes_to_original_size():
    """Detected boxes should be scaled to original frame dimensions."""
    detector = FaceDetector(scale=0.5)
    
    # Simulate detection at half scale
    small_boxes = [(50, 50, 100, 100)]  # Detection at 0.5x
    
    # Scale back
    scaled = detector._scale_boxes(small_boxes, scale_factor=0.5)
    
    # Should be 2x the size
    assert scaled[0] == (100, 100, 200, 200)


# --- Frame Skipping Tests ---

def test_returns_cached_on_skip():
    """Should return cached faces on skipped frames."""
    detector = FaceDetector(skip_frames=2)
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # First call - process
    result1 = detector.detect(blank)
    
    # Second call - should skip and return cached
    result2 = detector.detect(blank)
    
    # Both should be same (from cache on second call)
    assert result1 == result2


# --- Temporal Smoothing Tests ---

def test_smooth_reduces_jitter():
    """Smoothing should reduce position jitter between frames."""
    detector = FaceDetector()
    
    # Simulate face at different positions (jittery)
    positions = [
        [(100, 100, 50, 50)],
        [(102, 98, 50, 50)],   # Slight jitter
        [(99, 101, 50, 50)],   # Slight jitter
    ]
    
    smoothed = detector._smooth_detections(positions)
    
    # Smoothed position should be average
    assert len(smoothed) == 1
    x, y, w, h = smoothed[0]
    assert 99 <= x <= 101  # Close to 100
    assert 99 <= y <= 101  # Close to 100


# --- IoU Tracking Tests ---

def test_iou_calculation_perfect_overlap():
    """IoU should be 1.0 for identical boxes."""
    detector = FaceDetector()
    
    box1 = (0, 0, 100, 100)
    box2 = (0, 0, 100, 100)  # Same box
    
    iou = detector._calculate_iou(box1, box2)
    assert iou == 1.0


def test_iou_no_overlap():
    """IoU should be 0 for non-overlapping boxes."""
    detector = FaceDetector()
    
    box1 = (0, 0, 50, 50)
    box2 = (100, 100, 50, 50)  # No overlap
    
    iou = detector._calculate_iou(box1, box2)
    assert iou == 0.0


def test_iou_partial_overlap():
    """IoU should calculate correct value for partial overlap."""
    detector = FaceDetector()
    
    box1 = (0, 0, 100, 100)
    box2 = (50, 50, 100, 100)  # 50% overlap on each axis
    
    iou = detector._calculate_iou(box1, box2)
    # Intersection: 50x50 = 2500
    # Union: 100x100 + 100x100 - 2500 = 17500
    # IoU = 2500/17500 ≈ 0.143
    assert 0.1 < iou < 0.2
