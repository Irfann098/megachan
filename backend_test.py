import requests
import sys
import json
from datetime import datetime

class FarcasterQuizAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = None
        self.user_fid = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")

            return success, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test basic health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "/health",
            200
        )
        return success

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, response = self.run_test(
            "Root Endpoint",
            "GET",
            "/",
            200
        )
        return success

    def test_mock_login(self):
        """Test mock authentication and get token"""
        test_fid = 12345
        success, response = self.run_test(
            "Mock Login",
            "POST",
            "/auth/mock-login",
            200,
            params={"fid": test_fid}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_fid = test_fid
            print(f"   Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_user_profile(self):
        """Test getting user profile"""
        if not self.token:
            print("❌ No token available for user profile test")
            return False
            
        success, response = self.run_test(
            "User Profile",
            "GET",
            "/user/profile",
            200
        )
        if success:
            print(f"   User: {response.get('display_name')} (@{response.get('username')})")
        return success

    def test_start_crypto_quiz(self):
        """Test starting a crypto quiz"""
        if not self.token:
            print("❌ No token available for quiz start test")
            return False
            
        success, response = self.run_test(
            "Start Crypto Quiz",
            "POST",
            "/quiz/start",
            200,
            params={"category": "crypto"}
        )
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            print(f"   Quiz session started: {self.session_id}")
            print(f"   Questions count: {len(response.get('questions', []))}")
            print(f"   Category: {response.get('category')}")
            return True
        return False

    def test_start_general_quiz(self):
        """Test starting a general knowledge quiz"""
        if not self.token:
            print("❌ No token available for general quiz test")
            return False
            
        success, response = self.run_test(
            "Start General Quiz",
            "POST",
            "/quiz/start",
            200,
            params={"category": "general"}
        )
        if success and 'session_id' in response:
            print(f"   General quiz session: {response['session_id']}")
            print(f"   Questions count: {len(response.get('questions', []))}")
            return True
        return False

    def test_submit_answer(self):
        """Test submitting an answer"""
        if not self.token or not self.session_id:
            print("❌ No token or session available for answer submission test")
            return False

        # Get the quiz session first to get question details
        success, session_response = self.run_test(
            "Get Quiz Session",
            "GET",
            f"/quiz/session/{self.session_id}",
            200
        )
        
        if not success:
            return False

        current_question = session_response['questions'][0]  # First question
        
        success, response = self.run_test(
            "Submit Answer",
            "POST",
            "/quiz/answer",
            200,
            data={
                "session_id": self.session_id,
                "question_id": current_question['id'],
                "selected_answer": 0  # Select first option
            }
        )
        if success:
            print(f"   Answer correct: {response.get('correct')}")
            print(f"   Current score: {response.get('current_score')}")
            print(f"   Quiz completed: {response.get('quiz_completed')}")
        return success

    def test_get_quiz_session(self):
        """Test getting quiz session details"""
        if not self.token or not self.session_id:
            print("❌ No token or session available for session retrieval test")
            return False
            
        success, response = self.run_test(
            "Get Quiz Session",
            "GET",
            f"/quiz/session/{self.session_id}",
            200
        )
        if success:
            print(f"   Session user FID: {response.get('user_fid')}")
            print(f"   Current question: {response.get('current_question')}")
            print(f"   Score: {response.get('score')}")
        return success

    def test_leaderboard(self):
        """Test getting leaderboard"""
        success, response = self.run_test(
            "Get Leaderboard",
            "GET",
            "/quiz/leaderboard",
            200
        )
        if success:
            print(f"   Leaderboard entries: {len(response)}")
            if response:
                top_entry = response[0]
                print(f"   Top player: {top_entry.get('display_name')} with {top_entry.get('score')} points")
        return success

    def test_leaderboard_with_category(self):
        """Test getting leaderboard filtered by category"""
        success, response = self.run_test(
            "Get Crypto Leaderboard",
            "GET",
            "/quiz/leaderboard",
            200,
            params={"category": "crypto", "limit": 5}
        )
        if success:
            print(f"   Crypto leaderboard entries: {len(response)}")
        return success

    def test_invalid_session(self):
        """Test accessing invalid session"""
        if not self.token:
            print("❌ No token available for invalid session test")
            return False
            
        success, response = self.run_test(
            "Invalid Session Access",
            "GET",
            "/quiz/session/invalid-session-id",
            404
        )
        return success

    def test_unauthorized_access(self):
        """Test accessing protected endpoint without token"""
        # Temporarily remove token
        temp_token = self.token
        self.token = None
        
        success, response = self.run_test(
            "Unauthorized Access",
            "GET",
            "/user/profile",
            401
        )
        
        # Restore token
        self.token = temp_token
        return success

def main():
    print("🚀 Starting Farcaster Quiz API Tests")
    print("=" * 50)
    
    # Initialize tester
    tester = FarcasterQuizAPITester()
    
    # Run basic connectivity tests
    if not tester.test_health_check():
        print("❌ Health check failed, stopping tests")
        return 1
    
    if not tester.test_root_endpoint():
        print("❌ Root endpoint failed, stopping tests")
        return 1

    # Test authentication
    if not tester.test_mock_login():
        print("❌ Authentication failed, stopping tests")
        return 1

    # Test user profile
    tester.test_user_profile()

    # Test quiz functionality
    if not tester.test_start_crypto_quiz():
        print("❌ Crypto quiz start failed")
        return 1

    # Test quiz session retrieval
    tester.test_get_quiz_session()

    # Test answer submission
    tester.test_submit_answer()

    # Test general knowledge quiz
    tester.test_start_general_quiz()

    # Test leaderboard
    tester.test_leaderboard()
    tester.test_leaderboard_with_category()

    # Test error cases
    tester.test_invalid_session()
    tester.test_unauthorized_access()

    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"❌ {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())