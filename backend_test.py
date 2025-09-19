import requests
import sys
import json
from datetime import datetime

class FarcasterQuizAPITester:
    def __init__(self, base_url="https://quizchain.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = None
        self.user_fid = None
        self.quest_status = None

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

    def test_daily_quest_status(self):
        """Test getting daily quest status"""
        if not self.token:
            print("❌ No token available for daily quest status test")
            return False
            
        success, response = self.run_test(
            "Daily Quest Status",
            "GET",
            "/user/daily-quest",
            200
        )
        if success:
            self.quest_status = response
            print(f"   Attempts remaining: {response.get('attempts_remaining')}")
            print(f"   Max attempts: {response.get('max_attempts')}")
            print(f"   Total score today: {response.get('total_score_today')}")
            print(f"   Can play: {response.get('can_play')}")
            print(f"   Reset time: {response.get('reset_time')}")
        return success

    def test_daily_limit_enforcement(self):
        """Test that daily limit is enforced after 3 attempts"""
        if not self.token:
            print("❌ No token available for daily limit test")
            return False
        
        print(f"\n🔍 Testing Daily Limit Enforcement...")
        attempts_made = 0
        max_attempts = 3
        
        # Make multiple quiz attempts to test daily limit
        for attempt in range(max_attempts + 1):  # Try one more than allowed
            print(f"\n   Attempt {attempt + 1}:")
            
            # Check quest status before attempt
            success, quest_response = self.run_test(
                f"Quest Status Before Attempt {attempt + 1}",
                "GET",
                "/user/daily-quest",
                200
            )
            
            if success:
                can_play = quest_response.get('can_play', False)
                attempts_remaining = quest_response.get('attempts_remaining', 0)
                print(f"     Can play: {can_play}, Attempts remaining: {attempts_remaining}")
                
                if can_play and attempts_remaining > 0:
                    # Try to start a quiz
                    success, quiz_response = self.run_test(
                        f"Start Quiz Attempt {attempt + 1}",
                        "POST",
                        "/quiz/start",
                        200,
                        params={"category": "crypto"}
                    )
                    
                    if success:
                        attempts_made += 1
                        session_id = quiz_response.get('session_id')
                        questions = quiz_response.get('questions', [])
                        
                        # Answer the first question to complete the attempt
                        if questions:
                            answer_success, answer_response = self.run_test(
                                f"Submit Answer Attempt {attempt + 1}",
                                "POST",
                                "/quiz/answer",
                                200,
                                data={
                                    "session_id": session_id,
                                    "question_id": questions[0]['id'],
                                    "selected_answer": 0
                                }
                            )
                            
                            if answer_success:
                                print(f"     Answer submitted, daily score: {answer_response.get('daily_total_score')}")
                else:
                    # Should get 429 error when trying to start quiz after limit
                    success, error_response = self.run_test(
                        f"Expected 429 on Attempt {attempt + 1}",
                        "POST",
                        "/quiz/start",
                        429,
                        params={"category": "crypto"}
                    )
                    
                    if success:
                        print(f"     ✅ Correctly blocked with 429 error")
                        self.tests_passed += 1
                        return True
                    else:
                        print(f"     ❌ Expected 429 error but got different response")
                        return False
        
        print(f"   Total attempts made: {attempts_made}")
        return attempts_made == max_attempts

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