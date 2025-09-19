import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { Card } from './components/ui/card';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Timer, Trophy, User, Zap, Brain, Globe, Wallet } from 'lucide-react';
import { AuthKitProvider, SignInButton, useProfile } from '@farcaster/auth-kit';
import '@farcaster/auth-kit/styles.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Farcaster Auth Config
const farcasterConfig = {
  rpcUrl: 'https://mainnet.optimism.io',
  domain: window.location.hostname,
  siweUri: window.location.origin,
  relay: 'https://relay.farcaster.xyz',
};

const FarcasterQuizApp = () => {
  const { 
    isAuthenticated, 
    profile,
    signOut
  } = useProfile();
  
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
  const [questStatus, setQuestStatus] = useState(null);
  const [resetCountdown, setResetCountdown] = useState('');
  const [weeklyLeaderboardStatus, setWeeklyLeaderboardStatus] = useState(null);
  const [weeklyResetCountdown, setWeeklyResetCountdown] = useState('');

  useEffect(() => {
    if (isAuthenticated && profile) {
      initializeAuthenticatedApp();
    } else {
      // For unauthenticated users, still initialize the app with demo functionality
      initializeDemoApp();
    }
  }, [isAuthenticated, profile]);

  // Timer effect for question countdown
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

  // Timer effect for reset countdown
  useEffect(() => {
    if (questStatus && questStatus.reset_time) {
      const updateCountdown = () => {
        const resetTime = new Date(questStatus.reset_time);
        const now = new Date();
        const diff = resetTime - now;
        
        if (diff > 0) {
          const hours = Math.floor(diff / (1000 * 60 * 60));
          const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
          const seconds = Math.floor((diff % (1000 * 60)) / 1000);
          setResetCountdown(`${hours}h ${minutes}m ${seconds}s`);
        } else {
          setResetCountdown('Resetting...');
          // Refresh quest status when reset time is reached
          loadQuestStatus();
        }
      };

      updateCountdown();
      const interval = setInterval(updateCountdown, 1000);
      return () => clearInterval(interval);
    }
  }, [questStatus]);

  // Timer effect for weekly leaderboard reset countdown
  useEffect(() => {
    if (weeklyLeaderboardStatus && weeklyLeaderboardStatus.next_reset) {
      const updateWeeklyCountdown = () => {
        const resetTime = new Date(weeklyLeaderboardStatus.next_reset);
        const now = new Date();
        const diff = resetTime - now;
        
        if (diff > 0) {
          const days = Math.floor(diff / (1000 * 60 * 60 * 24));
          const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
          const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
          
          if (days > 0) {
            setWeeklyResetCountdown(`${days}d ${hours}h ${minutes}m`);
          } else {
            setWeeklyResetCountdown(`${hours}h ${minutes}m`);
          }
        } else {
          setWeeklyResetCountdown('Resetting...');
          // Refresh leaderboard when reset time is reached
          loadLeaderboard();
        }
      };

      updateWeeklyCountdown();
      const interval = setInterval(updateWeeklyCountdown, 60000); // Update every minute
      return () => clearInterval(interval);
    }
  }, [weeklyLeaderboardStatus]);

  const initializeAuthenticatedApp = async () => {
    try {
      setLoading(true);
      
      // Create user object from Farcaster profile
      const farcasterUser = {
        fid: profile.fid,
        username: profile.username,
        display_name: profile.displayName,
        bio: profile.bio,
        pfp_url: profile.pfpUrl
      };
      
      setUser(farcasterUser);
      
      // Get mock authentication token for the backend
      const authResponse = await axios.post(`${API}/auth/mock-login`, null, {
        params: { fid: profile.fid }
      });
      
      const token = authResponse.data.access_token;
      setAuthToken(token);
      
      // Load quest status and leaderboard
      await loadQuestStatus(token);
      await loadLeaderboard();
      await loadWeeklyLeaderboardStatus();
    } catch (error) {
      console.error('Failed to initialize authenticated app:', error);
      initializeDemoApp();
    } finally {
      setLoading(false);
    }
  };

  const initializeDemoApp = async () => {
    try {
      setLoading(true);
      
      // For demo purposes without authentication
      const mockFid = Math.floor(Math.random() * 10000) + 1000;
      const authResponse = await axios.post(`${API}/auth/mock-login`, null, {
        params: { fid: mockFid }
      });
      
      const token = authResponse.data.access_token;
      setAuthToken(token);
      
      // Create demo user
      const demoUser = {
        fid: mockFid,
        username: `demo_user_${mockFid}`,
        display_name: `Demo User ${mockFid}`,
        bio: 'Demo user for testing',
        pfp_url: `https://api.dicebear.com/7.x/avataaars/svg?seed=user${mockFid}`
      };
      
      setUser(demoUser);
      await loadQuestStatus(token);
      await loadLeaderboard();
    } catch (error) {
      console.error('Failed to initialize demo app:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadQuestStatus = async (token = authToken) => {
    try {
      const response = await axios.get(`${API}/user/daily-quest`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setQuestStatus(response.data);
    } catch (error) {
      console.error('Failed to load quest status:', error);
      // Set default quest status for demo
      setQuestStatus({
        attempts_remaining: 3,
        max_attempts: 3,
        reset_time: new Date(new Date().setUTCHours(24, 0, 0, 0)).toISOString(),
        total_score_today: 0,
        can_play: true
      });
    }
  };

  const loadWeeklyLeaderboardStatus = async () => {
    try {
      const response = await axios.get(`${API}/leaderboard/weekly-status`);
      setWeeklyLeaderboardStatus(response.data);
    } catch (error) {
      console.error('Failed to load weekly leaderboard status:', error);
      // Set default weekly status
      const nextMonday = new Date();
      nextMonday.setDate(nextMonday.getDate() + (1 + 7 - nextMonday.getDay()) % 7);
      nextMonday.setUTCHours(0, 0, 0, 0);
      
      setWeeklyLeaderboardStatus({
        next_reset: nextMonday.toISOString(),
        days_until_reset: Math.ceil((nextMonday - new Date()) / (1000 * 60 * 60 * 24)),
        last_reset: new Date().toISOString()
      });
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
      // Check if user can play
      if (!questStatus || !questStatus.can_play) {
        alert(`Daily limit reached! You can play again in ${resetCountdown}`);
        return;
      }

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
      
      // Update quest status after starting
      await loadQuestStatus();
    } catch (error) {
      console.error('Failed to start quiz:', error);
      if (error.response?.status === 429) {
        alert('Daily limit reached! Come back tomorrow for more questions.');
      }
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
      
      // Update quest status from response
      if (response.data.quest_status) {
        setQuestStatus(response.data.quest_status);
      }
      
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
    
    // Safety check: if no current question, quiz should be completed
    if (!currentQuestion) {
      setGameState('completed');
      return null;
    }
    
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
    const sessionPercentage = Math.round((currentQuiz.score / currentQuiz.questions.length) * 100);
    const dailyScore = lastResult?.daily_total_score || questStatus?.total_score_today || 0;
    
    return (
      <div className="completion-container">
        <Card className="completion-card">
          <div className="completion-header">
            <Trophy className="completion-icon" />
            <h1>Daily Quest Complete!</h1>
          </div>
          
          <div className="completion-stats">
            <div className="stat-large">
              <span className="stat-number">{currentQuiz.score}</span>
              <span className="stat-label">This Session</span>
            </div>
            <div className="stat-large">
              <span className="stat-number">{dailyScore}</span>
              <span className="stat-label">Today's Total</span>
            </div>
            <div className="stat-large">
              <span className="stat-number">{questStatus?.attempts_remaining || 0}</span>
              <span className="stat-label">Attempts Left</span>
            </div>
          </div>

          {questStatus?.attempts_remaining > 0 ? (
            <div className="completion-actions">
              <Button onClick={() => startQuiz(selectedCategory)} className="primary">
                Continue Daily Quest
              </Button>
              <Button onClick={() => setGameState('leaderboard')} className="secondary">
                View Leaderboard
              </Button>
              <Button onClick={() => setGameState('home')} className="tertiary">
                Home
              </Button>
            </div>
          ) : (
            <div className="completion-actions">
              <div className="daily-complete-message">
                <h3>🎉 Daily Quest Complete!</h3>
                <p>Come back tomorrow for more questions!</p>
                <p className="reset-countdown">Next reset: {resetCountdown}</p>
              </div>
              <Button onClick={() => setGameState('leaderboard')} className="primary">
                View Leaderboard
              </Button>
              <Button onClick={() => setGameState('home')} className="secondary">
                Home
              </Button>
            </div>
          )}
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

      {!isAuthenticated && (
        <Card className="auth-card">
          <div className="auth-content">
            <h3>Connect with Farcaster</h3>
            <p>Sign in with your Farcaster account to save your progress and compete on the leaderboard!</p>
            <SignInButton />
            <p className="demo-note">Or continue as a demo user below</p>
          </div>
        </Card>
      )}

      {user && (
        <Card className="user-card">
          <div className="user-profile">
            <img src={user.pfp_url} alt={user.display_name} className="user-avatar" />
            <div className="user-info">
              <h3 className="user-name">{user.display_name}</h3>
              <p className="user-username">@{user.username}</p>
              {questStatus && (
                <div className="quest-status">
                  <p className="daily-score">Today's Score: {questStatus.total_score_today}</p>
                  <p className="attempts-remaining">
                    Attempts: {questStatus.attempts_remaining}/{questStatus.max_attempts}
                  </p>
                  {questStatus.attempts_remaining === 0 && (
                    <p className="reset-timer">Reset in: {resetCountdown}</p>
                  )}
                </div>
              )}
            </div>
            {isAuthenticated && (
              <Button onClick={signOut} className="sign-out-button">
                Sign Out
              </Button>
            )}
          </div>
        </Card>
      )}

      <div className="game-modes">
        <Card className={`mode-card crypto-mode ${!questStatus?.can_play ? 'disabled' : ''}`} onClick={() => questStatus?.can_play && startQuiz('crypto')}>
          <div className="mode-icon">
            <Zap />
          </div>
          <h3 className="mode-title">Crypto & Blockchain</h3>
          <p className="mode-description">
            Test your knowledge of cryptocurrencies, DeFi, and blockchain technology
          </p>
          <Badge className="mode-badge">
            {questStatus?.can_play ? `${questStatus.attempts_remaining} Questions Left` : 'Daily Limit Reached'}
          </Badge>
          {!questStatus?.can_play && (
            <p className="reset-info">Reset in: {resetCountdown}</p>
          )}
        </Card>

        <Card className={`mode-card general-mode ${!questStatus?.can_play ? 'disabled' : ''}`} onClick={() => questStatus?.can_play && startQuiz('general')}>
          <div className="mode-icon">
            <Brain />
          </div>
          <h3 className="mode-title">General Knowledge</h3>
          <p className="mode-description">
            Challenge yourself with questions from various topics and subjects
          </p>
          <Badge className="mode-badge">
            {questStatus?.can_play ? `${questStatus.attempts_remaining} Questions Left` : 'Daily Limit Reached'}
          </Badge>
          {!questStatus?.can_play && (
            <p className="reset-info">Reset in: {resetCountdown}</p>
          )}
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

const App = () => {
  return (
    <AuthKitProvider config={farcasterConfig}>
      <FarcasterQuizApp />
    </AuthKitProvider>
  );
};

export default App;