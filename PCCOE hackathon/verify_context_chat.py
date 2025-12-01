import requests
import json
from app import app
from unittest.mock import MagicMock, patch

def test_context_aware_chat():
    with app.test_client() as client:
        # Mock the InferenceClient to avoid actual API calls and check prompt injection
        with patch('app.client') as mock_client:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Mock response"
            mock_client.chat_completion.return_value = mock_response

            # 1. Test Guest Context Injection
            print("\n--- Testing Guest Context ---")
            guest_data = {
                'message': 'What should I eat?',
                'context': {
                    'prakruti': 'Pitta',
                    'scores': {'Vata': 10, 'Pitta': 80, 'Kapha': 10}
                }
            }
            client.post('/api/chat', json=guest_data)
            
            # Check if system prompt contains the context
            call_args = mock_client.chat_completion.call_args
            messages = call_args.kwargs['messages']
            system_msg = messages[0]['content']
            print(f"System Prompt: {system_msg}")
            
            if "User Profile (Guest): Dosha=Pitta" in system_msg:
                print("SUCCESS: Guest context injected correctly.")
            else:
                print("FAILURE: Guest context NOT found.")

            # 2. Test Logged-In User Context Injection
            # First, create a user
            print("\n--- Testing Logged-In User Context ---")
            with client.session_transaction() as sess:
                sess['user_id'] = 'test_user_id'
            
            # Mock DB connection to return a user
            with patch('app.get_db_connection') as mock_get_db:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                
                # CRITICAL: Link the patch to the mock connection
                mock_get_db.return_value = mock_conn
                mock_conn.execute.return_value = mock_cursor
                
                # Mock user data - just return a dict!
                mock_user = {
                    'prakruti': 'Vata',
                    'age': 30,
                    'gender': 'Male',
                    'weight': 70.0
                }
                mock_cursor.fetchone.return_value = mock_user
                
                client.post('/api/chat', json={'message': 'Diet tips?'})
                
                # Check prompt again
                call_args = mock_client.chat_completion.call_args
                messages = call_args.kwargs['messages']
                system_msg = messages[0]['content']
                print(f"System Prompt: {system_msg}")
                
                if "User Profile: Dosha=Vata, Age=30" in system_msg:
                    print("SUCCESS: User context injected correctly.")
                else:
                    print("FAILURE: User context NOT found.")

if __name__ == "__main__":
    test_context_aware_chat()
