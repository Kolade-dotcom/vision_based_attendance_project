import json

def test_api_health(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'



def test_api_enroll_student(client):
    response = client.post('/api/enroll', json={
        'student_id': '125/22/1/0178',
        'name': 'Test API Student',
        'email': 'api@test.com',
        'level': '400',
        'courses': ['MTE411', 'MTE412']
    })
    
    assert response.status_code == 201
    assert b"125/22/1/0178" in response.data

def test_api_get_students(client):
    client.post('/api/enroll', json={
        'student_id': '125/22/1/0178',
        'name': 'Test API',
        'level': '400',
        'courses': ['MTE411']
    })

    
    response = client.get('/api/students')
    assert response.status_code == 200
    

def test_api_get_statistics_filtered(client, db):
    # Setup: Enroll and record attendance manually in DB for precision
    db.add_student("S1", "Student 1", level="400", courses=["MTE411"])
    db.add_student("S2", "Student 2", level="100", courses=["MTE111"])
    
    # S1 present for MTE411 (400 Level)
    db.record_attendance("S1", status="present", course_code="MTE411", level="400")
    
    # S2 present for MTE111 (100 Level)
    db.record_attendance("S2", status="present", course_code="MTE111", level="100")
    
    # 1. Test Filter by Level 400
    resp_400 = client.get('/api/statistics?level=400')
    data_400 = resp_400.get_json()
    assert data_400['present_today'] == 1
    assert data_400['total_students'] == 1 # Only 1 student in level 400
    
    # 2. Test Filter by Course MTE111
    resp_mte111 = client.get('/api/statistics?course=MTE111')
    data_mte111 = resp_mte111.get_json()
    assert data_mte111['present_today'] == 1

