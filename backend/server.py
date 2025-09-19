from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import jwt
import httpx
import json
import random
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Farcaster Quiz Mini App", version="1.0.0")

# Security
security = HTTPBearer()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class FarcasterUser(BaseModel):
    fid: int
    username: str
    display_name: str
    bio: str = ""
    pfp_url: str = ""
    custody_address: Optional[str] = None
    verified_addresses: Optional[List[str]] = []

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    options: List[str]
    correct_answer: int
    category: str
    difficulty: str
    image_url: str = ""

class QuizSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_fid: int
    questions: List[Question]
    current_question: int = 0
    score: int = 0
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed: bool = False
    category: str = "crypto"

class AnswerSubmission(BaseModel):
    session_id: str
    question_id: str
    selected_answer: int

class LeaderboardEntry(BaseModel):
    fid: int
    username: str
    display_name: str
    score: int
    completion_time: int
    pfp_url: str
    category: str

# Sample quiz questions with images
CRYPTO_QUESTIONS = [
    {
        "question": "What was the first and most widely recognized cryptocurrency, created by a person or group known as Satoshi Nakamoto?",
        "options": ["Ethereum", "Litecoin", "Bitcoin", "Ripple"],
        "correct_answer": 2,
        "category": "Crypto",
        "difficulty": "Easy",
        "image_url": "https://images.unsplash.com/photo-1640161704729-cbe966a08476"
    },
    {
        "question": "What is the process called where new cryptocurrency coins are created and transactions are verified?",
        "options": ["Mining", "Staking", "Farming", "Trading"],
        "correct_answer": 0,
        "category": "Crypto",
        "difficulty": "Easy",
        "image_url": "https://images.unsplash.com/photo-1639322537228-f710d846310a"
    },
    {
        "question": "What technology underlies most cryptocurrencies?",
        "options": ["Cloud Computing", "Blockchain", "Artificial Intelligence", "Internet of Things"],
        "correct_answer": 1,
        "category": "Crypto",
        "difficulty": "Easy",
        "image_url": "https://images.unsplash.com/photo-1639762681485-074b7f938ba0"
    },
    {
        "question": "What is the maximum supply of Bitcoin?",
        "options": ["18 million", "21 million", "25 million", "Unlimited"],
        "correct_answer": 1,
        "category": "Crypto",
        "difficulty": "Medium",
        "image_url": "https://images.unsplash.com/photo-1623227413711-25ee4388dae3"
    },
    {
        "question": "What does DeFi stand for?",
        "options": ["Digital Finance", "Decentralized Finance", "Derivative Finance", "Direct Finance"],
        "correct_answer": 1,
        "category": "Crypto",
        "difficulty": "Medium",
        "image_url": "https://images.unsplash.com/photo-1639754390580-2e7437267698"
    }
]

GENERAL_QUESTIONS = [
    {
        "question": "What is the capital of France?",
        "options": ["London", "Berlin", "Paris", "Madrid"],
        "correct_answer": 2,
        "category": "Geography",
        "difficulty": "Easy",
        "image_url": "https://images.unsplash.com/photo-1502602898536-47ad22581b52"
    },
    {
        "question": "Who painted the Mona Lisa?",
        "options": ["Vincent van Gogh", "Leonardo da Vinci", "Pablo Picasso", "Michelangelo"],
        "correct_answer": 1,
        "category": "Art",
        "difficulty": "Easy",
        "image_url": "https://images.unsplash.com/photo-1541961017774-22349e4a1262"
    },
    {
        "question": "What is the largest planet in our solar system?",
        "options": ["Saturn", "Jupiter", "Neptune", "Earth"],
        "correct_answer": 1,
        "category": "Science",
        "difficulty": "Easy",
        "image_url": "https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4"
    },
    {
        "question": "In what year did World War II end?",
        "options": ["1944", "1945", "1946", "1947"],
        "correct_answer": 1,
        "category": "History",
        "difficulty": "Medium",
        "image_url": "https://images.unsplash.com/photo-1553729459-efe14ef6055d"
    }
]

# In-memory storage (use database in production)
quiz_sessions = {}
leaderboard_data = []

# Authentication functions
class FarcasterAuth:
    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "dev-secret-key-farcaster-quiz-2024")
        
    async def verify_farcaster_token(self, token: str) -> FarcasterUser:
        """Verify Farcaster JWT token and return user information"""
        try:
            # For development, create mock user from token
            # In production, this would verify with Farcaster's service
            if token.startswith("mock_"):
                fid = int(token.split("_")[1])
                return FarcasterUser(
                    fid=fid,
                    username=f"user{fid}",
                    display_name=f"Farcaster User {fid}",
                    bio="Quiz game enthusiast",
                    pfp_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed=user{fid}"
                )
            
            # Development JWT verification
            try:
                payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
                fid = int(payload.get("sub", 0))
                
                return FarcasterUser(
                    fid=fid,
                    username=payload.get("username", f"user{fid}"),
                    display_name=payload.get("display_name", f"User {fid}"),
                    bio=payload.get("bio", ""),
                    pfp_url=payload.get("pfp_url", f"https://api.dicebear.com/7.x/avataaars/svg?seed=user{fid}")
                )
            except jwt.InvalidTokenError:
                # Create demo user for development
                return FarcasterUser(
                    fid=12345,
                    username="demo_user",
                    display_name="Demo User",
                    bio="Demo user for testing",
                    pfp_url="https://api.dicebear.com/7.x/avataaars/svg?seed=demo"
                )
                
        except Exception as e:
            logging.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

farcaster_auth = FarcasterAuth()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> FarcasterUser:
    """Extract and verify user from JWT token"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return await farcaster_auth.verify_farcaster_token(credentials.credentials)

async def get_optional_user(request: Request) -> Optional[FarcasterUser]:
    """Extract user from token if present, return None if not authenticated"""
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            return await farcaster_auth.verify_farcaster_token(token)
        return None
    except:
        return None

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Farcaster Quiz Mini App API"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

@api_router.post("/auth/mock-login")
async def mock_login(fid: int = 12345):
    """Create mock authentication token for development"""
    payload = {
        "sub": str(fid),
        "username": f"user{fid}",
        "display_name": f"Test User {fid}",
        "bio": "Quiz enthusiast",
        "pfp_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed=user{fid}",
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": (datetime.now(timezone.utc).timestamp() + 86400)  # 24 hours
    }
    
    token = jwt.encode(payload, farcaster_auth.jwt_secret, algorithm="HS256")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 86400
    }

@api_router.get("/user/profile")
async def get_user_profile(current_user: FarcasterUser = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@api_router.post("/quiz/start")
async def start_quiz(
    category: str = "crypto",
    current_user: FarcasterUser = Depends(get_current_user)
) -> QuizSession:
    """Start a new quiz session"""
    # Select questions based on category
    if category.lower() == "crypto":
        available_questions = CRYPTO_QUESTIONS
    else:
        available_questions = GENERAL_QUESTIONS
    
    # Select random questions
    selected_questions = random.sample(available_questions, min(5, len(available_questions)))
    
    # Create Question objects
    questions = []
    for q_data in selected_questions:
        question = Question(
            question=q_data["question"],
            options=q_data["options"],
            correct_answer=q_data["correct_answer"],
            category=q_data["category"],
            difficulty=q_data["difficulty"],
            image_url=q_data["image_url"]
        )
        questions.append(question)
    
    # Create quiz session
    quiz_session = QuizSession(
        user_fid=current_user.fid,
        questions=questions,
        category=category
    )
    
    # Store session
    quiz_sessions[quiz_session.session_id] = quiz_session
    
    return quiz_session

@api_router.post("/quiz/answer")
async def submit_answer(
    answer: AnswerSubmission,
    current_user: FarcasterUser = Depends(get_current_user)
):
    """Submit an answer for a quiz question"""
    session = quiz_sessions.get(answer.session_id)  
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz session not found"
        )
    
    if session.user_fid != current_user.fid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this quiz session"
        )
    
    if session.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz session already completed"
        )
    
    # Find the current question
    current_q_index = session.current_question
    if current_q_index >= len(session.questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No more questions in this quiz"
        )
    
    current_question = session.questions[current_q_index]
    
    # Check if answer is correct
    is_correct = answer.selected_answer == current_question.correct_answer
    if is_correct:
        session.score += 1
    
    # Move to next question
    session.current_question += 1
    
    # Check if quiz is completed
    if session.current_question >= len(session.questions):
        session.completed = True
        completion_time = int((datetime.now(timezone.utc) - session.start_time).total_seconds())
        
        # Add to leaderboard
        leaderboard_entry = LeaderboardEntry(
            fid=current_user.fid,
            username=current_user.username,
            display_name=current_user.display_name,
            score=session.score,
            completion_time=completion_time,
            pfp_url=current_user.pfp_url,
            category=session.category
        )
        leaderboard_data.append(leaderboard_entry)
        
        # Sort leaderboard by score (desc) then by time (asc)
        leaderboard_data.sort(key=lambda x: (-x.score, x.completion_time))
    
    next_question = None
    if session.current_question < len(session.questions):
        next_question = session.questions[session.current_question]
    
    return {
        "correct": is_correct,
        "correct_answer": current_question.correct_answer,
        "explanation": f"The correct answer was: {current_question.options[current_question.correct_answer]}",
        "current_score": session.score,
        "total_questions": len(session.questions),
        "quiz_completed": session.completed,
        "next_question": next_question,
        "session_id": session.session_id
    }

@api_router.get("/quiz/leaderboard")
async def get_leaderboard(
    category: Optional[str] = None,
    limit: int = 10,
    current_user: Optional[FarcasterUser] = Depends(get_optional_user)
) -> List[LeaderboardEntry]:
    """Get the quiz leaderboard"""
    filtered_data = leaderboard_data
    
    if category:
        filtered_data = [entry for entry in leaderboard_data if entry.category.lower() == category.lower()]
    
    return filtered_data[:limit]

@api_router.get("/quiz/session/{session_id}")
async def get_quiz_session(
    session_id: str,
    current_user: FarcasterUser = Depends(get_current_user)
) -> QuizSession:
    """Get details of a quiz session"""
    session = quiz_sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz session not found"
        )
    
    if session.user_fid != current_user.fid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this quiz session"
        )
    
    return session

# Include the router in the main app
app.include_router(api_router)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()