// Flashcards App - Core Logic

// Constants
const STORAGE_KEY = 'flashcards_progress';
const NEW_CARDS_PER_DAY = 20;
const INITIAL_EASE = 2.5;
const MIN_EASE = 1.3;

// State
let state = {
  cards: [],
  currentCard: null,
  currentIndex: 0,
  todayNew: 0,
  todayReview: 0,
  queue: [],
};

// DOM Elements
const elements = {
  card: document.getElementById('card'),
  categoryBadge: document.getElementById('category-badge'),
  questionText: document.getElementById('question-text'),
  answerContainer: document.getElementById('answer-container'),
  answerText: document.getElementById('answer-text'),
  showAnswerBtn: document.getElementById('show-answer-btn'),
  showAnswerContainer: document.getElementById('show-answer-container'),
  ratingContainer: document.getElementById('rating-container'),
  emptyState: document.getElementById('empty-state'),
  progressText: document.getElementById('progress-text'),
  todayNew: document.getElementById('today-new'),
  todayReview: document.getElementById('today-review'),
  btnAgain: document.getElementById('btn-again'),
  btnGood: document.getElementById('btn-good'),
  btnEasy: document.getElementById('btn-easy'),
  goodInterval: document.getElementById('good-interval'),
  easyInterval: document.getElementById('easy-interval'),
};

// Initialize dark mode based on system preference
function initDarkMode() {
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.classList.add('dark');
  }

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (e.matches) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  });
}

// Load progress from localStorage
function loadProgress() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    return JSON.parse(saved);
  }
  return {};
}

// Save progress to localStorage
function saveProgress(progress) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}

// Get card progress or create default
function getCardProgress(cardId, progress) {
  if (progress[cardId]) {
    return progress[cardId];
  }
  return {
    interval: 0,
    ease: INITIAL_EASE,
    nextReview: 0,
    reviews: 0,
    lapses: 0,
  };
}

// Calculate next interval based on rating
function calculateInterval(cardProgress, rating) {
  const now = Date.now();
  let { interval, ease } = cardProgress;

  switch (rating) {
    case 'again':
      // Failed - reset to 1 minute, decrease ease
      interval = 1 / 1440; // 1 minute in days
      ease = Math.max(MIN_EASE, ease - 0.2);
      break;
    case 'good':
      // Correct - increase interval
      if (interval === 0) {
        interval = 1; // First review: 1 day
      } else {
        interval = interval * ease;
      }
      break;
    case 'easy':
      // Easy - increase interval more, boost ease
      if (interval === 0) {
        interval = 4; // First review: 4 days
      } else {
        interval = interval * ease * 1.3;
      }
      ease = ease + 0.15;
      break;
  }

  const nextReview = now + interval * 24 * 60 * 60 * 1000;

  return {
    interval,
    ease,
    nextReview,
    reviews: cardProgress.reviews + 1,
    lapses: rating === 'again' ? cardProgress.lapses + 1 : cardProgress.lapses,
  };
}

// Format interval for display
function formatInterval(days) {
  if (days < 1 / 60) return '<1 мин';
  if (days < 1 / 24) return `${Math.round(days * 24 * 60)} мин`;
  if (days < 1) return `${Math.round(days * 24)} ч`;
  if (days < 30) return `${Math.round(days)} дн`;
  if (days < 365) return `${Math.round(days / 30)} мес`;
  return `${Math.round(days / 365)} г`;
}

// Check if it's a new day since last session
function isNewDay(lastDate) {
  if (!lastDate) return true;
  const last = new Date(lastDate);
  const now = new Date();
  return last.toDateString() !== now.toDateString();
}

// Fisher-Yates shuffle
function shuffle(array) {
  const arr = [...array];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// Build the study queue for today
function buildQueue(progress) {
  const now = Date.now();
  const todayKey = new Date().toDateString();
  const sessionData = JSON.parse(localStorage.getItem('flashcards_session') || '{}');

  // Reset daily counters if new day
  if (isNewDay(sessionData.date)) {
    sessionData.date = todayKey;
    sessionData.newStudied = 0;
    sessionData.reviewed = 0;
    localStorage.setItem('flashcards_session', JSON.stringify(sessionData));
  }

  const queue = [];
  const reviewCards = [];
  const newCards = [];

  CARDS.forEach((card) => {
    const cardProgress = getCardProgress(card.id, progress);

    if (cardProgress.reviews === 0) {
      // New card
      newCards.push({ card, progress: cardProgress, isNew: true });
    } else if (cardProgress.nextReview <= now) {
      // Due for review
      reviewCards.push({ card, progress: cardProgress, isNew: false });
    }
  });

  // Shuffle review cards (so order is random each session)
  const shuffledReview = shuffle(reviewCards);

  // Shuffle new cards too
  const shuffledNew = shuffle(newCards);

  // Add review cards first
  queue.push(...shuffledReview);

  // Add new cards up to daily limit
  const newCardsToAdd = Math.min(
    NEW_CARDS_PER_DAY - sessionData.newStudied,
    shuffledNew.length
  );
  queue.push(...shuffledNew.slice(0, Math.max(0, newCardsToAdd)));

  return {
    queue,
    todayNew: newCardsToAdd,
    todayReview: reviewCards.length,
  };
}

// Display current card
function displayCard() {
  if (state.queue.length === 0) {
    showEmptyState();
    return;
  }

  const { card, progress, isNew } = state.queue[state.currentIndex];
  state.currentCard = { card, progress, isNew };

  // Update UI
  elements.categoryBadge.textContent = card.category;
  elements.questionText.textContent = card.question;
  elements.answerText.textContent = card.answer;

  // Update progress indicator
  elements.progressText.textContent = `${state.currentIndex + 1} / ${state.queue.length}`;

  // Update session counters
  elements.todayNew.textContent = state.todayNew;
  elements.todayReview.textContent = state.todayReview;

  // Calculate and show intervals
  const goodInterval = progress.interval === 0 ? 1 : progress.interval * progress.ease;
  const easyInterval = progress.interval === 0 ? 4 : progress.interval * progress.ease * 1.3;
  elements.goodInterval.textContent = formatInterval(goodInterval);
  elements.easyInterval.textContent = formatInterval(easyInterval);

  // Reset to question view
  showQuestion();
}

// Show question state
function showQuestion() {
  elements.answerContainer.classList.add('hidden');
  elements.showAnswerContainer.classList.remove('hidden');
  elements.ratingContainer.classList.add('hidden');
  elements.card.classList.remove('flipping');
}

// Show answer state
function showAnswer() {
  elements.card.classList.add('flipping');
  setTimeout(() => {
    elements.answerContainer.classList.remove('hidden');
    elements.showAnswerContainer.classList.add('hidden');
    elements.ratingContainer.classList.remove('hidden');
    elements.card.classList.remove('flipping');
  }, 250);
}

// Show empty state
function showEmptyState() {
  elements.card.parentElement.classList.add('hidden');
  elements.ratingContainer.classList.add('hidden');
  elements.emptyState.classList.remove('hidden');
}

// Handle rating
function handleRating(rating) {
  const { card, progress, isNew } = state.currentCard;

  // Calculate new progress
  const newProgress = calculateInterval(progress, rating);

  // Save progress
  const allProgress = loadProgress();
  allProgress[card.id] = newProgress;
  saveProgress(allProgress);

  // Update session data
  const sessionData = JSON.parse(localStorage.getItem('flashcards_session') || '{}');
  if (isNew) {
    sessionData.newStudied = (sessionData.newStudied || 0) + 1;
  } else {
    sessionData.reviewed = (sessionData.reviewed || 0) + 1;
  }
  localStorage.setItem('flashcards_session', JSON.stringify(sessionData));

  // If "again", move card to end of queue
  if (rating === 'again') {
    state.queue.push(state.queue[state.currentIndex]);
  }

  // Move to next card
  state.currentIndex++;

  if (state.currentIndex >= state.queue.length) {
    showEmptyState();
  } else {
    displayCard();
  }
}

// Initialize app
function init() {
  initDarkMode();

  const progress = loadProgress();
  const queueData = buildQueue(progress);

  state.queue = queueData.queue;
  state.todayNew = queueData.todayNew;
  state.todayReview = queueData.todayReview;
  state.currentIndex = 0;

  // Event listeners
  elements.showAnswerBtn.addEventListener('click', showAnswer);
  elements.btnAgain.addEventListener('click', () => handleRating('again'));
  elements.btnGood.addEventListener('click', () => handleRating('good'));
  elements.btnEasy.addEventListener('click', () => handleRating('easy'));

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (elements.showAnswerContainer.classList.contains('hidden')) {
      // Rating mode
      if (e.key === '1') handleRating('again');
      if (e.key === '2') handleRating('good');
      if (e.key === '3') handleRating('easy');
    } else {
      // Question mode
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        showAnswer();
      }
    }
  });

  displayCard();
}

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', init);
