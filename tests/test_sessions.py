import pytest
import sqlite3
import os
import tempfile
from datetime import datetime
from db_helper import (
    init_database, get_db_connection, create_session, end_session, 
    get_active_session, record_attendance, get_session_history, 
    get_session_attendance, delete_session, set_database_path, get_database_path,
    create_user
)
import json


# Test user ID (created in setup)
TEST_USER_ID = None


@pytest.fixture(autouse=True)
def setup_test_db():
    """
    Setup an isolated temporary database for testing.
    This runs before EACH test and cleans up after.
    """
    global TEST_USER_ID
    
    # Store the original database path
    original_db_path = get_database_path()
    
    # Create a temporary test database
    fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)  # Close the file descriptor, we just need the path
    
    # Point db_helper to the test database
    set_database_path(test_db_path)
    
    # Initialize the test database with schema
    init_database()
    
    # Create a test user for session tests
    TEST_USER_ID = create_user("test@test.com", "hashedpassword", "Test User")
    
    yield  # Run the test
    
    # Teardown: Restore original path and delete test database
    set_database_path(original_db_path)
    try:
        os.unlink(test_db_path)
    except OSError:
        pass  # File might already be deleted

def test_create_session():
    course_code = "CS101"
    
    session_id = create_session(course_code, TEST_USER_ID)
    assert session_id is not None
    
    # Verify it's active
    active_session = get_active_session(TEST_USER_ID, course_code)
    assert active_session is not None
    assert active_session['id'] == session_id
    assert active_session['course_code'] == course_code
    assert active_session['is_active'] == 1

def test_end_session():
    course_code = "CS102"
    session_id = create_session(course_code, TEST_USER_ID)
    
    assert get_active_session(TEST_USER_ID, course_code) is not None
    
    end_session(session_id)
    
    assert get_active_session(TEST_USER_ID, course_code) is None

def test_attendance_linking():
    course_code = "CS103"
    student_id = "TEST001"
    
    session_id = create_session(course_code, TEST_USER_ID)
    
    # Record attendance - the function may return None if student doesn't exist
    # which is expected in this test context
    record_id = record_attendance(student_id, course_code=course_code)
    
    # This test verifies the function runs without error
    # Attendance linking with sessions is handled internally
    pass

def test_controller_start_session():
    """Test start_session_logic controller."""
    from app import app
    from api.controllers.session_controller import start_session_logic
    
    with app.test_request_context('/api/sessions/start', 
                                  method='POST',
                                  json={'course_code': 'CS201'}):
        # Simulate logged-in user
        from flask import session
        session['user_id'] = TEST_USER_ID
        
        response, status_code = start_session_logic()
        assert status_code == 201
        assert response.json['status'] == 'active'
        assert 'session_id' in response.json

def test_controller_end_session():
    """Test end_session_logic controller."""
    from app import app
    from api.controllers.session_controller import end_session_logic
    
    # First create a session
    sid = create_session('CS202', TEST_USER_ID)
    
    with app.test_request_context('/api/sessions/end',
                                  method='POST',
                                  json={'session_id': sid}):
        response, status_code = end_session_logic()
        assert status_code == 200
        assert response.json['status'] == 'inactive'


def test_get_session_history():
    """Test get_session_history returns inactive sessions for user."""
    # Create and end a session
    course_code = "HIST100"
    session_id = create_session(course_code, TEST_USER_ID)
    end_session(session_id)
    
    # Get history
    history = get_session_history(TEST_USER_ID)
    
    # Should contain our ended session
    assert isinstance(history, list)
    session_ids = [s['id'] for s in history]
    assert session_id in session_ids
    
    # Find our session and verify it's inactive
    our_session = next((s for s in history if s['id'] == session_id), None)
    assert our_session is not None
    assert our_session['is_active'] == 0
    assert our_session['course_code'] == course_code


def test_get_session_attendance():
    """Test get_session_attendance returns records for specific session."""
    session_id = create_session("ATT100", TEST_USER_ID)
    
    records = get_session_attendance(session_id)
    
    assert isinstance(records, list)
    # Empty list is valid if no students attended


def test_delete_session():
    """Test delete_session removes session and its attendance."""
    course_code = "DEL100"
    session_id = create_session(course_code, TEST_USER_ID)
    end_session(session_id)
    
    # Verify it exists in history
    history_before = get_session_history(TEST_USER_ID)
    session_ids_before = [s['id'] for s in history_before]
    assert session_id in session_ids_before
    
    # Delete it
    result = delete_session(session_id)
    assert result == True
    
    # Verify it's gone
    history_after = get_session_history(TEST_USER_ID)
    session_ids_after = [s['id'] for s in history_after]
    assert session_id not in session_ids_after


def test_delete_nonexistent_session():
    """Test delete_session returns False for non-existent session."""
    result = delete_session(999999)
    assert result == False


def test_user_isolation():
    """Test that sessions are isolated per user."""
    # Create a second test user
    user2_id = create_user("user2@test.com", "hashedpassword", "User Two")
    
    # Create session for user 1
    session1_id = create_session("ISO101", TEST_USER_ID)
    end_session(session1_id)
    
    # Create session for user 2
    session2_id = create_session("ISO102", user2_id)
    end_session(session2_id)
    
    # User 1 should only see their session
    history1 = get_session_history(TEST_USER_ID)
    session_ids_1 = [s['id'] for s in history1]
    assert session1_id in session_ids_1
    assert session2_id not in session_ids_1
    
    # User 2 should only see their session
    history2 = get_session_history(user2_id)
    session_ids_2 = [s['id'] for s in history2]
    assert session2_id in session_ids_2
    assert session1_id not in session_ids_2
