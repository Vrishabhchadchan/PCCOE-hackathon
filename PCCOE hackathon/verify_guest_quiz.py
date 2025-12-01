import requests
import json
from app import app

def test_guest_quiz_submission():
    with app.test_client() as client:
        # Ensure NO session (Guest)
        with client.session_transaction() as sess:
            sess.clear()
            
        # Submit quiz as guest
        data = {
            'age': 25,
            'gender': 'Female',
            'weight': 60.0,
            'city': 'Mumbai',
            'answers': {'q1': 'K', 'q2': 'K'} # Kapha answers
        }
        
        response = client.post('/api/submit-quiz', json=data)
        print("Status Code:", response.status_code)
        print("Response:", response.get_json())
        
        if response.status_code == 200:
            print("Guest submission successful!")
        else:
            print("Guest submission failed!")

if __name__ == "__main__":
    test_guest_quiz_submission()
