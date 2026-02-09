/**
 * Frontend JavaScript for Exam Generator
 * Handles user interactions, API calls, and UI updates
 */

// API Configuration
const API_BASE_URL = 'http://127.0.0.1:5000/api';

// Global State
let currentPdf = null;
let currentExam = null;
let examStartTime = null;
let timerInterval = null;
let userAnswers = {};

// DOM Elements
const uploadSection = document.getElementById('upload-section');
const configSection = document.getElementById('config-section');
const examSection = document.getElementById('exam-section');
const resultsSection = document.getElementById('results-section');
const attemptsSection = document.getElementById('attempts-section');
const loadingOverlay = document.getElementById('loading-overlay');

// Utility Functions
function showLoading(message = 'Processing...') {
    document.getElementById('loading-message').textContent = message;
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

function showStatus(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.style.display = 'block';
}

function hideAllSections() {
    [uploadSection, configSection, examSection, resultsSection, attemptsSection].forEach(
        section => section.classList.add('hidden')
    );
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Step 1: PDF Upload
document.getElementById('pdf-upload').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        showLoading('Uploading and extracting text from PDF...');
        
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            currentPdf = data.pdf;
            displayPdfInfo(data.pdf, data.summary);
            showStatus('upload-status', 'PDF uploaded successfully!', 'success');
            configSection.classList.remove('hidden');
        } else {
            showStatus('upload-status', data.error || 'Upload failed', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showStatus('upload-status', 'Failed to upload PDF. Is the server running?', 'error');
    } finally {
        hideLoading();
    }
});

function displayPdfInfo(pdf, summary) {
    const pdfInfo = document.getElementById('pdf-info');
    pdfInfo.innerHTML = `
        <h3>📄 ${pdf.original_name}</h3>
        <p><strong>Pages:</strong> ${summary.total_pages}</p>
        <p><strong>Words:</strong> ${summary.total_words.toLocaleString()}</p>
        <p><strong>OCR Used:</strong> ${summary.ocr_used ? 'Yes (scanned document)' : 'No (text-based)'}</p>
    `;
    pdfInfo.classList.remove('hidden');
}

// Step 2: Generate Exam
document.getElementById('generate-btn').addEventListener('click', async () => {
    if (!currentPdf) {
        alert('Please upload a PDF first');
        return;
    }

    const numQuestions = parseInt(document.getElementById('num-questions').value);
    const difficulty = document.getElementById('difficulty').value;

    if (numQuestions < 1 || numQuestions > 50) {
        alert('Please enter between 1 and 50 questions');
        return;
    }

    try {
        showLoading('Generating exam questions with AI...');
        
        const response = await fetch(`${API_BASE_URL}/generate-exam`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pdf_id: currentPdf.id,
                num_questions: numQuestions,
                difficulty: difficulty
            })
        });

        const data = await response.json();

        if (data.success) {
            currentExam = data.exam;
            showStatus('generation-status', 'Exam generated successfully!', 'success');
            setTimeout(() => startExam(), 1000);
        } else {
            showStatus('generation-status', data.error || 'Generation failed', 'error');
        }
    } catch (error) {
        console.error('Generation error:', error);
        showStatus('generation-status', 'Failed to generate exam. Check API key.', 'error');
    } finally {
        hideLoading();
    }
});

// Step 3: Take Exam
function startExam() {
    hideAllSections();
    examSection.classList.remove('hidden');
    
    document.getElementById('exam-title').textContent = currentExam.title;
    document.getElementById('question-counter').textContent = 
        `${currentExam.num_questions} Questions`;
    
    userAnswers = {};
    examStartTime = Date.now();
    startTimer();
    
    displayQuestions();
}

function startTimer() {
    let seconds = 0;
    timerInterval = setInterval(() => {
        seconds++;
        document.getElementById('timer').textContent = `Time: ${formatTime(seconds)}`;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
    }
}

function displayQuestions() {
    const container = document.getElementById('questions-container');
    container.innerHTML = '';

    currentExam.questions.forEach((question, index) => {
        const questionCard = document.createElement('div');
        questionCard.className = 'question-card';
        
        const questionText = document.createElement('div');
        questionText.className = 'question-text';
        questionText.textContent = `${index + 1}. ${question.question_text}`;
        
        const answersList = document.createElement('div');
        answersList.className = 'answers-list';
        
        question.answers.forEach((answer, ansIndex) => {
            const answerOption = document.createElement('label');
            answerOption.className = 'answer-option';
            
            const radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = `question-${question.id}`;
            radio.value = ansIndex;
            radio.addEventListener('change', () => {
                userAnswers[question.id] = ansIndex;
                // Visual feedback
                document.querySelectorAll(`input[name="question-${question.id}"]`).forEach(r => {
                    r.parentElement.classList.remove('selected');
                });
                answerOption.classList.add('selected');
            });
            
            const answerText = document.createElement('span');
            answerText.textContent = answer.text;
            
            answerOption.appendChild(radio);
            answerOption.appendChild(answerText);
            answersList.appendChild(answerOption);
        });
        
        questionCard.appendChild(questionText);
        questionCard.appendChild(answersList);
        container.appendChild(questionCard);
    });
}

// Step 4: Submit Exam
document.getElementById('submit-exam-btn').addEventListener('click', async () => {
    // Check if all questions answered
    const unansweredCount = currentExam.num_questions - Object.keys(userAnswers).length;
    
    if (unansweredCount > 0) {
        const confirm = window.confirm(
            `You have ${unansweredCount} unanswered question(s). Submit anyway?`
        );
        if (!confirm) return;
    }

    stopTimer();
    const timeTaken = Math.floor((Date.now() - examStartTime) / 1000);

    try {
        showLoading('Calculating your score...');
        
        const response = await fetch(`${API_BASE_URL}/submit-attempt`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                exam_id: currentExam.id,
                answers: userAnswers,
                time_taken: timeTaken
            })
        });

        const data = await response.json();

        if (data.success) {
            displayResults(data, timeTaken);
        } else {
            alert('Failed to submit exam: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Submit error:', error);
        alert('Failed to submit exam');
    } finally {
        hideLoading();
    }
});

// Step 5: Display Results
function displayResults(attemptData, timeTaken) {
    hideAllSections();
    resultsSection.classList.remove('hidden');

    const score = attemptData.score;
    const correctCount = Math.round((score / 100) * currentExam.num_questions);
    
    // Update score display
    document.getElementById('score-percentage').textContent = `${Math.round(score)}%`;
    document.getElementById('correct-count').textContent = `${correctCount}/${currentExam.num_questions}`;
    document.getElementById('total-questions').textContent = currentExam.num_questions;
    document.getElementById('time-taken').textContent = formatTime(timeTaken);
    
    // Score message
    let message = '';
    if (score >= 90) message = 'Excellent! 🎉';
    else if (score >= 70) message = 'Great job! 👍';
    else if (score >= 50) message = 'Good effort! 💪';
    else message = 'Keep practicing! 📚';
    
    document.getElementById('score-text').textContent = message;
    
    // Update score circle color
    const scoreCircle = document.querySelector('.score-circle');
    if (score >= 70) {
        scoreCircle.style.background = 'linear-gradient(135deg, #2ECC71, #27ae60)';
    } else if (score >= 50) {
        scoreCircle.style.background = 'linear-gradient(135deg, #F39C12, #E67E22)';
    } else {
        scoreCircle.style.background = 'linear-gradient(135deg, #E74C3C, #C0392B)';
    }
    
    // Display detailed results
    displayDetailedResults();
}

function displayDetailedResults() {
    const container = document.getElementById('results-container');
    container.innerHTML = '';

    currentExam.questions.forEach((question, index) => {
        const questionCard = document.createElement('div');
        questionCard.className = 'question-card';
        
        const questionText = document.createElement('div');
        questionText.className = 'question-text';
        questionText.textContent = `${index + 1}. ${question.question_text}`;
        
        const answersList = document.createElement('div');
        answersList.className = 'answers-list';
        
        const userAnswer = userAnswers[question.id];
        
        question.answers.forEach((answer, ansIndex) => {
            const answerOption = document.createElement('div');
            answerOption.className = 'answer-option';
            
            // Mark correct/incorrect
            if (answer.is_correct) {
                answerOption.classList.add('correct');
            } else if (userAnswer === ansIndex) {
                answerOption.classList.add('incorrect');
            }
            
            const prefix = answer.is_correct ? '✓ ' : (userAnswer === ansIndex ? '✗ ' : '');
            answerOption.textContent = prefix + answer.text;
            
            answersList.appendChild(answerOption);
        });
        
        // Justification
        const justification = document.createElement('div');
        justification.className = 'justification';
        justification.innerHTML = `<strong>Explanation:</strong> ${question.justification}`;
        
        // Source
        const source = document.createElement('div');
        source.className = 'source-info';
        source.innerHTML = `📖 <strong>Source:</strong> Page ${question.source_page}${
            question.source_section ? ` - ${question.source_section}` : ''
        }`;
        
        questionCard.appendChild(questionText);
        questionCard.appendChild(answersList);
        questionCard.appendChild(justification);
        questionCard.appendChild(source);
        container.appendChild(questionCard);
    });
}

// New Exam
document.getElementById('new-exam-btn').addEventListener('click', () => {
    // Reset state
    currentExam = null;
    userAnswers = {};
    stopTimer();
    
    // Show config section
    hideAllSections();
    uploadSection.classList.remove('hidden');
    if (currentPdf) {
        configSection.classList.remove('hidden');
    }
});

// View Past Attempts
document.getElementById('review-attempts-btn').addEventListener('click', async () => {
    try {
        showLoading('Loading past attempts...');
        
        const response = await fetch(`${API_BASE_URL}/attempts/${currentExam.id}`);
        const data = await response.json();
        
        if (data.success) {
            displayAttempts(data.attempts);
            hideAllSections();
            attemptsSection.classList.remove('hidden');
        } else {
            alert('Failed to load attempts');
        }
    } catch (error) {
        console.error('Error loading attempts:', error);
        alert('Failed to load attempts');
    } finally {
        hideLoading();
    }
});

function displayAttempts(attempts) {
    const container = document.getElementById('attempts-container');
    container.innerHTML = '';
    
    if (attempts.length === 0) {
        container.innerHTML = '<p>No past attempts found.</p>';
        return;
    }
    
    attempts.forEach((attempt, index) => {
        const attemptCard = document.createElement('div');
        attemptCard.className = 'attempt-card';
        
        const date = new Date(attempt.attempt_date);
        attemptCard.innerHTML = `
            <h4>Attempt ${attempts.length - index}</h4>
            <div class="attempt-meta">
                <span>📅 ${date.toLocaleDateString()} ${date.toLocaleTimeString()}</span>
                <span>📊 Score: ${Math.round(attempt.score)}%</span>
                <span>⏱️ Time: ${formatTime(attempt.time_taken)}</span>
            </div>
        `;
        
        container.appendChild(attemptCard);
    });
}

document.getElementById('back-to-results-btn').addEventListener('click', () => {
    hideAllSections();
    resultsSection.classList.remove('hidden');
});

// Initialize
console.log('Exam Generator initialized');
console.log('Make sure the backend server is running on http://127.0.0.1:5000');
