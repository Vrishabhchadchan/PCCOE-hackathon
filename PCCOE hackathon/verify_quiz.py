import requests
import json
from app import app, get_db_connection

def test_quiz_submission():
    with app.test_client() as client:
        # Mock login
        with client.session_transaction() as sess:
            sess['user_id'] = 'test_user_quiz'
            sess['user_name'] = 'Test User'
            
        # Create test user in DB if not exists
        conn = get_db_connection()
        conn.execute('INSERT OR IGNORE INTO users (id, name, email) VALUES (?, ?, ?)', 
                     ('test_user_quiz', 'Test User', 'test@example.com'))
        conn.commit()
        conn.close()
            
        # Submit quiz with new fields
        data = {
            'age': 30,
            'gender': 'Male',
            'weight': 75.5,
            'city': 'Pune',
            'answers': {'q1': 'V', 'q2': 'P'} # Partial answers
        }
        
        response = client.post('/api/submit-quiz', json=data)
        print("Status Code:", response.status_code)
        print("Response:", response.get_json())
        
        # Verify DB update
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', ('test_user_quiz',)).fetchone()
        conn.close()
        
        print(f"DB Verification - Age: {user['age']}, Gender: {user['gender']}, Weight: {user['weight']}")

if __name__ == "__main__":
    test_quiz_submission()
