import pytest
import os
import sys
import tempfile
import sqlite3

# Add root directory to sys.path to resolve imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import db_helper


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app.config['TESTING'] = True
    
    # Save original path to restore later
    original_path = db_helper.DATABASE_PATH
    db_helper.DATABASE_PATH = db_path
    
    # Set up the database for testing
    with app.test_client() as client:
        with app.app_context():
            db_helper.init_database()
        yield client

    # Clean up
    db_helper.DATABASE_PATH = original_path
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def db():
    db_fd, db_path = tempfile.mkstemp()
    # Save original path to restore later
    original_path = db_helper.DATABASE_PATH
    db_helper.DATABASE_PATH = db_path
    
    # Set up the database for testing
    db_helper.init_database()
    
    yield db_helper
    
    # Clean up
    db_helper.DATABASE_PATH = original_path
    os.close(db_fd)
    os.unlink(db_path)
