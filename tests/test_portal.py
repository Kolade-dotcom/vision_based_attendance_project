import pytest
import os
import tempfile
import db_helper
from app import app


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create isolated test database."""
    original_path = db_helper.get_database_path()
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    db_helper.set_database_path(path)
    db_helper.init_database()
    yield
    db_helper.set_database_path(original_path)
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-key'
    with app.test_client() as client:
        yield client


class TestPortalAuth:
    def test_student_signup(self, client):
        resp = client.post('/api/portal/auth/signup', json={
            'matric_number': '125/22/1/0001',
            'name': 'Test Student',
            'email': 'test@uni.edu',
            'password': 'password123'
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['status'] == 'success'
        assert data['is_enrolled'] == False

    def test_student_signup_duplicate(self, client):
        client.post('/api/portal/auth/signup', json={
            'matric_number': '125/22/1/0002',
            'name': 'Student A',
            'password': 'password123'
        })
        resp = client.post('/api/portal/auth/signup', json={
            'matric_number': '125/22/1/0002',
            'name': 'Student B',
            'password': 'password123'
        })
        assert resp.status_code == 409

    def test_student_login(self, client):
        client.post('/api/portal/auth/signup', json={
            'matric_number': '125/22/1/0003',
            'name': 'Login Test',
            'password': 'mypassword'
        })
        resp = client.post('/api/portal/auth/login', json={
            'matric_number': '125/22/1/0003',
            'password': 'mypassword'
        })
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'success'

    def test_student_login_wrong_password(self, client):
        client.post('/api/portal/auth/signup', json={
            'matric_number': '125/22/1/0004',
            'name': 'Wrong PW',
            'password': 'correct'
        })
        resp = client.post('/api/portal/auth/login', json={
            'matric_number': '125/22/1/0004',
            'password': 'wrong'
        })
        assert resp.status_code == 401

    def test_student_signup_short_password(self, client):
        resp = client.post('/api/portal/auth/signup', json={
            'matric_number': '125/22/1/0005',
            'name': 'Short PW',
            'password': '12345'
        })
        assert resp.status_code == 400

    def test_student_signup_missing_fields(self, client):
        resp = client.post('/api/portal/auth/signup', json={
            'matric_number': '125/22/1/0006'
        })
        assert resp.status_code == 400

    def test_student_login_nonexistent(self, client):
        resp = client.post('/api/portal/auth/login', json={
            'matric_number': '125/22/1/9999',
            'password': 'password123'
        })
        assert resp.status_code == 401


class TestPortalProfile:
    def _signup_and_login(self, client, matric='125/22/1/0010'):
        client.post('/api/portal/auth/signup', json={
            'matric_number': matric,
            'name': 'Profile Test',
            'email': 'profile@uni.edu',
            'password': 'password123'
        })

    def test_get_profile(self, client):
        self._signup_and_login(client)
        resp = client.get('/api/portal/profile')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['matric'] == '125/22/1/0010'
        assert data['name'] == 'Profile Test'

    def test_update_profile(self, client):
        self._signup_and_login(client)
        resp = client.put('/api/portal/profile', json={
            'name': 'Updated Name',
            'level': '400',
            'courses': ['MTE411', 'MTE412']
        })
        assert resp.status_code == 200

        profile = client.get('/api/portal/profile').get_json()
        assert profile['name'] == 'Updated Name'
        assert profile['level'] == '400'
        assert 'MTE411' in profile['courses']

    def test_change_password(self, client):
        self._signup_and_login(client)
        resp = client.put('/api/portal/password', json={
            'current_password': 'password123',
            'new_password': 'newpassword456'
        })
        assert resp.status_code == 200

        # Login with new password
        resp = client.post('/api/portal/auth/login', json={
            'matric_number': '125/22/1/0010',
            'password': 'newpassword456'
        })
        assert resp.status_code == 200

    def test_change_password_wrong_current(self, client):
        self._signup_and_login(client)
        resp = client.put('/api/portal/password', json={
            'current_password': 'wrongpassword',
            'new_password': 'newpassword456'
        })
        assert resp.status_code == 401

    def test_change_password_too_short(self, client):
        self._signup_and_login(client)
        resp = client.put('/api/portal/password', json={
            'current_password': 'password123',
            'new_password': '123'
        })
        assert resp.status_code == 400

    def test_profile_requires_login(self, client):
        resp = client.get('/api/portal/profile')
        # Should redirect to login
        assert resp.status_code == 302
