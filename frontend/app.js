/**
 * StudyWise AI Exam Generator - Frontend Application Logic
 * Single Page Application (SPA) supporting:
 * - Dynamic Dashboard with metrics & search
 * - Exam Creation Wizard (PDF with OCR, Topics, Pasted text)
 * - Interactive Question Bank & Live Editor (Edit, Delete, Add, AI Regenerate)
 * - Student Exam Player (Question palette, countdown timer, flagging)
 * - Auto-Grading & AI Subjective Evaluation
 * - Multi-Format Export Hub (Student & Teacher PDF, Word, Moodle GIFT, Google Forms CSV)
 * - AI Settings & Multi-Provider switcher (Gemini, OpenAI, Demo Engine)
 */

const API_BASE = 'http://127.0.0.1:5000/api';

class AppState {
    constructor() {
        this.currentView = 'dashboard';
        this.currentPdf = null;
        this.currentExam = null;
        this.currentAttempt = null;
        this.allExams = [];

        // Exam Player State
        this.activeQuestionIndex = 0;
        this.userAnswers = {};
        this.flaggedQuestions = new Set();
        this.timerInterval = null;
        this.timerSecondsRemaining = 0;
        this.examStartTime = null;

        // Active regeneration target
        this.regeneratingQuestionId = null;

        // Settings
        this.settings = this.loadSettings();

        this.init();
    }

    init() {
        this.bindEvents();
        this.updateProviderBadge();
        this.navigateTo('dashboard');
    }

    // -------------------------------------------------------------
    // Settings & Persistence
    // -------------------------------------------------------------
    loadSettings() {
        const defaults = {
            provider: 'demo',
            geminiKey: '',
            openaiKey: ''
        };
        try {
            const saved = localStorage.getItem('studywise_settings');
            return saved ? { ...defaults, ...JSON.parse(saved) } : defaults;
        } catch (e) {
            return defaults;
        }
    }

    saveSettings() {
        const provider = document.getElementById('settings-provider-select').value;
        const geminiKey = document.getElementById('settings-gemini-key').value.trim();
        const openaiKey = document.getElementById('settings-openai-key').value.trim();

        this.settings = { provider, geminiKey, openaiKey };
        localStorage.setItem('studywise_settings', JSON.stringify(this.settings));
        this.updateProviderBadge();
        this.closeSettings();
        this.showToast('Settings saved successfully!', 'success');
    }

    updateProviderBadge() {
        const badgeLabel = document.getElementById('provider-label');
        if (!badgeLabel) return;

        if (this.settings.provider === 'gemini') {
            badgeLabel.textContent = 'Gemini AI';
        } else if (this.settings.provider === 'openai') {
            badgeLabel.textContent = 'OpenAI';
        } else {
            badgeLabel.textContent = 'Demo Engine';
        }
    }

    getActiveApiKey() {
        if (this.settings.provider === 'gemini') return this.settings.geminiKey;
        if (this.settings.provider === 'openai') return this.settings.openaiKey;
        return '';
    }

    openSettings() {
        document.getElementById('settings-provider-select').value = this.settings.provider;
        document.getElementById('settings-gemini-key').value = this.settings.geminiKey || '';
        document.getElementById('settings-openai-key').value = this.settings.openaiKey || '';
        this.handleProviderChange(this.settings.provider);
        document.getElementById('settings-test-status').textContent = '';
        document.getElementById('modal-settings').classList.remove('hidden');
    }

    closeSettings() {
        document.getElementById('modal-settings').classList.add('hidden');
    }

    handleProviderChange(provider) {
        document.getElementById('gemini-key-group').classList.toggle('hidden', provider !== 'gemini');
        document.getElementById('openai-key-group').classList.toggle('hidden', provider !== 'openai');
    }

    async testAIConnection() {
        const statusEl = document.getElementById('settings-test-status');
        const provider = document.getElementById('settings-provider-select').value;
        const apiKey = (provider === 'gemini') 
            ? document.getElementById('settings-gemini-key').value.trim()
            : document.getElementById('settings-openai-key').value.trim();

        statusEl.textContent = 'Testing connection...';
        statusEl.style.color = '#4F46E5';

        try {
            const res = await fetch(`${API_BASE}/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, api_key: apiKey })
            });
            const data = await res.json();
            if (data.success) {
                statusEl.textContent = '✔ ' + data.message;
                statusEl.style.color = '#10B981';
            } else {
                statusEl.textContent = '✖ ' + (data.error || 'Connection failed');
                statusEl.style.color = '#EF4444';
            }
        } catch (e) {
            statusEl.textContent = '✖ Unable to connect to server';
            statusEl.style.color = '#EF4444';
        }
    }

    // -------------------------------------------------------------
    // Navigation & Routing
    // -------------------------------------------------------------
    navigateTo(viewId, params = {}) {
        // Stop timer if leaving player view without submitting
        if (this.currentView === 'player' && viewId !== 'player') {
            this.stopTimer();
        }

        this.currentView = viewId;

        // Toggle Views
        const views = ['dashboard', 'wizard', 'editor', 'player', 'results', 'export'];
        views.forEach(v => {
            const el = document.getElementById(`view-${v}`);
            if (el) el.classList.toggle('hidden', v !== viewId);
        });

        // Update nav links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.view === viewId);
        });

        // Initialize view data
        if (viewId === 'dashboard') {
            this.loadDashboard();
        } else if (viewId === 'editor') {
            if (this.currentExam) this.loadEditor(this.currentExam);
        } else if (viewId === 'export') {
            this.loadExportHub();
        }

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // -------------------------------------------------------------
    // Dashboard Logic
    // -------------------------------------------------------------
    async loadDashboard() {
        try {
            const res = await fetch(`${API_BASE}/analytics`);
            const data = await res.json();
            if (data.success) {
                const s = data.summary;
                document.getElementById('stat-total-exams').textContent = s.total_exams || 0;
                document.getElementById('stat-total-questions').textContent = s.total_questions || 0;
                document.getElementById('stat-total-attempts').textContent = s.total_attempts || 0;
                document.getElementById('stat-avg-score').textContent = `${s.avg_score || 0}%`;

                this.allExams = data.recent_exams || [];
                this.renderExamsTable(this.allExams);
            }
        } catch (e) {
            console.error('Failed to load dashboard data:', e);
        }
    }

    renderExamsTable(exams) {
        const container = document.getElementById('exams-table-container');
        if (!exams || exams.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📂</span>
                    <p>No exams created yet. Click "Create New Exam" to generate your first test!</p>
                </div>
            `;
            return;
        }

        let rows = exams.map(exam => {
            const diffClass = `badge-${exam.difficulty || 'medium'}`;
            const dateStr = exam.created_date ? new Date(exam.created_date).toLocaleDateString() : 'Recent';
            return `
                <tr>
                    <td>
                        <div class="table-title">${this.escapeHtml(exam.title)}</div>
                        <div style="font-size: 0.78rem; color: #64748B;">Source: ${this.escapeHtml(exam.source_ref || exam.source_type || 'Custom')}</div>
                    </td>
                    <td><span class="badge-tag ${diffClass}">${exam.difficulty || 'Medium'}</span></td>
                    <td><strong>${exam.num_questions}</strong> Questions</td>
                    <td>${exam.time_limit ? exam.time_limit + ' mins' : 'Untimed'}</td>
                    <td>${dateStr}</td>
                    <td>
                        <div class="btn-group">
                            <button class="btn btn-primary" style="padding: 6px 12px; font-size: 0.8rem;" onclick="appState.openExamFromDashboard(${exam.id}, 'player')">🎯 Take</button>
                            <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8rem;" onclick="appState.openExamFromDashboard(${exam.id}, 'editor')">📝 Edit</button>
                            <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8rem;" onclick="appState.openExamFromDashboard(${exam.id}, 'export')">📥 Export</button>
                            <button class="btn btn-secondary" style="padding: 6px 10px; font-size: 0.8rem; color: #EF4444;" title="Delete" onclick="appState.deleteExam(${exam.id})">🗑️</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Exam Title</th>
                        <th>Difficulty</th>
                        <th>Length</th>
                        <th>Duration</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    filterExams(query) {
        if (!query.trim()) {
            this.renderExamsTable(this.allExams);
            return;
        }
        const q = query.toLowerCase();
        const filtered = this.allExams.filter(e => 
            (e.title && e.title.toLowerCase().includes(q)) ||
            (e.source_ref && e.source_ref.toLowerCase().includes(q))
        );
        this.renderExamsTable(filtered);
    }

    async openExamFromDashboard(examId, targetView) {
        try {
            this.showLoading('Loading exam details...');
            const res = await fetch(`${API_BASE}/exam/${examId}`);
            const data = await res.json();
            if (data.success) {
                this.currentExam = data.exam;
                if (targetView === 'player') {
                    this.startExamWithCurrent();
                } else {
                    this.navigateTo(targetView);
                }
            } else {
                this.showToast(data.error || 'Failed to load exam', 'error');
            }
        } catch (e) {
            this.showToast('Network error while loading exam', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async deleteExam(examId) {
        if (!confirm('Are you sure you want to delete this exam and all student attempt records?')) {
            return;
        }
        try {
            const res = await fetch(`${API_BASE}/exam/${examId}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                this.showToast('Exam deleted successfully', 'success');
                this.loadDashboard();
            } else {
                this.showToast(data.error || 'Failed to delete exam', 'error');
            }
        } catch (e) {
            this.showToast('Failed to delete exam', 'error');
        }
    }

    // -------------------------------------------------------------
    // Exam Creation Wizard Logic
    // -------------------------------------------------------------
    startWizardWithSource(source) {
        this.navigateTo('wizard');
        this.switchSourceTab(source);
    }

    switchSourceTab(source) {
        document.querySelectorAll('.tab-pill').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.source === source);
        });

        document.getElementById('pane-source-pdf').classList.toggle('hidden', source !== 'pdf');
        document.getElementById('pane-source-topic').classList.toggle('hidden', source !== 'topic');
        document.getElementById('pane-source-text').classList.toggle('hidden', source !== 'text');

        if (source === 'topic') {
            document.getElementById('input-topic').focus();
        } else if (source === 'text') {
            document.getElementById('input-raw-text').focus();
        }
    }

    bindEvents() {
        // Navigation links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                this.navigateTo(link.dataset.view);
            });
        });

        // Dropzone & File Input
        const fileInput = document.getElementById('pdf-file-input');
        const dropzone = document.getElementById('dropzone');

        if (fileInput && dropzone) {
            fileInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files[0]) {
                    this.uploadDocument(e.target.files[0]);
                }
            });

            dropzone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropzone.classList.add('drag-over');
            });
            dropzone.addEventListener('dragleave', () => {
                dropzone.classList.remove('drag-over');
            });
            dropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropzone.classList.remove('drag-over');
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    this.uploadDocument(e.dataTransfer.files[0]);
                }
            });
        }
    }

    async uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);

        this.showLoading(`Extracting text & analyzing ${file.name}...`);
        try {
            const res = await fetch(`${API_BASE}/upload`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                this.currentPdf = data.pdf;
                const summaryEl = document.getElementById('pdf-upload-summary');
                summaryEl.innerHTML = `
                    <div style="font-weight: 700; color: #1E1B4B; margin-bottom: 4px;">📄 ${this.escapeHtml(data.pdf.original_name)}</div>
                    <div>Pages: <strong>${data.summary.total_pages}</strong> &nbsp;•&nbsp; Words: <strong>${data.summary.total_words.toLocaleString()}</strong> &nbsp;•&nbsp; OCR Used: <strong>${data.summary.ocr_used ? 'Yes' : 'No'}</strong></div>
                    <div style="font-style: italic; color: #4B5563; margin-top: 6px; font-size: 0.8rem;">"${this.escapeHtml(data.preview_text.slice(0, 160))}..."</div>
                `;
                summaryEl.classList.remove('hidden');

                // Pre-fill exam title
                const baseName = data.pdf.original_name.replace(/\.[^/.]+$/, "");
                const titleInput = document.getElementById('exam-title-input');
                if (!titleInput.value) {
                    titleInput.value = `Assessment: ${baseName}`;
                }
                this.showToast('Document processed successfully!', 'success');
            } else {
                this.showToast(data.error || 'Upload failed', 'error');
            }
        } catch (e) {
            this.showToast('Failed to upload document. Is the server running?', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async handleGenerateExam() {
        const activeSourceBtn = document.querySelector('.tab-pill.active');
        const sourceType = activeSourceBtn ? activeSourceBtn.dataset.source : 'pdf';

        const title = document.getElementById('exam-title-input').value.trim();
        const difficulty = document.getElementById('select-difficulty').value;
        const targetAudience = document.getElementById('select-audience').value;
        const timeLimit = parseInt(document.getElementById('input-time-limit').value) || 0;
        const passingScore = parseFloat(document.getElementById('input-pass-score').value) || 70;

        const countMcq = parseInt(document.getElementById('count-mcq').value) || 0;
        const countTf = parseInt(document.getElementById('count-tf').value) || 0;
        const countSa = parseInt(document.getElementById('count-sa').value) || 0;
        const countEssay = parseInt(document.getElementById('count-essay').value) || 0;

        const qConfig = {
            mcq: countMcq,
            true_false: countTf,
            short_answer: countSa,
            essay: countEssay
        };

        const totalQ = countMcq + countTf + countSa + countEssay;
        if (totalQ <= 0) {
            alert('Please specify at least 1 question to generate.');
            return;
        }

        const payload = {
            source_type: sourceType,
            title: title,
            difficulty: difficulty,
            target_audience: targetAudience,
            time_limit: timeLimit,
            passing_score: passingScore,
            question_config: qConfig,
            provider: this.settings.provider,
            api_key: this.getActiveApiKey()
        };

        if (sourceType === 'pdf') {
            if (!this.currentPdf) {
                alert('Please upload a PDF document first.');
                return;
            }
            payload.pdf_id = this.currentPdf.id;
        } else if (sourceType === 'topic') {
            const topic = document.getElementById('input-topic').value.trim();
            if (!topic) {
                alert('Please enter a subject or curriculum topic.');
                return;
            }
            payload.topic = topic;
        } else if (sourceType === 'text') {
            const text = document.getElementById('input-raw-text').value.trim();
            if (!text) {
                alert('Please paste some text notes or syllabus content.');
                return;
            }
            payload.raw_text = text;
        }

        this.showLoading(`Formulating ${totalQ} questions using ${this.settings.provider.toUpperCase()}...`);

        try {
            const res = await fetch(`${API_BASE}/generate-exam`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                this.currentExam = data.exam;
                this.showToast('Exam generated successfully!', 'success');
                this.navigateTo('editor');
            } else {
                this.showToast(data.error || 'Exam generation failed', 'error');
            }
        } catch (e) {
            this.showToast('Server error during exam generation', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // -------------------------------------------------------------
    // Question Bank & Live Editor Logic
    // -------------------------------------------------------------
    loadEditor(exam) {
        document.getElementById('editor-exam-title').textContent = exam.title;
        document.getElementById('editor-exam-meta').textContent = 
            `${exam.num_questions} Questions • ${exam.total_points || exam.num_questions} Total Points • ${exam.difficulty.toUpperCase()} • Level: ${exam.target_audience || 'General'}`;

        const container = document.getElementById('editor-questions-list');
        if (!exam.questions || exam.questions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📝</span>
                    <p>No questions found in this exam. Click "Add Question" to create one.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = exam.questions.map((q, idx) => {
            return this.renderEditorQuestionCard(q, idx + 1);
        }).join('');
    }

    renderEditorQuestionCard(q, index) {
        let optionsHtml = '';
        if (q.question_type === 'mcq' || q.question_type === 'true_false') {
            optionsHtml = `
                <div class="editor-options-list">
                    ${q.answers.map((ans, optIdx) => `
                        <div class="editor-option-row ${ans.is_correct ? 'is-correct' : ''}">
                            <input type="radio" name="opt-correct-${q.id}" value="${optIdx}" ${ans.is_correct ? 'checked' : ''} onchange="appState.handleEditorCorrectChange(${q.id}, ${optIdx})">
                            <input type="text" class="editor-opt-input" value="${this.escapeHtml(ans.text)}" onchange="appState.handleEditorOptionTextChange(${q.id}, ${optIdx}, this.value)">
                            ${ans.is_correct ? '<span style="font-size: 0.75rem; color: #059669; font-weight: 700;">✔ CORRECT</span>' : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            optionsHtml = `
                <div style="margin: 12px 0;">
                    <label style="font-size: 0.82rem; font-weight: 700; color: #475569;">Expected Model Response / Scoring Rubric:</label>
                    <textarea class="form-group textarea" style="width: 100%; padding: 8px; font-size: 0.9rem;" rows="3" onchange="appState.handleEditorRubricChange(${q.id}, this.value)">${this.escapeHtml(q.correct_answer || q.rubric || '')}</textarea>
                </div>
            `;
        }

        return `
            <div class="question-card" id="q-card-${q.id}">
                <div class="card-top-bar">
                    <div class="badge-row">
                        <span class="badge-pill pill-type">Q${index} • ${q.question_type.replace('_', ' ').toUpperCase()}</span>
                        <span class="badge-pill pill-points">${q.points} pt${q.points !== 1 ? 's' : ''}</span>
                        ${q.source_page ? `<span class="badge-pill pill-source">📖 Page ${q.source_page}</span>` : ''}
                    </div>
                    <div style="font-size: 0.85rem; color: #64748B;">
                        Points: <input type="number" min="0.5" max="50" step="0.5" value="${q.points}" style="width: 55px; padding: 2px 6px; font-weight: 700;" onchange="appState.handleEditorPointsChange(${q.id}, this.value)">
                    </div>
                </div>

                <textarea class="question-edit-text" rows="2" onchange="appState.handleEditorTextChange(${q.id}, this.value)">${this.escapeHtml(q.question_text)}</textarea>

                ${optionsHtml}

                <div class="editor-justification-box">
                    <strong>Pedagogical Explanation:</strong>
                    <textarea style="width: 100%; border: none; background: transparent; font-size: 0.88rem; outline: none; margin-top: 4px; resize: vertical;" rows="2" onchange="appState.handleEditorJustificationChange(${q.id}, this.value)">${this.escapeHtml(q.justification || '')}</textarea>
                </div>

                <div class="editor-card-actions">
                    <button class="btn btn-secondary" style="font-size: 0.82rem; padding: 6px 12px;" onclick="appState.openRegenerateModal(${q.id})">
                        🪄 AI Regenerate
                    </button>
                    <button class="btn btn-danger" style="font-size: 0.82rem; padding: 6px 12px;" onclick="appState.deleteQuestion(${q.id})">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        `;
    }

    async handleEditorTextChange(qId, newText) {
        await this.patchQuestion(qId, { question_text: newText });
    }

    async handleEditorPointsChange(qId, newPoints) {
        await this.patchQuestion(qId, { points: parseFloat(newPoints) || 1.0 });
    }

    async handleEditorJustificationChange(qId, newJust) {
        await this.patchQuestion(qId, { justification: newJust });
    }

    async handleEditorRubricChange(qId, newRubric) {
        await this.patchQuestion(qId, { correct_answer: newRubric, rubric: newRubric });
    }

    async handleEditorOptionTextChange(qId, optIndex, newText) {
        const q = this.currentExam.questions.find(x => x.id === qId);
        if (!q || !q.answers[optIndex]) return;
        q.answers[optIndex].text = newText;
        await this.patchQuestion(qId, { answers: q.answers });
    }

    async handleEditorCorrectChange(qId, selectedIdx) {
        const q = this.currentExam.questions.find(x => x.id === qId);
        if (!q) return;
        q.answers.forEach((ans, i) => {
            ans.is_correct = (i === selectedIdx);
        });
        await this.patchQuestion(qId, { 
            answers: q.answers,
            correct_answer: q.answers[selectedIdx].text 
        });
        // Re-render editor card
        const idx = this.currentExam.questions.findIndex(x => x.id === qId);
        const cardEl = document.getElementById(`q-card-${qId}`);
        if (cardEl) {
            cardEl.outerHTML = this.renderEditorQuestionCard(q, idx + 1);
        }
    }

    async patchQuestion(qId, data) {
        try {
            const res = await fetch(`${API_BASE}/questions/${qId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const resData = await res.json();
            if (resData.success) {
                // Update local model
                const qIdx = this.currentExam.questions.findIndex(x => x.id === qId);
                if (qIdx !== -1) {
                    this.currentExam.questions[qIdx] = resData.question;
                }
                this.showToast('Question updated', 'success');
            }
        } catch (e) {
            console.error('Failed to update question:', e);
        }
    }

    async deleteQuestion(qId) {
        if (!confirm('Delete this question from the exam?')) return;
        try {
            const res = await fetch(`${API_BASE}/questions/${qId}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                this.currentExam.questions = this.currentExam.questions.filter(x => x.id !== qId);
                this.loadEditor(this.currentExam);
                this.showToast('Question deleted', 'success');
            }
        } catch (e) {
            this.showToast('Failed to delete question', 'error');
        }
    }

    // Modal: AI Regenerate Question
    openRegenerateModal(qId) {
        this.regeneratingQuestionId = qId;
        document.getElementById('regen-instruction').value = '';
        document.getElementById('modal-regenerate').classList.remove('hidden');
    }

    closeRegenerateModal() {
        this.regeneratingQuestionId = null;
        document.getElementById('modal-regenerate').classList.add('hidden');
    }

    async confirmRegenerateQuestion() {
        if (!this.regeneratingQuestionId) return;
        const qId = this.regeneratingQuestionId;
        const instruction = document.getElementById('regen-instruction').value.trim();
        this.closeRegenerateModal();

        this.showLoading('AI is regenerating question with your guidance...');
        try {
            const res = await fetch(`${API_BASE}/questions/${qId}/regenerate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    instruction: instruction,
                    provider: this.settings.provider,
                    api_key: this.getActiveApiKey()
                })
            });
            const data = await res.json();
            if (data.success) {
                const qIdx = this.currentExam.questions.findIndex(x => x.id === qId);
                if (qIdx !== -1) {
                    this.currentExam.questions[qIdx] = data.question;
                }
                this.loadEditor(this.currentExam);
                this.showToast('Question regenerated successfully!', 'success');
            } else {
                this.showToast(data.error || 'Failed to regenerate question', 'error');
            }
        } catch (e) {
            this.showToast('Error during regeneration', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Modal: Add Custom Question
    openAddQuestionModal() {
        document.getElementById('new-q-text').value = '';
        document.getElementById('new-opt-0').value = '';
        document.getElementById('new-opt-1').value = '';
        document.getElementById('new-opt-2').value = '';
        document.getElementById('new-opt-3').value = '';
        document.getElementById('new-q-model-ans').value = '';
        document.getElementById('new-q-justification').value = '';
        this.toggleNewQuestionFields('mcq');
        document.getElementById('modal-add-question').classList.remove('hidden');
    }

    closeAddQuestionModal() {
        document.getElementById('modal-add-question').classList.add('hidden');
    }

    toggleNewQuestionFields(qType) {
        document.getElementById('new-q-mcq-block').classList.toggle('hidden', qType !== 'mcq');
        document.getElementById('new-q-tf-block').classList.toggle('hidden', qType !== 'true_false');
        document.getElementById('new-q-subjective-block').classList.toggle('hidden', qType === 'mcq' || qType === 'true_false');
    }

    async saveNewQuestion() {
        if (!this.currentExam) return;
        const qType = document.getElementById('new-q-type').value;
        const text = document.getElementById('new-q-text').value.trim();
        const points = parseFloat(document.getElementById('new-q-points').value) || 1.0;
        const page = parseInt(document.getElementById('new-q-page').value) || 1;
        const justification = document.getElementById('new-q-justification').value.trim();

        if (!text) {
            alert('Please enter a question text.');
            return;
        }

        let answers = [];
        let correctAnswer = '';

        if (qType === 'mcq') {
            const corrRadio = document.querySelector('input[name="new-correct-opt"]:checked');
            const corrIdx = corrRadio ? parseInt(corrRadio.value) : 0;
            for (let i = 0; i < 4; i++) {
                const optVal = document.getElementById(`new-opt-${i}`).value.trim() || `Option ${i+1}`;
                const isCorr = (i === corrIdx);
                answers.push({ text: optVal, is_correct: isCorr });
                if (isCorr) correctAnswer = optVal;
            }
        } else if (qType === 'true_false') {
            const corrRadio = document.querySelector('input[name="new-tf-val"]:checked');
            const isTrue = corrRadio ? (corrRadio.value === 'True') : true;
            answers = [
                { text: 'True', is_correct: isTrue },
                { text: 'False', is_correct: !isTrue }
            ];
            correctAnswer = isTrue ? 'True' : 'False';
        } else {
            correctAnswer = document.getElementById('new-q-model-ans').value.trim();
        }

        const payload = {
            question_text: text,
            question_type: qType,
            answers: answers,
            correct_answer: correctAnswer,
            points: points,
            justification: justification,
            rubric: correctAnswer,
            source_page: page,
            source_section: 'Custom Question'
        };

        try {
            const res = await fetch(`${API_BASE}/exam/${this.currentExam.id}/questions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                this.currentExam.questions.push(data.question);
                this.loadEditor(this.currentExam);
                this.closeAddQuestionModal();
                this.showToast('Question added to exam!', 'success');
            } else {
                this.showToast(data.error || 'Failed to add question', 'error');
            }
        } catch (e) {
            this.showToast('Error saving question', 'error');
        }
    }

    // -------------------------------------------------------------
    // Student Exam Player Logic
    // -------------------------------------------------------------
    startExamWithCurrent() {
        if (!this.currentExam || !this.currentExam.questions || this.currentExam.questions.length === 0) {
            alert('Please generate or select an exam with questions first.');
            return;
        }

        this.userAnswers = {};
        this.flaggedQuestions.clear();
        this.activeQuestionIndex = 0;
        this.examStartTime = Date.now();

        document.getElementById('player-exam-title').textContent = this.currentExam.title;

        this.navigateTo('player');
        this.renderQuestionPalette();
        this.renderActiveQuestion();

        // Start Timer
        const timeLimitMins = this.currentExam.time_limit || 0;
        this.startTimer(timeLimitMins);
    }

    startTimer(minutes) {
        this.stopTimer();
        const timerBox = document.getElementById('player-timer-container');
        const timerText = document.getElementById('player-timer-text');

        if (minutes <= 0) {
            // Untimed: count upwards
            let elapsed = 0;
            timerBox.className = 'timer-box';
            timerText.textContent = '00:00';
            this.timerInterval = setInterval(() => {
                elapsed++;
                const m = Math.floor(elapsed / 60).toString().padStart(2, '0');
                const s = (elapsed % 60).toString().padStart(2, '0');
                timerText.textContent = `${m}:${s}`;
            }, 1000);
            return;
        }

        // Countdown mode
        this.timerSecondsRemaining = minutes * 60;
        this.timerInterval = setInterval(() => {
            this.timerSecondsRemaining--;
            if (this.timerSecondsRemaining <= 0) {
                this.stopTimer();
                alert('Time has expired! Submitting your exam now.');
                this.submitExam();
                return;
            }

            const m = Math.floor(this.timerSecondsRemaining / 60).toString().padStart(2, '0');
            const s = (this.timerSecondsRemaining % 60).toString().padStart(2, '0');
            timerText.textContent = `${m}:${s}`;

            if (this.timerSecondsRemaining <= 120) {
                timerBox.className = 'timer-box urgent';
            } else if (this.timerSecondsRemaining <= 300) {
                timerBox.className = 'timer-box warning';
            } else {
                timerBox.className = 'timer-box';
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    renderQuestionPalette() {
        const grid = document.getElementById('palette-grid');
        const questions = this.currentExam.questions;

        grid.innerHTML = questions.map((q, idx) => {
            let stateClass = 'unanswered';
            if (idx === this.activeQuestionIndex) {
                stateClass = 'current';
            } else if (this.flaggedQuestions.has(q.id)) {
                stateClass = 'flagged';
            } else if (this.userAnswers[q.id] !== undefined && String(this.userAnswers[q.id]).trim() !== '') {
                stateClass = 'answered';
            }

            return `
                <button class="palette-btn ${stateClass}" onclick="appState.goToQuestion(${idx})">
                    ${idx + 1}
                </button>
            `;
        }).join('');

        // Progress text
        const answeredCount = Object.keys(this.userAnswers).filter(k => String(this.userAnswers[k]).trim() !== '').length;
        document.getElementById('palette-progress-text').textContent = `${answeredCount} of ${questions.length} Answered`;

        // Update Flag button text
        const currentQ = questions[this.activeQuestionIndex];
        const flagBtn = document.getElementById('btn-flag-question');
        if (currentQ && this.flaggedQuestions.has(currentQ.id)) {
            flagBtn.textContent = '🚩 Remove Flag';
        } else {
            flagBtn.textContent = '🚩 Flag for Review';
        }
    }

    renderActiveQuestion() {
        const questions = this.currentExam.questions;
        const q = questions[this.activeQuestionIndex];
        const container = document.getElementById('player-active-question-card');
        const prevBtn = document.getElementById('btn-prev-question');
        const nextBtn = document.getElementById('btn-next-question');

        prevBtn.disabled = (this.activeQuestionIndex === 0);
        nextBtn.textContent = (this.activeQuestionIndex === questions.length - 1) ? 'Review & Submit →' : 'Next →';

        const userAns = this.userAnswers[q.id];

        let inputHtml = '';
        if (q.question_type === 'mcq' || q.question_type === 'true_false') {
            const letters = ['A', 'B', 'C', 'D', 'E'];
            inputHtml = `
                <div class="player-options-list">
                    ${q.answers.map((ans, optIdx) => {
                        const isSelected = (userAns === optIdx);
                        const letter = letters[optIdx] || (optIdx + 1);
                        return `
                            <label class="player-option-label ${isSelected ? 'selected' : ''}">
                                <input type="radio" name="player-q-opt" value="${optIdx}" ${isSelected ? 'checked' : ''} onchange="appState.recordPlayerOption(${q.id}, ${optIdx})">
                                <span style="font-weight: 700; color: #4F46E5;">(${letter})</span>
                                <span>${this.escapeHtml(ans.text)}</span>
                            </label>
                        `;
                    }).join('')}
                </div>
            `;
        } else {
            inputHtml = `
                <div>
                    <label style="font-size: 0.88rem; font-weight: 600; color: #475569; display: block; margin-bottom: 8px;">
                        Type your written answer below:
                    </label>
                    <textarea class="player-textarea" rows="6" placeholder="Provide a detailed response..." oninput="appState.recordPlayerText(${q.id}, this.value)">${this.escapeHtml(userAns || '')}</textarea>
                </div>
            `;
        }

        container.innerHTML = `
            <div class="active-q-header">
                <span class="active-q-num">Question ${this.activeQuestionIndex + 1} of ${questions.length}</span>
                <span class="badge-pill pill-points">${q.points} Point${q.points !== 1 ? 's' : ''}</span>
            </div>
            <div class="active-q-text">${this.escapeHtml(q.question_text)}</div>
            ${inputHtml}
        `;

        this.renderQuestionPalette();
    }

    recordPlayerOption(qId, optIdx) {
        this.userAnswers[qId] = optIdx;
        this.renderQuestionPalette();
        // Update styling
        document.querySelectorAll('.player-option-label').forEach((lbl, idx) => {
            lbl.classList.toggle('selected', idx === optIdx);
        });
    }

    recordPlayerText(qId, text) {
        this.userAnswers[qId] = text;
        this.renderQuestionPalette();
    }

    goToQuestion(idx) {
        if (idx < 0 || idx >= this.currentExam.questions.length) return;
        this.activeQuestionIndex = idx;
        this.renderActiveQuestion();
    }

    prevQuestion() {
        if (this.activeQuestionIndex > 0) {
            this.goToQuestion(this.activeQuestionIndex - 1);
        }
    }

    nextQuestion() {
        if (this.activeQuestionIndex < this.currentExam.questions.length - 1) {
            this.goToQuestion(this.activeQuestionIndex + 1);
        } else {
            this.confirmSubmitExam();
        }
    }

    toggleFlagCurrentQuestion() {
        const q = this.currentExam.questions[this.activeQuestionIndex];
        if (!q) return;
        if (this.flaggedQuestions.has(q.id)) {
            this.flaggedQuestions.delete(q.id);
        } else {
            this.flaggedQuestions.add(q.id);
        }
        this.renderQuestionPalette();
    }

    confirmSubmitExam() {
        const total = this.currentExam.questions.length;
        const answered = Object.keys(this.userAnswers).filter(k => String(this.userAnswers[k]).trim() !== '').length;
        const unanswered = total - answered;
        const flagged = this.flaggedQuestions.size;

        let warning = `You have answered ${answered} of ${total} questions.`;
        if (unanswered > 0) {
            warning += `\n⚠️ You have ${unanswered} unanswered question(s).`;
        }
        if (flagged > 0) {
            warning += `\n🚩 You have ${flagged} question(s) flagged for review.`;
        }
        warning += '\n\nAre you sure you want to finish and submit for grading?';

        if (confirm(warning)) {
            this.submitExam();
        }
    }

    async submitExam() {
        this.stopTimer();
        const timeTaken = Math.floor((Date.now() - (this.examStartTime || Date.now())) / 1000);
        const studentName = document.getElementById('player-student-name').value.trim() || 'Student';

        this.showLoading('Grading objective answers & running AI subjective evaluation...');

        try {
            const res = await fetch(`${API_BASE}/submit-attempt`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    exam_id: this.currentExam.id,
                    student_name: studentName,
                    answers: this.userAnswers,
                    time_taken: timeTaken,
                    provider: this.settings.provider,
                    api_key: this.getActiveApiKey()
                })
            });
            const data = await res.json();
            if (data.success) {
                this.currentAttempt = data.attempt;
                this.renderResults(data, timeTaken);
                this.navigateTo('results');
                this.showToast('Exam submitted & graded!', 'success');
            } else {
                this.showToast(data.error || 'Failed to submit exam', 'error');
            }
        } catch (e) {
            this.showToast('Error submitting exam', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // -------------------------------------------------------------
    // Results & Auto-Grading Logic
    // -------------------------------------------------------------
    renderResults(data, timeTaken) {
        const score = data.score || 0;
        const pointsEarned = data.points_earned || 0;
        const totalPoints = data.total_points || this.currentExam.total_points;
        const passed = data.passed || false;
        const passingScore = this.currentExam.passing_score || 70;

        // Radial Circle
        const scoreCircle = document.getElementById('result-score-circle');
        const scorePct = document.getElementById('result-score-percentage');
        scorePct.textContent = `${Math.round(score)}%`;
        scoreCircle.style.background = `conic-gradient(${passed ? '#10B981' : '#EF4444'} ${score}%, rgba(255,255,255,0.15) ${score}%)`;

        // Badge & Headline
        const badge = document.getElementById('result-status-badge');
        const headline = document.getElementById('result-headline');
        const summaryText = document.getElementById('result-summary-text');

        if (passed) {
            badge.textContent = 'PASSED';
            badge.className = 'result-badge badge-pass';
            headline.textContent = score >= 90 ? 'Outstanding Performance! 🌟' : 'Congratulations! You Passed 👍';
            summaryText.textContent = `You exceeded the required passing threshold of ${passingScore}%.`;
        } else {
            badge.textContent = 'NEEDS IMPROVEMENT';
            badge.className = 'result-badge badge-fail';
            headline.textContent = 'Keep Practicing! 💪';
            summaryText.textContent = `You scored below the passing mark of ${passingScore}%. Review the explanations below.`;
        }

        // Stats
        document.getElementById('result-points-earned').textContent = `${pointsEarned.toFixed(1)} / ${totalPoints.toFixed(1)}`;
        document.getElementById('result-time-taken').textContent = this.formatSeconds(timeTaken);
        document.getElementById('result-passing-score').textContent = `${passingScore}%`;

        // Render Breakdown List
        const list = document.getElementById('results-breakdown-list');
        const questions = this.currentExam.questions;
        const feedback = data.feedback || {};

        list.innerHTML = questions.map((q, idx) => {
            const userAns = this.userAnswers[q.id];
            const qFeedback = feedback[String(q.id)] || feedback[q.id] || {};
            const qScore = (qFeedback.score !== undefined) ? qFeedback.score : 0;

            let cardClass = 'incorrect';
            let statusLabel = '✖ Incorrect';
            if (qScore >= q.points) {
                cardClass = 'correct';
                statusLabel = '✔ Correct';
            } else if (qScore > 0) {
                cardClass = 'partial';
                statusLabel = '⚡ Partial Credit';
            }

            let answerReviewHtml = '';
            if (q.question_type === 'mcq' || q.question_type === 'true_false') {
                const letters = ['A', 'B', 'C', 'D', 'E'];
                answerReviewHtml = q.answers.map((ans, optIdx) => {
                    const isSelected = (userAns === optIdx);
                    const isCorrect = ans.is_correct;
                    const letter = letters[optIdx] || (optIdx + 1);

                    let optClass = 'review-opt';
                    let suffix = '';
                    if (isCorrect) {
                        optClass += ' is-correct-ans';
                        suffix = ' <strong style="color: #059669;">[CORRECT ANSWER]</strong>';
                    } else if (isSelected && !isCorrect) {
                        optClass += ' is-user-wrong';
                        suffix = ' <span style="color: #DC2626;">[YOUR CHOICE]</span>';
                    }

                    return `<div class="${optClass}">(${letter}) ${this.escapeHtml(ans.text)} ${suffix}</div>`;
                }).join('');
            } else {
                answerReviewHtml = `
                    <div style="margin: 8px 0; font-size: 0.92rem;">
                        <strong>Your Submitted Response:</strong>
                        <div style="background: #F8FAFC; padding: 10px; border-radius: 6px; margin-top: 4px; border: 1px solid #E2E8F0;">
                            ${userAns ? this.escapeHtml(userAns) : '<em>No answer submitted</em>'}
                        </div>
                    </div>
                    <div style="margin: 8px 0; font-size: 0.92rem;">
                        <strong>Expected Model Answer / Rubric:</strong>
                        <div style="background: #ECFDF5; padding: 10px; border-radius: 6px; margin-top: 4px; border: 1px solid #A7F3D0; color: #065F46;">
                            ${this.escapeHtml(q.correct_answer || q.rubric || 'Detailed in explanation')}
                        </div>
                    </div>
                `;
            }

            return `
                <div class="result-review-card ${cardClass}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 800; font-size: 0.95rem;">Question ${idx + 1} (${q.question_type.toUpperCase()})</span>
                        <span style="font-weight: 700; font-size: 0.85rem;">Score: ${qScore.toFixed(1)} / ${q.points} pts</span>
                    </div>
                    <div style="font-size: 1.05rem; font-weight: 600; margin-bottom: 12px; color: #0F172A;">
                        ${this.escapeHtml(q.question_text)}
                    </div>

                    ${answerReviewHtml}

                    ${qFeedback.feedback ? `<div class="feedback-bubble">💡 <strong>AI Evaluation:</strong> ${this.escapeHtml(qFeedback.feedback)}</div>` : ''}

                    <div style="margin-top: 10px; font-size: 0.85rem; color: #475569; background: #F8FAFC; padding: 8px 12px; border-radius: 6px;">
                        📖 <strong>Explanation:</strong> ${this.escapeHtml(q.justification || 'Refer to course syllabus.')}
                        ${q.source_page ? `<span style="margin-left: 14px; color: #64748B;">Source: Page ${q.source_page}</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    retakeExam() {
        this.startExamWithCurrent();
    }

    // -------------------------------------------------------------
    // Export Hub Logic
    // -------------------------------------------------------------
    loadExportHub() {
        const titleEl = document.getElementById('export-exam-title');
        if (this.currentExam) {
            titleEl.textContent = `Exporting: ${this.currentExam.title} (${this.currentExam.num_questions} Questions • ${this.currentExam.total_points || this.currentExam.num_questions} pts)`;
        } else {
            titleEl.textContent = 'Select an exam from the dashboard to download export packages.';
        }
    }

    triggerExport(format, type = 'student') {
        if (!this.currentExam) {
            alert('Please select or generate an exam first.');
            return;
        }

        const url = `${API_BASE}/export/${this.currentExam.id}/${format}?type=${type}`;
        if (format === 'html') {
            window.open(url, '_blank');
        } else {
            // Download file
            window.location.href = url;
        }
    }

    // -------------------------------------------------------------
    // UI Helpers & Utilities
    // -------------------------------------------------------------
    showLoading(message = 'Processing...') {
        document.getElementById('loading-message').textContent = message;
        document.getElementById('loading-overlay').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3200);
    }

    formatSeconds(sec) {
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        return `${m}:${s.toString().padStart(2, '0')}`;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Global initialization
let appState = null;
document.addEventListener('DOMContentLoaded', () => {
    appState = new AppState();
    window.appState = appState;
});
