import requests
import json

def test_chat():
    url = "http://localhost:5000/api/chat"
    # We need to be logged in, but for a quick unit test of the function we might need to mock session or login first.
    # Since app.py uses @login_required, we need a valid session.
    # Alternatively, we can temporarily comment out @login_required for testing or use a test client.
    
    # Let's use Flask's test client
    from app import app
    
    with app.test_client() as client:
        # Mock login
        with client.session_transaction() as sess:
            sess['user_id'] = 'test_user'
            sess['user_name'] = 'Test User'
            
        # Send message requesting a routine to test formatting
        response = client.post('/api/chat', json={'message': 'Give me a daily routine for Vata dosha'})
        
        print("Status Code:", response.status_code)
        print("Response:", response.get_json())

if __name__ == "__main__":
    test_chat()
