#!/usr/bin/env python3
"""
Complete Quiz Flow Test - Testing the full quiz experience with /frames endpoints
"""
import requests
import json
import time
from datetime import datetime

class CompleteQuizFlowTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/frames"
        self.token = None
        self.user_fid = None
        self.session_id = None

    def authenticate(self, fid=None):
        """Authenticate and get token"""
        if not fid:
            fid = 99999  # Use a unique FID for testing
        
        print(f"🔐 Authenticating with FID: {fid}")
        response = requests.post(f"{self.api_url}/auth/mock-login", params={"fid": fid})
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            self.user_fid = fid
            print(f"✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return False

    def get_headers(self):
        """Get headers with authentication"""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }

    def get_user_profile(self):
        """Get user profile"""
        print("\n👤 Getting user profile...")
        response = requests.get(f"{self.api_url}/user/profile", headers=self.get_headers())
        
        if response.status_code == 200:
            profile = response.json()
            print(f"✅ User: {profile['display_name']} (@{profile['username']})")
            print(f"   FID: {profile['fid']}")
            print(f"   Bio: {profile['bio']}")
            return profile
        else:
            print(f"❌ Failed to get profile: {response.status_code}")
            return None

    def get_daily_quest_status(self):
        """Get daily quest status"""
        print("\n🎯 Getting daily quest status...")
        response = requests.get(f"{self.api_url}/user/daily-quest", headers=self.get_headers())
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Quest Status:")
            print(f"   Attempts remaining: {status['attempts_remaining']}")
            print(f"   Max attempts: {status['max_attempts']}")
            print(f"   Total score today: {status['total_score_today']}")
            print(f"   Can play: {status['can_play']}")
            print(f"   Reset time: {status['reset_time']}")
            return status
        else:
            print(f"❌ Failed to get quest status: {response.status_code}")
            return None

    def get_weekly_leaderboard_status(self):
        """Get weekly leaderboard status"""
        print("\n📅 Getting weekly leaderboard status...")
        response = requests.get(f"{self.api_url}/leaderboard/weekly-status")
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Weekly Leaderboard Status:")
            print(f"   Next reset: {status['next_reset']}")
            print(f"   Days until reset: {status['days_until_reset']}")
            print(f"   Last reset: {status['last_reset']}")
            return status
        else:
            print(f"❌ Failed to get weekly status: {response.status_code}")
            return None

    def start_quiz(self, category="crypto"):
        """Start a quiz"""
        print(f"\n🚀 Starting {category} quiz...")
        response = requests.post(
            f"{self.api_url}/quiz/start", 
            headers=self.get_headers(),
            params={"category": category}
        )
        
        if response.status_code == 200:
            quiz = response.json()
            self.session_id = quiz['session_id']
            print(f"✅ Quiz started!")
            print(f"   Session ID: {self.session_id}")
            print(f"   Category: {quiz['category']}")
            print(f"   Questions: {len(quiz['questions'])}")
            print(f"   Current question: {quiz['current_question']}")
            
            # Show first question
            if quiz['questions']:
                q = quiz['questions'][0]
                print(f"\n📝 First Question:")
                print(f"   {q['question']}")
                for i, option in enumerate(q['options']):
                    print(f"   {chr(65+i)}. {option}")
                print(f"   Correct answer: {chr(65+q['correct_answer'])}")
            
            return quiz
        else:
            print(f"❌ Failed to start quiz: {response.status_code}")
            if response.status_code == 429:
                print("   Daily limit reached!")
            return None

    def submit_answer(self, question_id, selected_answer):
        """Submit an answer"""
        print(f"\n✍️ Submitting answer {selected_answer} for question...")
        response = requests.post(
            f"{self.api_url}/quiz/answer",
            headers=self.get_headers(),
            json={
                "session_id": self.session_id,
                "question_id": question_id,
                "selected_answer": selected_answer
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Answer submitted!")
            print(f"   Correct: {result['correct']}")
            print(f"   Explanation: {result['explanation']}")
            print(f"   Current score: {result['current_score']}")
            print(f"   Daily total score: {result['daily_total_score']}")
            print(f"   Quiz completed: {result['quiz_completed']}")
            
            if result['next_question']:
                print(f"   Next question available")
            
            return result
        else:
            print(f"❌ Failed to submit answer: {response.status_code}")
            return None

    def get_leaderboard(self, category=None, limit=5):
        """Get leaderboard"""
        print(f"\n🏆 Getting leaderboard...")
        params = {"limit": limit}
        if category:
            params["category"] = category
            
        response = requests.get(f"{self.api_url}/quiz/leaderboard", params=params)
        
        if response.status_code == 200:
            leaderboard = response.json()
            print(f"✅ Leaderboard ({len(leaderboard)} entries):")
            for i, entry in enumerate(leaderboard):
                print(f"   #{i+1}. {entry['display_name']} (@{entry['username']}) - {entry['score']} pts")
            return leaderboard
        else:
            print(f"❌ Failed to get leaderboard: {response.status_code}")
            return None

    def play_complete_quiz(self, category="crypto"):
        """Play a complete quiz session"""
        print(f"\n🎮 Playing complete {category} quiz...")
        
        # Start quiz
        quiz = self.start_quiz(category)
        if not quiz:
            return False
        
        # Answer all questions
        for i, question in enumerate(quiz['questions']):
            print(f"\n--- Question {i+1}/{len(quiz['questions'])} ---")
            print(f"Q: {question['question']}")
            for j, option in enumerate(question['options']):
                print(f"   {chr(65+j)}. {option}")
            
            # For testing, always select the correct answer
            correct_answer = question['correct_answer']
            print(f"Selecting correct answer: {chr(65+correct_answer)}")
            
            result = self.submit_answer(question['id'], correct_answer)
            if not result:
                return False
            
            # Small delay between questions
            time.sleep(1)
        
        print(f"\n🎉 Quiz completed!")
        return True

def main():
    print("🚀 Starting Complete Quiz Flow Test with /frames endpoints")
    print("=" * 70)
    
    tester = CompleteQuizFlowTester()
    
    # Test 1: Authentication
    if not tester.authenticate():
        print("❌ Authentication failed, stopping tests")
        return 1
    
    # Test 2: User Profile
    profile = tester.get_user_profile()
    if not profile:
        print("❌ Profile test failed")
        return 1
    
    # Test 3: Daily Quest Status
    quest_status = tester.get_daily_quest_status()
    if not quest_status:
        print("❌ Quest status test failed")
        return 1
    
    # Test 4: Weekly Leaderboard Status
    weekly_status = tester.get_weekly_leaderboard_status()
    if not weekly_status:
        print("❌ Weekly status test failed")
        return 1
    
    # Test 5: Complete Quiz Flow (if attempts available)
    if quest_status['can_play']:
        print(f"\n🎯 User has {quest_status['attempts_remaining']} attempts remaining")
        
        # Play one complete crypto quiz
        if tester.play_complete_quiz("crypto"):
            print("✅ Crypto quiz completed successfully")
        else:
            print("❌ Crypto quiz failed")
            return 1
        
        # Check updated quest status
        updated_status = tester.get_daily_quest_status()
        if updated_status:
            print(f"📊 Updated quest status: {updated_status['attempts_remaining']} attempts remaining")
    else:
        print("⏰ No attempts remaining today, skipping quiz play")
    
    # Test 6: Leaderboard
    leaderboard = tester.get_leaderboard()
    if not leaderboard:
        print("❌ Leaderboard test failed")
        return 1
    
    print("\n" + "=" * 70)
    print("🎉 All Complete Quiz Flow Tests Passed!")
    print("✅ Authentication working")
    print("✅ User profile working") 
    print("✅ Daily quest system working")
    print("✅ Weekly leaderboard system working")
    print("✅ Quiz flow working")
    print("✅ Leaderboard working")
    print("\n🔧 Issue: Kubernetes ingress needs to route /frames/* to backend")
    return 0

if __name__ == "__main__":
    exit(main())