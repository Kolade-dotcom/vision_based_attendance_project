import pytest
import os
import sys
import tempfile
import sqlite3

# Add root directory to sys.path to resolve imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db_helper


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    
    # Save original path to restore later
    original_path = db_helper.get_database_path()
    db_helper.set_database_path(db_path)
    
    # Import app here. Now db_helper is pointing to temp db, so init_database (if called at import)
    # will run on temp db.
    from app import app
    app.config['TESTING'] = True
    
    # Set up the database for testing (schema, etc)
    with app.app_context():
        db_helper.init_database()
        
    with app.test_client() as client:
        yield client

    # Clean up
    db_helper.set_database_path(original_path)
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def db():
    db_fd, db_path = tempfile.mkstemp()
    # Save original path to restore later
    original_path = db_helper.get_database_path()
    db_helper.set_database_path(db_path)
    
    # Set up the database for testing
    db_helper.init_database()
    
    yield db_helper
    
    # Clean up
    db_helper.set_database_path(original_path)
    os.close(db_fd)
    os.unlink(db_path)
