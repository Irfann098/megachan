import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { Card } from './components/ui/card';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Timer, Trophy, User, Zap, Brain, Globe } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FarcasterQuizApp = () => {
  const [user, setUser] = useState(null);
  const [authToken, setAuthToken] = useState(null);
  const [currentQuiz, setCurrentQuiz] = useState(null);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [gameState, setGameState] = useState('home'); // home, quiz, completed, leaderboard
  const [selectedCategory, setSelectedCategory] = useState('crypto');
  const [showAnswer, setShowAnswer] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [timeLeft, setTimeLeft] = useState(10);
  const [timerActive, setTimerActive] = useState(false);

  useEffect(() => {
    initializeApp();
  }, []);

  // Timer effect
  useEffect(() => {
    let interval = null;
    if (timerActive && timeLeft > 0) {
      interval = setInterval(() => {
        setTimeLeft(time => {
          if (time <= 1) {
            handleTimeUp();
            return 0;
          }
          return time - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [timerActive, timeLeft]);

  const initializeApp = async () => {
    try {
      setLoading(true);
      await authenticateUser();
      await loadLeaderboard();
    } catch (error) {
      console.error('Failed to initialize app:', error);
    } finally {
      setLoading(false);
    }
  };

  const authenticateUser = async () => {
    try {
      // For development, use mock authentication
      // In production, this would use Farcaster SDK
      const mockFid = Math.floor(Math.random() * 10000) + 1000;
      const authResponse = await axios.post(`${API}/auth/mock-login`, null, {
        params: { fid: mockFid }
      });
      
      const token = authResponse.data.access_token;
      setAuthToken(token);
      
      // Get user profile
      const profileResponse = await apiCall('/user/profile', {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setUser(profileResponse.data);
    } catch (error) {
      console.error('Authentication failed:', error);
      throw new Error('Failed to authenticate');
    }
  };

  const apiCall = async (endpoint, options = {}) => {
    const config = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
        ...options.headers
      },
      ...options
    };
    
    return await axios.get(`${API}${endpoint}`, config);
  };

  const apiPost = async (endpoint, data = {}, options = {}) => {
    const config = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
        ...options.headers
      },
      ...options
    };
    
    return await axios.post(`${API}${endpoint}`, data, config);
  };

  const startQuiz = async (category = 'crypto') => {
    try {
      setSelectedCategory(category);
      const response = await apiPost('/quiz/start', null, {
        params: { category }
      });
      
      setCurrentQuiz(response.data);
      setGameState('quiz');
      setSelectedAnswer(null);
      setShowAnswer(false);
      setTimeLeft(10);
      setTimerActive(true);
    } catch (error) {
      console.error('Failed to start quiz:', error);
    }
  };

  const submitAnswer = async () => {
    if (selectedAnswer === null || !currentQuiz) return;
    
    try {
      setTimerActive(false);
      const currentQuestion = currentQuiz.questions[currentQuiz.current_question];
      
      const response = await apiPost('/quiz/answer', {
        session_id: currentQuiz.session_id,
        question_id: currentQuestion.id,
        selected_answer: selectedAnswer
      });
      
      setLastResult(response.data);
      setShowAnswer(true);
      
      // Update quiz state
      setCurrentQuiz(prev => ({
        ...prev,
        score: response.data.current_score,
        current_question: prev.current_question + 1
      }));
      
      // Show result for 3 seconds
      setTimeout(() => {
        if (response.data.quiz_completed) {
          setGameState('completed');
          loadLeaderboard();
        } else {
          setSelectedAnswer(null);
          setShowAnswer(false);
          setTimeLeft(10);
          setTimerActive(true);
        }
      }, 3000);
      
    } catch (error) {
      console.error('Failed to submit answer:', error);
    }
  };

  const handleTimeUp = () => {
    if (selectedAnswer === null) {
      // Auto-select first option if no answer chosen
      setSelectedAnswer(0);
    }
    submitAnswer();
  };

  const selectAnswer = (index) => {
    if (showAnswer) return;
    setSelectedAnswer(index);
  };

  const loadLeaderboard = async () => {
    try {
      const response = await axios.get(`${API}/quiz/leaderboard`);
      setLeaderboard(response.data);
    } catch (error) {
      console.error('Failed to load leaderboard:', error);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading Farcaster Quiz...</p>
      </div>
    );
  }

  if (gameState === 'quiz' && currentQuiz) {
    const currentQuestion = currentQuiz.questions[currentQuiz.current_question];
    const progress = ((currentQuiz.current_question) / currentQuiz.questions.length) * 100;
    
    return (
      <div className="quiz-container">
        <div className="quiz-header">
          <div className="quiz-progress">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }}></div>
            </div>
            <span className="progress-text">
              Question {currentQuiz.current_question + 1} of {currentQuiz.questions.length}
            </span>
          </div>
          
          <div className="quiz-stats">
            <div className="stat">
              <Trophy className="stat-icon" />
              <span>{currentQuiz.score}</span>
            </div>
            <div className="stat timer">
              <Timer className="stat-icon" />
              <span className={timeLeft <= 3 ? 'timer-urgent' : ''}>{timeLeft}s</span>
            </div>
          </div>
        </div>

        <Card className="question-card">
          {currentQuestion.image_url && (
            <div className="question-image">
              <img src={currentQuestion.image_url} alt="Question illustration" />
            </div>
          )}
          
          <div className="question-content">
            <h2 className="question-title">{currentQuestion.question}</h2>
            
            <div className="answer-options">
              {currentQuestion.options.map((option, index) => {
                let buttonClass = 'answer-option';
                
                if (showAnswer) {
                  if (index === currentQuestion.correct_answer) {
                    buttonClass += ' correct';
                  } else if (index === selectedAnswer && index !== currentQuestion.correct_answer) {
                    buttonClass += ' incorrect';
                  }
                } else if (index === selectedAnswer) {
                  buttonClass += ' selected';
                }
                
                return (
                  <Button
                    key={index}
                    className={buttonClass}
                    onClick={() => selectAnswer(index)}
                    disabled={showAnswer}
                  >
                    <span className="option-letter">{String.fromCharCode(65 + index)}</span>
                    <span className="option-text">{option}</span>
                  </Button>
                );
              })}
            </div>
            
            {showAnswer && lastResult && (
              <div className={`result-feedback ${lastResult.correct ? 'correct' : 'incorrect'}`}>
                <p className="result-text">
                  {lastResult.correct ? '🎉 Correct!' : '❌ Incorrect'}
                </p>
                <p className="result-explanation">{lastResult.explanation}</p>
              </div>
            )}
            
            {!showAnswer && selectedAnswer !== null && (
              <Button className="submit-button" onClick={submitAnswer}>
                Submit Answer
              </Button>
            )}
          </div>
        </Card>
      </div>
    );
  }

  if (gameState === 'completed') {
    const percentage = Math.round((currentQuiz.score / currentQuiz.questions.length) * 100);
    
    return (
      <div className="completion-container">
        <Card className="completion-card">
          <div className="completion-header">
            <Trophy className="completion-icon" />
            <h1>Quiz Complete!</h1>
          </div>
          
          <div className="completion-stats">
            <div className="stat-large">
              <span className="stat-number">{currentQuiz.score}</span>
              <span className="stat-label">Correct Answers</span>
            </div>
            <div className="stat-large">
              <span className="stat-number">{percentage}%</span>
              <span className="stat-label">Accuracy</span>
            </div>
          </div>
          
          <div className="completion-actions">
            <Button onClick={() => startQuiz(selectedCategory)} className="primary">
              Play Again
            </Button>
            <Button onClick={() => setGameState('leaderboard')} className="secondary">
              View Leaderboard
            </Button>
            <Button onClick={() => setGameState('home')} className="tertiary">
              Home
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (gameState === 'leaderboard') {
    return (
      <div className="leaderboard-container">
        <Card className="leaderboard-card">
          <div className="leaderboard-header">
            <Trophy className="leaderboard-icon" />
            <h1>Leaderboard</h1>
          </div>
          
          <div className="leaderboard-list">
            {leaderboard.map((entry, index) => (
              <div key={entry.fid} className={`leaderboard-entry ${entry.fid === user?.fid ? 'current-user' : ''}`}>
                <div className="rank-badge">#{index + 1}</div>
                <img src={entry.pfp_url} alt={entry.display_name} className="player-avatar" />
                <div className="player-info">
                  <span className="player-name">{entry.display_name}</span>
                  <span className="player-username">@{entry.username}</span>
                </div>
                <Badge className="category-badge">{entry.category}</Badge>
                <div className="player-score">{entry.score} pts</div>
              </div>
            ))}
          </div>
          
          <Button onClick={() => setGameState('home')} className="back-button">
            Back to Home
          </Button>
        </Card>
      </div>
    );
  }

  // Home screen
  return (
    <div className="home-container">
      <div className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="gradient-text">Crypto Knowledge</span>
            <br />Quiz Challenge
          </h1>
          <p className="hero-subtitle">
            Test your blockchain and general knowledge in this futuristic quiz game
          </p>
        </div>
      </div>

      {user && (
        <Card className="user-card">
          <div className="user-profile">
            <img src={user.pfp_url} alt={user.display_name} className="user-avatar" />
            <div className="user-info">
              <h3 className="user-name">{user.display_name}</h3>
              <p className="user-username">@{user.username}</p>
            </div>
          </div>
        </Card>
      )}

      <div className="game-modes">
        <Card className="mode-card crypto-mode" onClick={() => startQuiz('crypto')}>
          <div className="mode-icon">
            <Zap />
          </div>
          <h3 className="mode-title">Crypto & Blockchain</h3>
          <p className="mode-description">
            Test your knowledge of cryptocurrencies, DeFi, and blockchain technology
          </p>
          <Badge className="mode-badge">5 Questions</Badge>
        </Card>

        <Card className="mode-card general-mode" onClick={() => startQuiz('general')}>
          <div className="mode-icon">
            <Brain />
          </div>
          <h3 className="mode-title">General Knowledge</h3>
          <p className="mode-description">
            Challenge yourself with questions from various topics and subjects
          </p>
          <Badge className="mode-badge">4 Questions</Badge>
        </Card>
      </div>

      <Button 
        onClick={() => setGameState('leaderboard')} 
        className="leaderboard-button"
      >
        <Trophy className="button-icon" />
        View Leaderboard
      </Button>

      <div className="floating-shapes">
        <div className="shape shape-1"></div>
        <div className="shape shape-2"></div>
        <div className="shape shape-3"></div>
      </div>
    </div>
  );
};

export default FarcasterQuizApp;