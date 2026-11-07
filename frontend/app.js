/**
 * StudyWise AI - Academic Exam Generator & Assessment Platform
 * High-Performance Single Page Application (SPA)
 * Modeled after Stitch Academic Precision System
 * Zero Emojis - Vector Lucide Icons
 */

const API_BASE = 'http://127.0.0.1:5000/api';

class AppState {
    constructor() {
        this.currentView = 'dashboard';
        this.currentPdf = null;
        this.currentExam = null;
        this.currentAttempt = null;
        this.allExams = [];
        this.sourceTab = 'pdf';

        // Question distribution counts
        this.questionCounts = {
            mcq: 5,
            tf: 2,
            short: 2,
            essay: 1
        };

        // Exam Player State
        this.activeQuestionIndex = 0;
        this.userAnswers = {};
        this.flaggedQuestions = new Set();
        this.timerInterval = null;
        this.timerSecondsRemaining = 0;
        this.totalExamSeconds = 0;
        this.examStartTime = null;

        // Editor active filter
        this.editorActiveFilter = 'all';

        // Active regeneration target
        this.regeneratingQuestionId = null;

        // Settings
        this.settings = this.loadSettings();

        this.init();
    }

    init() {
        this.bindEvents();
        this.updateProviderBadge();
        this.loadDashboardData();
        this.navigateTo('dashboard');
    }

    renderIcons() {
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    // -------------------------------------------------------------
    // Event Listeners & Binding
    // -------------------------------------------------------------
    bindEvents() {
        // Navigation clicks
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const view = btn.dataset.view;
                if (view) this.navigateTo(view);
            });
        });

        // Dropzone drag-and-drop
        const dropzone = document.getElementById('pdf-dropzone');
        if (dropzone) {
            dropzone.addEventListener('click', () => {
                document.getElementById('pdf-file-input').click();
            });

            ['dragenter', 'dragover'].forEach(event => {
                dropzone.addEventListener(event, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropzone.classList.add('border-indigo-500', 'bg-indigo-50/40');
                });
            });

            ['dragleave', 'drop'].forEach(event => {
                dropzone.addEventListener(event, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropzone.classList.remove('border-indigo-500', 'bg-indigo-50/40');
                });
            });

            dropzone.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files && files.length > 0) {
                    this.uploadFile(files[0]);
                }
            });
        }
    }

    // -------------------------------------------------------------
    // Navigation & View Routing
    // -------------------------------------------------------------
    navigateTo(viewName) {
        // Stop timer if moving away from exam player
        if (this.currentView === 'player' && viewName !== 'player') {
            this.stopTimer();
        }

        this.currentView = viewName;

        // Hide all views
        document.querySelectorAll('.app-view').forEach(view => {
            view.classList.add('hidden');
        });

        // Show target view
        const targetView = document.getElementById(`view-${viewName}`);
        if (targetView) {
            targetView.classList.remove('hidden');
        }

        // Update nav button states
        document.querySelectorAll('.nav-btn').forEach(btn => {
            if (btn.dataset.view === viewName) {
                btn.className = 'nav-btn flex items-center gap-1.5 font-semibold bg-white text-indigo-600 rounded-full px-4 py-1.5 text-xs tracking-wide shadow-xs transition-all';
            } else {
                btn.className = 'nav-btn flex items-center gap-1.5 font-medium text-slate-600 rounded-full px-4 py-1.5 text-xs tracking-wide hover:text-slate-900 hover:bg-slate-200/60 transition-all';
            }
        });

        // View-specific initializers
        if (viewName === 'dashboard') {
            this.loadDashboardData();
        } else if (viewName === 'editor') {
            this.renderQuestions();
        } else if (viewName === 'player') {
            this.initPlayer();
        } else if (viewName === 'export') {
            this.updateExportView();
        }

        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => this.renderIcons(), 50);
    }

    // -------------------------------------------------------------
    // Dashboard Data & Analytics
    // -------------------------------------------------------------
    async loadDashboardData() {
        try {
            // Load analytics summary
            const statsRes = await fetch(`${API_BASE}/analytics/summary`);
            if (statsRes.ok) {
                const stats = await statsRes.json();
                document.getElementById('stat-total-exams').textContent = stats.total_exams || 0;
                document.getElementById('stat-total-questions').textContent = stats.total_questions || 0;
                document.getElementById('stat-total-attempts').textContent = stats.total_attempts || 0;
                document.getElementById('stat-avg-score').textContent = `${Math.round(stats.average_score || 0)}%`;
            }

            // Load exams list
            const examsRes = await fetch(`${API_BASE}/exams`);
            if (examsRes.ok) {
                const resData = await examsRes.json();
                this.allExams = Array.isArray(resData) ? resData : (resData.exams || []);
                this.renderDashboardExams(this.allExams);
            }
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }

    renderDashboardExams(exams) {
        const tbody = document.getElementById('dashboard-exams-tbody');
        const emptyState = document.getElementById('exams-empty-state');
        const countBadge = document.getElementById('exam-count-badge');

        if (!tbody) return;

        countBadge.textContent = `${exams.length} assessment${exams.length === 1 ? '' : 's'}`;

        if (exams.length === 0) {
            tbody.innerHTML = '';
            emptyState.classList.remove('hidden');
            return;
        }

        emptyState.classList.add('hidden');

        tbody.innerHTML = exams.map(exam => {
            let diffBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 uppercase">MEDIUM</span>';
            if (exam.difficulty === 'easy') {
                diffBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 uppercase">EASY</span>';
            } else if (exam.difficulty === 'hard') {
                diffBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200 uppercase">HARD</span>';
            }

            const timeLimitStr = exam.time_limit > 0 ? `${exam.time_limit} mins` : 'Untimed';
            const createdStr = exam.created_date ? new Date(exam.created_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recent';

            return `
                <tr class="hover:bg-slate-50/80 transition-colors group">
                    <td class="py-3.5 px-4">
                        <div class="flex items-center gap-3">
                            <div class="w-1.5 h-8 rounded-full bg-indigo-600"></div>
                            <div>
                                <div class="text-xs font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                                    ${this.escapeHtml(exam.title)}
                                </div>
                                <div class="text-[11px] text-slate-500 truncate max-w-xs">
                                    ${this.escapeHtml(exam.description || exam.source_ref || 'Academic Examination')}
                                </div>
                            </div>
                        </div>
                    </td>
                    <td class="py-3.5 px-4">${diffBadge}</td>
                    <td class="py-3.5 px-4 font-semibold text-slate-800">
                        ${exam.num_questions || 0} Questions
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                        <div class="flex items-center gap-1.5">
                            <i data-lucide="clock" class="w-3.5 h-3.5 text-slate-400"></i>
                            <span>${timeLimitStr}</span>
                        </div>
                    </td>
                    <td class="py-3.5 px-4 text-slate-500">${createdStr}</td>
                    <td class="py-3.5 px-4 text-right">
                        <div class="inline-flex items-center gap-1">
                            <button onclick="appState.loadExamAndPlay(${exam.id})" class="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-600 hover:text-white text-indigo-700 rounded-lg text-xs font-semibold transition-all">
                                Take
                            </button>
                            <button onclick="appState.loadExamAndEdit(${exam.id})" class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-all">
                                Edit
                            </button>
                            <button onclick="appState.loadExamAndExport(${exam.id})" class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-all">
                                Export
                            </button>
                            <button onclick="appState.deleteExam(${exam.id})" class="p-1 hover:bg-rose-50 text-slate-400 hover:text-rose-600 rounded-lg transition-all" title="Delete Exam">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        this.renderIcons();
    }

    filterExams(query) {
        if (!query || !query.trim()) {
            this.renderDashboardExams(this.allExams);
            return;
        }
        const q = query.toLowerCase();
        const filtered = this.allExams.filter(exam => 
            (exam.title && exam.title.toLowerCase().includes(q)) ||
            (exam.description && exam.description.toLowerCase().includes(q)) ||
            (exam.source_ref && exam.source_ref.toLowerCase().includes(q))
        );
        this.renderDashboardExams(filtered);
    }

    async deleteExam(examId) {
        if (!confirm('Are you sure you want to delete this examination? This cannot be undone.')) return;

        try {
            const res = await fetch(`${API_BASE}/exams/${examId}`, { method: 'DELETE' });
            if (res.ok) {
                this.showToast('Exam deleted successfully', 'success');
                this.loadDashboardData();
            } else {
                this.showToast('Failed to delete exam', 'error');
            }
        } catch (e) {
            this.showToast('Network error while deleting exam', 'error');
        }
    }

    // -------------------------------------------------------------
    // Quick-Start & Wizard Source Selection
    // -------------------------------------------------------------
    startFromSource(sourceType) {
        this.navigateTo('wizard');
        this.switchWizardTab(sourceType);
    }

    switchWizardTab(tab) {
        this.sourceTab = tab;

        const tabs = ['pdf', 'topic', 'text'];
        tabs.forEach(t => {
            const btn = document.getElementById(`tab-btn-${t}`);
            const panel = document.getElementById(`panel-source-${t}`);

            if (t === tab) {
                btn.className = 'wizard-tab py-2 px-3 rounded-lg bg-white text-indigo-600 font-semibold shadow-xs text-xs flex items-center justify-center gap-1.5 transition-all';
                panel.classList.remove('hidden');
            } else {
                btn.className = 'wizard-tab py-2 px-3 rounded-lg text-slate-600 hover:text-slate-900 font-medium text-xs flex items-center justify-center gap-1.5 transition-all';
                panel.classList.add('hidden');
            }
        });

        this.renderIcons();
    }

    // -------------------------------------------------------------
    // PDF Upload & Document Ingestion
    // -------------------------------------------------------------
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) this.uploadFile(file);
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        this.showToast('Extracting text and structure with OCR...', 'info');

        try {
            const res = await fetch(`${API_BASE}/upload`, {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                this.currentPdf = data;

                // Update UI elements
                document.getElementById('pdf-dropzone').classList.add('hidden');
                const card = document.getElementById('pdf-uploaded-card');
                card.classList.remove('hidden');

                document.getElementById('pdf-filename-display').textContent = data.filename;
                document.getElementById('pdf-filesize-display').textContent = `${(file.size / (1024 * 1024)).toFixed(1)} MB • Processed with OCR`;
                document.getElementById('pdf-pages-display').textContent = data.num_pages || 1;
                document.getElementById('pdf-words-display').textContent = data.word_count || 0;
                document.getElementById('pdf-excerpt-display').textContent = data.excerpt || 'Excerpt synthesized from pages.';

                // Auto-fill exam title if blank
                const titleInput = document.getElementById('exam-title-input');
                if (!titleInput.value.trim()) {
                    const cleanName = data.filename.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
                    titleInput.value = `Assessment: ${cleanName.charAt(0).toUpperCase() + cleanName.slice(1)}`;
                }

                this.showToast('Document ingested successfully!', 'success');
                this.renderIcons();
            } else {
                const err = await res.json();
                this.showToast(`Upload failed: ${err.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            this.showToast('Network error uploading file', 'error');
        }
    }

    removeSelectedFile() {
        this.currentPdf = null;
        document.getElementById('pdf-uploaded-card').classList.add('hidden');
        document.getElementById('pdf-dropzone').classList.remove('hidden');
        document.getElementById('pdf-file-input').value = '';
    }

    updatePastedWordCount(text) {
        const words = text.trim() ? text.trim().split(/\s+/).length : 0;
        document.getElementById('pasted-word-count').textContent = `${words} words`;
    }

    // -------------------------------------------------------------
    // Question Distribution Steppers
    // -------------------------------------------------------------
    adjustQuestionCount(type, delta) {
        const current = this.questionCounts[type] || 0;
        const next = Math.max(0, Math.min(30, current + delta));
        this.questionCounts[type] = next;

        const countEl = document.getElementById(`count-${type}`);
        if (countEl) countEl.textContent = next;

        const total = Object.values(this.questionCounts).reduce((a, b) => a + b, 0);
        document.getElementById('wizard-total-questions-badge').textContent = `Total: ${total} Items`;
    }

    // -------------------------------------------------------------
    // Exam Generation Flow
    // -------------------------------------------------------------
    async generateExam() {
        const title = document.getElementById('exam-title-input').value.trim() || 'Comprehensive Academic Assessment';
        const difficulty = document.getElementById('exam-difficulty-select').value;
        const targetAudience = document.getElementById('exam-target-audience').value;
        const timeLimit = parseInt(document.getElementById('exam-time-limit').value, 10) || 0;
        const passingScore = parseInt(document.getElementById('exam-passing-score').value, 10) || 75;

        const totalQuestions = Object.values(this.questionCounts).reduce((a, b) => a + b, 0);
        if (totalQuestions === 0) {
            this.showToast('Please specify at least 1 question item', 'error');
            return;
        }

        const payload = {
            title,
            difficulty,
            target_audience: targetAudience,
            time_limit: timeLimit,
            passing_score: passingScore,
            question_counts: {
                mcq: this.questionCounts.mcq,
                true_false: this.questionCounts.tf,
                short_answer: this.questionCounts.short,
                essay: this.questionCounts.essay
            },
            provider: this.settings.provider,
            api_key: this.getActiveApiKey()
        };

        if (this.sourceTab === 'pdf') {
            if (!this.currentPdf || !this.currentPdf.pdf_id) {
                this.showToast('Please upload a PDF document first', 'error');
                return;
            }
            payload.source_type = 'pdf';
            payload.pdf_id = this.currentPdf.pdf_id;
        } else if (this.sourceTab === 'topic') {
            const subject = document.getElementById('topic-subject-input').value.trim();
            const objectives = document.getElementById('topic-objectives-input').value.trim();
            if (!subject) {
                this.showToast('Please enter a subject topic', 'error');
                return;
            }
            payload.source_type = 'topic';
            payload.topic = subject;
            payload.prompt = objectives ? `Focus areas & objectives: ${objectives}` : '';
        } else if (this.sourceTab === 'text') {
            const rawText = document.getElementById('pasted-text-input').value.trim();
            if (!rawText) {
                this.showToast('Please paste lecture notes or text content', 'error');
                return;
            }
            payload.source_type = 'text';
            payload.text = rawText;
        }

        // Show Progress Bar
        const btn = document.getElementById('btn-generate-exam');
        const progressBox = document.getElementById('generation-progress-box');
        const progressBar = document.getElementById('generation-progress-bar');
        const stageText = document.getElementById('generation-stage-text');
        const pctText = document.getElementById('generation-pct-text');

        btn.disabled = true;
        btn.classList.add('opacity-60', 'cursor-not-allowed');
        progressBox.classList.remove('hidden');

        // Animated progress stages
        let stageIdx = 0;
        const stages = [
            { pct: 20, text: 'Extracting corpus structure & cognitive concepts...' },
            { pct: 45, text: 'Synthesizing question stems & distractor options...' },
            { pct: 75, text: 'Generating scoring rubrics & pedagogical rationales...' },
            { pct: 95, text: 'Finalizing assessment blueprint...' }
        ];

        const progressInterval = setInterval(() => {
            if (stageIdx < stages.length) {
                progressBar.style.width = `${stages[stageIdx].pct}%`;
                pctText.textContent = `${stages[stageIdx].pct}%`;
                stageText.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin text-indigo-600 inline-block mr-1"></i> ${stages[stageIdx].text}`;
                this.renderIcons();
                stageIdx++;
            }
        }, 1800);

        try {
            const res = await fetch(`${API_BASE}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            clearInterval(progressInterval);

            if (res.ok) {
                const exam = await res.json();
                this.currentExam = exam;

                progressBar.style.width = '100%';
                pctText.textContent = '100%';
                stageText.innerHTML = '<span class="text-emerald-600 font-bold">Exam generation complete!</span>';

                setTimeout(() => {
                    btn.disabled = false;
                    btn.classList.remove('opacity-60', 'cursor-not-allowed');
                    progressBox.classList.add('hidden');
                    this.showToast('Assessment generated successfully!', 'success');
                    this.navigateTo('editor');
                }, 800);
            } else {
                const err = await res.json();
                clearInterval(progressInterval);
                btn.disabled = false;
                btn.classList.remove('opacity-60', 'cursor-not-allowed');
                progressBox.classList.add('hidden');
                this.showToast(`Generation failed: ${err.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            clearInterval(progressInterval);
            btn.disabled = false;
            btn.classList.remove('opacity-60', 'cursor-not-allowed');
            progressBox.classList.add('hidden');
            this.showToast('Network error during AI exam generation', 'error');
        }
    }

    // -------------------------------------------------------------
    // Question Bank & Live Editor Studio
    // -------------------------------------------------------------
    async loadExamAndEdit(examId) {
        try {
            const res = await fetch(`${API_BASE}/exams/${examId}`);
            if (res.ok) {
                this.currentExam = await res.json();
                this.navigateTo('editor');
            }
        } catch (e) {
            this.showToast('Error loading exam details', 'error');
        }
    }

    renderQuestions() {
        if (!this.currentExam) return;

        const titleEl = document.getElementById('editor-exam-title');
        const metaBadge = document.getElementById('editor-exam-meta-badge');
        const ptsBadge = document.getElementById('editor-points-badge');
        const list = document.getElementById('editor-questions-list');

        titleEl.textContent = this.currentExam.title;
        metaBadge.textContent = `${this.currentExam.questions.length} Items`;
        ptsBadge.textContent = `${(this.currentExam.total_points || 0).toFixed(1)} Total Points`;

        // Update specs
        document.getElementById('editor-spec-diff').textContent = this.currentExam.difficulty || 'Medium';
        document.getElementById('editor-spec-time').textContent = this.currentExam.time_limit > 0 ? `${this.currentExam.time_limit} mins` : 'Untimed';
        document.getElementById('editor-spec-pass').textContent = `${this.currentExam.passing_score || 75}%`;

        // Update counts
        const questions = this.currentExam.questions;
        document.getElementById('filter-count-all').textContent = questions.length;
        document.getElementById('filter-count-mcq').textContent = questions.filter(q => q.question_type === 'mcq').length;
        document.getElementById('filter-count-tf').textContent = questions.filter(q => q.question_type === 'true_false').length;
        document.getElementById('filter-count-short').textContent = questions.filter(q => q.question_type === 'short_answer').length;
        document.getElementById('filter-count-essay').textContent = questions.filter(q => q.question_type === 'essay').length;

        // Filter questions
        const filtered = this.editorActiveFilter === 'all'
            ? questions
            : questions.filter(q => q.question_type === this.editorActiveFilter);

        if (filtered.length === 0) {
            list.innerHTML = `
                <div class="bg-white border border-slate-200 rounded-2xl p-8 text-center">
                    <p class="text-xs text-slate-500">No questions match the selected filter.</p>
                </div>
            `;
            return;
        }

        const letters = ['A', 'B', 'C', 'D', 'E', 'F'];

        list.innerHTML = filtered.map((q, idx) => {
            let optionsHtml = '';

            if (q.question_type === 'mcq' || q.question_type === 'true_false') {
                optionsHtml = `
                    <div class="space-y-1.5 pt-2">
                        ${q.answers.map((ans, optIdx) => {
                            const isCorr = ans.is_correct;
                            const letter = letters[optIdx] || (optIdx + 1);
                            return `
                                <div class="flex items-center gap-2.5 p-2 rounded-lg text-xs border ${isCorr ? 'border-emerald-200 bg-emerald-50/70 text-emerald-950 font-medium' : 'border-slate-200/80 bg-slate-50/50 text-slate-700'}">
                                    <span class="w-5 h-5 rounded-full flex items-center justify-center font-bold text-[10px] ${isCorr ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'}">
                                        ${letter}
                                    </span>
                                    <span class="flex-1">${this.escapeHtml(ans.text)}</span>
                                    ${isCorr ? '<span class="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">CORRECT</span>' : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            } else {
                optionsHtml = `
                    <div class="bg-indigo-50/40 border border-indigo-100 rounded-xl p-3 text-xs space-y-1 mt-2">
                        <span class="font-bold text-indigo-900 block text-[11px] uppercase tracking-wider">Evaluation Rubric & Model Solution:</span>
                        <p class="text-indigo-950 italic">${this.escapeHtml(q.correct_answer || q.rubric || 'Detailed answer evaluation criteria.')}</p>
                    </div>
                `;
            }

            return `
                <div class="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs space-y-3 relative group">
                    <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
                        <div class="flex items-center gap-2">
                            <span class="font-bold text-xs text-indigo-700 bg-indigo-50 border border-indigo-200/60 px-2.5 py-0.5 rounded-full uppercase">
                                Q${idx + 1} • ${q.question_type.replace('_', ' ')}
                            </span>
                            <span class="text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
                                ${q.points} pt${q.points === 1 ? '' : 's'}
                            </span>
                            ${q.source_page ? `<span class="text-[11px] text-slate-500">Page ${q.source_page}</span>` : ''}
                        </div>
                        <div class="flex items-center gap-1.5">
                            <button onclick="appState.openRegenerateModal(${q.id})" class="px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold text-xs flex items-center gap-1 transition-all">
                                <i data-lucide="wand-2" class="w-3 h-3"></i>
                                <span>AI Regenerate</span>
                            </button>
                            <button onclick="appState.deleteQuestion(${q.id})" class="p-1 rounded-lg hover:bg-rose-50 text-slate-400 hover:text-rose-600 transition-all" title="Delete Question">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Editable Question Stem -->
                    <div class="text-sm font-semibold text-slate-900 leading-snug">
                        ${this.escapeHtml(q.question_text)}
                    </div>

                    <!-- Answers / Rubric -->
                    ${optionsHtml}

                    <!-- Pedagogical Rationale Callout -->
                    ${q.justification ? `
                        <div class="bg-slate-50 border border-slate-200/70 rounded-xl p-3 text-xs text-slate-600 leading-relaxed flex items-start gap-2">
                            <i data-lucide="info" class="w-3.5 h-3.5 text-indigo-600 flex-shrink-0 mt-0.5"></i>
                            <div>
                                <strong class="text-slate-800">Pedagogical Rationale:</strong>
                                <span>${this.escapeHtml(q.justification)}</span>
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

        this.renderIcons();
    }

    filterEditorByType(type) {
        this.editorActiveFilter = type;
        document.querySelectorAll('.editor-type-filter').forEach(btn => {
            btn.className = 'editor-type-filter w-full text-left px-3 py-1.5 rounded-lg text-slate-600 hover:bg-slate-50 flex items-center justify-between text-xs';
        });
        this.renderQuestions();
    }

    async deleteQuestion(qId) {
        if (!confirm('Delete this question item?')) return;
        try {
            const res = await fetch(`${API_BASE}/questions/${qId}`, { method: 'DELETE' });
            if (res.ok) {
                this.currentExam.questions = this.currentExam.questions.filter(q => q.id !== qId);
                this.renderQuestions();
                this.showToast('Question deleted', 'success');
            }
        } catch (e) {
            this.showToast('Error deleting question', 'error');
        }
    }

    // -------------------------------------------------------------
    // Single-Question AI Regeneration
    // -------------------------------------------------------------
    openRegenerateModal(questionId) {
        this.regeneratingQuestionId = questionId;
        const q = this.currentExam.questions.find(item => item.id === questionId);
        if (q) {
            document.getElementById('regen-original-text').textContent = q.question_text;
        }
        document.getElementById('regen-instruction-input').value = '';
        document.getElementById('modal-regenerate').classList.remove('hidden');
        this.renderIcons();
    }

    closeRegenerateModal() {
        document.getElementById('modal-regenerate').classList.add('hidden');
        this.regeneratingQuestionId = null;
    }

    async confirmRegenerateQuestion() {
        if (!this.regeneratingQuestionId) return;

        const instruction = document.getElementById('regen-instruction-input').value.trim();
        const btn = document.getElementById('btn-confirm-regen');
        btn.disabled = true;
        btn.classList.add('opacity-60');

        try {
            const res = await fetch(`${API_BASE}/questions/${this.regeneratingQuestionId}/regenerate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    instruction,
                    provider: this.settings.provider,
                    api_key: this.getActiveApiKey()
                })
            });

            if (res.ok) {
                const updated = await res.json();
                const idx = this.currentExam.questions.findIndex(q => q.id === this.regeneratingQuestionId);
                if (idx !== -1) {
                    this.currentExam.questions[idx] = updated;
                }
                this.closeRegenerateModal();
                this.renderQuestions();
                this.showToast('Question regenerated with AI!', 'success');
            } else {
                this.showToast('Regeneration failed', 'error');
            }
        } catch (e) {
            this.showToast('Network error during question regeneration', 'error');
        } finally {
            btn.disabled = false;
            btn.classList.remove('opacity-60');
        }
    }

    // -------------------------------------------------------------
    // Add Custom Question Modal
    // -------------------------------------------------------------
    openAddQuestionModal() {
        document.getElementById('modal-add-question').classList.remove('hidden');
        this.renderIcons();
    }

    closeAddQuestionModal() {
        document.getElementById('modal-add-question').classList.add('hidden');
    }

    handleNewQuestionTypeChange(type) {
        const mcqBox = document.getElementById('new-q-mcq-box');
        if (type === 'mcq') {
            mcqBox.classList.remove('hidden');
        } else {
            mcqBox.classList.add('hidden');
        }
    }

    async confirmAddQuestion() {
        if (!this.currentExam) return;

        const qType = document.getElementById('new-q-type').value;
        const qPoints = parseFloat(document.getElementById('new-q-points').value) || 1.0;
        const qText = document.getElementById('new-q-text').value.trim();
        const qExplanation = document.getElementById('new-q-explanation').value.trim();

        if (!qText) {
            this.showToast('Please enter the question prompt', 'error');
            return;
        }

        const payload = {
            question_type: qType,
            points: qPoints,
            question_text: qText,
            justification: qExplanation,
            answers: []
        };

        if (qType === 'mcq') {
            const correctOptIdx = parseInt(document.querySelector('input[name="new-q-correct"]:checked').value, 10);
            for (let i = 0; i < 4; i++) {
                const optText = document.getElementById(`new-opt-${i}`).value.trim() || `Option ${String.fromCharCode(65 + i)}`;
                payload.answers.push({
                    text: optText,
                    is_correct: (i === correctOptIdx)
                });
            }
        } else if (qType === 'true_false') {
            payload.answers = [
                { text: 'True', is_correct: true },
                { text: 'False', is_correct: false }
            ];
        }

        try {
            const res = await fetch(`${API_BASE}/exams/${this.currentExam.id}/questions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const newQ = await res.json();
                this.currentExam.questions.push(newQ);
                this.closeAddQuestionModal();
                this.renderQuestions();
                this.showToast('Question added successfully', 'success');
            } else {
                this.showToast('Failed to add question', 'error');
            }
        } catch (e) {
            this.showToast('Network error adding question', 'error');
        }
    }

    // -------------------------------------------------------------
    // Online Exam Player Logic
    // -------------------------------------------------------------
    async loadExamAndPlay(examId) {
        try {
            const res = await fetch(`${API_BASE}/exams/${examId}`);
            if (res.ok) {
                this.currentExam = await res.json();
                this.navigateTo('player');
            }
        } catch (e) {
            this.showToast('Error loading exam player', 'error');
        }
    }

    startOnlineExam() {
        if (!this.currentExam || this.currentExam.questions.length === 0) {
            this.showToast('Exam has no questions', 'error');
            return;
        }
        this.navigateTo('player');
    }

    initPlayer() {
        if (!this.currentExam || !this.currentExam.questions) return;

        this.activeQuestionIndex = 0;
        this.userAnswers = {};
        this.flaggedQuestions.clear();
        this.examStartTime = new Date();

        document.getElementById('player-exam-title').textContent = this.currentExam.title;

        // Timer setup
        this.stopTimer();
        const timeLimitMins = this.currentExam.time_limit || 0;
        if (timeLimitMins > 0) {
            this.timerSecondsRemaining = timeLimitMins * 60;
            this.totalExamSeconds = this.timerSecondsRemaining;
            this.startTimer();
        } else {
            document.getElementById('player-timer-text').textContent = 'Untimed';
            document.getElementById('player-timer-box').className = 'flex items-center gap-2 bg-slate-100 border border-slate-200 px-3.5 py-1.5 rounded-xl text-slate-800 font-mono text-sm font-bold shadow-inner';
        }

        this.renderPlayerQuestion();
        this.renderPlayerPalette();
    }

    startTimer() {
        this.updateTimerDisplay();
        this.timerInterval = setInterval(() => {
            this.timerSecondsRemaining--;
            this.updateTimerDisplay();

            if (this.timerSecondsRemaining <= 0) {
                this.stopTimer();
                this.showToast('Time limit reached! Submitting examination automatically.', 'info');
                this.executeSubmitExam();
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    updateTimerDisplay() {
        const timerBox = document.getElementById('player-timer-box');
        const timerText = document.getElementById('player-timer-text');
        if (!timerBox || !timerText) return;

        const m = Math.floor(this.timerSecondsRemaining / 60);
        const s = this.timerSecondsRemaining % 60;
        timerText.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;

        if (this.timerSecondsRemaining < 120) {
            timerBox.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-xl font-mono text-sm font-bold shadow-inner timer-critical';
        } else if (this.timerSecondsRemaining < 300) {
            timerBox.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-xl font-mono text-sm font-bold shadow-inner timer-warning';
        } else {
            timerBox.className = 'flex items-center gap-2 bg-slate-100 border border-slate-200 px-3.5 py-1.5 rounded-xl text-slate-800 font-mono text-sm font-bold shadow-inner';
        }
    }

    renderPlayerQuestion() {
        const questions = this.currentExam.questions;
        const q = questions[this.activeQuestionIndex];
        if (!q) return;

        // Progress Text
        const pct = Math.round(((this.activeQuestionIndex + 1) / questions.length) * 100);
        document.getElementById('player-progress-text').textContent = `Question ${this.activeQuestionIndex + 1} of ${questions.length} • ${pct}% Complete`;

        // Badges
        document.getElementById('player-q-type-badge').textContent = q.question_type.replace('_', ' ').toUpperCase();
        document.getElementById('player-q-pts-badge').textContent = `${q.points} pt${q.points === 1 ? '' : 's'}`;
        document.getElementById('player-q-index-badge').textContent = `Question ${this.activeQuestionIndex + 1}`;
        document.getElementById('player-question-text').textContent = q.question_text;

        // Render Options
        const container = document.getElementById('player-options-container');
        const letters = ['A', 'B', 'C', 'D', 'E', 'F'];
        const savedAnswer = this.userAnswers[q.id];

        if (q.question_type === 'mcq' || q.question_type === 'true_false') {
            container.innerHTML = q.answers.map((ans, optIdx) => {
                const isSelected = (savedAnswer === optIdx);
                const letter = letters[optIdx] || (optIdx + 1);

                return `
                    <div onclick="appState.playerSelectOption(${q.id}, ${optIdx})" class="player-opt-card ${isSelected ? 'selected' : ''}">
                        <div class="player-opt-indicator">
                            <span class="player-opt-indicator-dot"></span>
                        </div>
                        <span class="font-bold text-xs text-slate-700">(${letter})</span>
                        <span class="text-xs text-slate-800 flex-1 leading-relaxed">${this.escapeHtml(ans.text)}</span>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = `
                <div class="space-y-2">
                    <label class="block text-xs font-semibold text-slate-700">Your Technical Response:</label>
                    <textarea oninput="appState.playerSaveTextAnswer(${q.id}, this.value)" rows="6" class="w-full p-3 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" placeholder="Type your full answer here...">${savedAnswer ? this.escapeHtml(savedAnswer) : ''}</textarea>
                </div>
            `;
        }

        // Prev / Next button state
        document.getElementById('btn-player-prev').disabled = (this.activeQuestionIndex === 0);
        document.getElementById('btn-player-prev').classList.toggle('opacity-50', this.activeQuestionIndex === 0);

        const isLast = (this.activeQuestionIndex === questions.length - 1);
        document.getElementById('btn-player-next').innerHTML = isLast 
            ? '<span>Finish Review</span> <i data-lucide="check" class="w-3.5 h-3.5"></i>' 
            : '<span>Next Question</span> <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>';

        // Flag button
        const isFlagged = this.flaggedQuestions.has(q.id);
        const flagLabel = document.getElementById('player-flag-label');
        flagLabel.textContent = isFlagged ? 'Flagged for Review' : 'Flag for Review';
        document.getElementById('btn-player-flag').classList.toggle('bg-amber-100', isFlagged);

        this.renderIcons();
    }

    playerSelectOption(questionId, optionIndex) {
        this.userAnswers[questionId] = optionIndex;
        this.renderPlayerQuestion();
        this.renderPlayerPalette();
    }

    playerSaveTextAnswer(questionId, text) {
        if (text.trim()) {
            this.userAnswers[questionId] = text.trim();
        } else {
            delete this.userAnswers[questionId];
        }
        this.renderPlayerPalette();
    }

    playerPrevQuestion() {
        if (this.activeQuestionIndex > 0) {
            this.activeQuestionIndex--;
            this.renderPlayerQuestion();
            this.renderPlayerPalette();
        }
    }

    playerNextQuestion() {
        const questions = this.currentExam.questions;
        if (this.activeQuestionIndex < questions.length - 1) {
            this.activeQuestionIndex++;
            this.renderPlayerQuestion();
            this.renderPlayerPalette();
        } else {
            this.confirmSubmitExam();
        }
    }

    playerToggleFlag() {
        const q = this.currentExam.questions[this.activeQuestionIndex];
        if (!q) return;

        if (this.flaggedQuestions.has(q.id)) {
            this.flaggedQuestions.delete(q.id);
        } else {
            this.flaggedQuestions.add(q.id);
        }

        this.renderPlayerQuestion();
        this.renderPlayerPalette();
    }

    playerJumpTo(idx) {
        this.activeQuestionIndex = idx;
        this.renderPlayerQuestion();
        this.renderPlayerPalette();
    }

    renderPlayerPalette() {
        const grid = document.getElementById('player-palette-grid');
        const summary = document.getElementById('player-palette-summary');
        if (!grid) return;

        const questions = this.currentExam.questions;
        const answeredCount = Object.keys(this.userAnswers).length;
        summary.textContent = `${answeredCount}/${questions.length} Answered`;

        grid.innerHTML = questions.map((q, idx) => {
            const isAnswered = (this.userAnswers[q.id] !== undefined);
            const isCurrent = (idx === this.activeQuestionIndex);
            const isFlagged = this.flaggedQuestions.has(q.id);

            let classes = 'palette-btn';
            if (isAnswered) classes += ' answered';
            if (isCurrent) classes += ' current';
            if (isFlagged) classes += ' flagged';

            return `
                <button onclick="appState.playerJumpTo(${idx})" class="${classes}" title="Question ${idx + 1}">
                    ${idx + 1}
                </button>
            `;
        }).join('');
    }

    // -------------------------------------------------------------
    // Submit Exam & Auto-Grading Evaluation
    // -------------------------------------------------------------
    confirmSubmitExam() {
        const questions = this.currentExam.questions;
        const total = questions.length;
        const answered = Object.keys(this.userAnswers).length;
        const unanswered = total - answered;
        const flagged = this.flaggedQuestions.size;

        document.getElementById('confirm-total-q').textContent = total;
        document.getElementById('confirm-answered-q').textContent = answered;
        document.getElementById('confirm-unanswered-q').textContent = unanswered;
        document.getElementById('confirm-flagged-q').textContent = flagged;

        const warning = document.getElementById('confirm-unanswered-warning');
        warning.classList.toggle('hidden', unanswered === 0);

        document.getElementById('modal-confirm-submit').classList.remove('hidden');
        this.renderIcons();
    }

    closeConfirmSubmitModal() {
        document.getElementById('modal-confirm-submit').classList.add('hidden');
    }

    async executeSubmitExam() {
        this.closeConfirmSubmitModal();
        this.stopTimer();

        const timeTaken = Math.round((new Date() - this.examStartTime) / 1000);
        this.showToast('Evaluating submissions and AI grading rubrics...', 'info');

        try {
            const res = await fetch(`${API_BASE}/exams/${this.currentExam.id}/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    answers: this.userAnswers,
                    time_taken: timeTaken,
                    provider: this.settings.provider,
                    api_key: this.getActiveApiKey()
                })
            });

            if (res.ok) {
                const results = await res.json();
                this.renderResults(results, timeTaken);
                this.navigateTo('results');
                this.showToast('Assessment evaluation complete!', 'success');
            } else {
                this.showToast('Evaluation submission failed', 'error');
            }
        } catch (e) {
            this.showToast('Network error during evaluation submission', 'error');
        }
    }

    // -------------------------------------------------------------
    // Results Scorecard View
    // -------------------------------------------------------------
    renderResults(data, timeTaken) {
        const score = data.score || 0;
        const pointsEarned = data.points_earned || 0;
        const totalPoints = data.total_points || this.currentExam.total_points || 0;
        const passed = data.passed || false;
        const passingScore = this.currentExam.passing_score || 75;

        // Radial gauge circle
        const circle = document.getElementById('result-score-circle');
        const scorePct = document.getElementById('result-score-percentage');
        scorePct.textContent = `${Math.round(score)}%`;
        circle.style.background = `conic-gradient(${passed ? '#10B981' : '#F43F5E'} ${score}%, rgba(255,255,255,0.12) ${score}%)`;

        // Headline & status badge
        const badge = document.getElementById('result-status-badge');
        const headline = document.getElementById('result-headline');
        const summary = document.getElementById('result-summary-text');

        if (passed) {
            badge.textContent = 'PASSED';
            badge.className = 'px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase inline-flex items-center gap-1.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
            headline.textContent = score >= 90 ? 'Outstanding Performance!' : 'Assessment Passed';
            summary.textContent = `You exceeded the required passing threshold of ${passingScore}% for this examination.`;
        } else {
            badge.textContent = 'NEEDS IMPROVEMENT';
            badge.className = 'px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase inline-flex items-center gap-1.5 bg-rose-500/20 text-rose-300 border border-rose-500/30';
            headline.textContent = 'Keep Practicing!';
            summary.textContent = `You scored below the passing mark of ${passingScore}%. Review the pedagogical feedback below.`;
        }

        // Metrics
        document.getElementById('result-points-earned').textContent = `${pointsEarned.toFixed(1)} / ${totalPoints.toFixed(1)}`;
        document.getElementById('result-time-taken').textContent = this.formatSeconds(timeTaken);
        document.getElementById('result-passing-score').textContent = `${passingScore}%`;

        // Review list
        const list = document.getElementById('results-breakdown-list');
        const questions = this.currentExam.questions;
        const feedback = data.feedback || {};
        const letters = ['A', 'B', 'C', 'D', 'E', 'F'];

        list.innerHTML = questions.map((q, idx) => {
            const userAns = this.userAnswers[q.id];
            const qFeedback = feedback[String(q.id)] || feedback[q.id] || {};
            const qScore = (qFeedback.score !== undefined) ? qFeedback.score : 0;

            let cardClass = 'incorrect';
            let statusText = 'Incorrect';
            if (qScore >= q.points) {
                cardClass = 'correct';
                statusText = 'Full Credit';
            } else if (qScore > 0) {
                cardClass = 'partial';
                statusText = 'Partial Credit';
            }

            let answerHtml = '';
            if (q.question_type === 'mcq' || q.question_type === 'true_false') {
                answerHtml = q.answers.map((ans, optIdx) => {
                    const isSelected = (userAns === optIdx);
                    const isCorrect = ans.is_correct;
                    const letter = letters[optIdx] || (optIdx + 1);

                    let optClass = 'review-opt';
                    let marker = '';
                    if (isCorrect) {
                        optClass += ' is-correct-ans';
                        marker = ' <strong class="text-emerald-700 ml-1">[CORRECT ANSWER]</strong>';
                    } else if (isSelected && !isCorrect) {
                        optClass += ' is-user-wrong';
                        marker = ' <span class="text-rose-700 ml-1">[YOUR SELECTION]</span>';
                    }

                    return `<div class="${optClass}">(${letter}) ${this.escapeHtml(ans.text)} ${marker}</div>`;
                }).join('');
            } else {
                answerHtml = `
                    <div class="space-y-2 mt-2 text-xs">
                        <div>
                            <strong class="text-slate-800">Your Submitted Response:</strong>
                            <div class="bg-slate-50 border border-slate-200 rounded-lg p-2.5 mt-1 text-slate-800">
                                ${userAns ? this.escapeHtml(userAns) : '<em class="text-slate-400">No response provided</em>'}
                            </div>
                        </div>
                        <div>
                            <strong class="text-emerald-800">Expected Model Rubric:</strong>
                            <div class="bg-emerald-50 border border-emerald-200 rounded-lg p-2.5 mt-1 text-emerald-950 font-medium">
                                ${this.escapeHtml(q.correct_answer || q.rubric || 'Refer to solution guidelines.')}
                            </div>
                        </div>
                    </div>
                `;
            }

            return `
                <div class="result-review-card ${cardClass}">
                    <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
                        <span class="text-xs font-bold text-slate-900 uppercase">Question ${idx + 1} • ${q.question_type.replace('_', ' ')}</span>
                        <span class="text-xs font-bold ${qScore >= q.points ? 'text-emerald-700' : (qScore > 0 ? 'text-amber-700' : 'text-rose-700')}">
                            Score: ${qScore.toFixed(1)} / ${q.points} pts (${statusText})
                        </span>
                    </div>

                    <div class="text-sm font-semibold text-slate-900 mb-2">
                        ${this.escapeHtml(q.question_text)}
                    </div>

                    ${answerHtml}

                    ${qFeedback.feedback ? `
                        <div class="feedback-bubble">
                            <strong>AI Evaluation:</strong> ${this.escapeHtml(qFeedback.feedback)}
                        </div>
                    ` : ''}

                    ${q.justification ? `
                        <div class="mt-3 bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs text-slate-600">
                            <strong>Pedagogical Rationale:</strong> ${this.escapeHtml(q.justification)}
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

        this.renderIcons();
    }

    retakeExam() {
        this.navigateTo('player');
    }

    // -------------------------------------------------------------
    // Export Hub Logic
    // -------------------------------------------------------------
    async loadExamAndExport(examId) {
        try {
            const res = await fetch(`${API_BASE}/exams/${examId}`);
            if (res.ok) {
                this.currentExam = await res.json();
                this.navigateTo('export');
            }
        } catch (e) {
            this.showToast('Error loading exam for export', 'error');
        }
    }

    updateExportView() {
        const titleEl = document.getElementById('export-exam-title');
        const shareUrlInput = document.getElementById('share-exam-url');

        if (this.currentExam) {
            titleEl.textContent = `${this.currentExam.title} (${this.currentExam.num_questions || this.currentExam.questions?.length || 0} Questions • ${(this.currentExam.total_points || 0).toFixed(1)} pts)`;
            shareUrlInput.value = `${window.location.origin}/#player?exam=${this.currentExam.id}`;
        } else {
            titleEl.textContent = 'Please select an examination from the Dashboard or Question Bank.';
            shareUrlInput.value = `${window.location.origin}/#player`;
        }
    }

    exportExam(format) {
        if (!this.currentExam) {
            this.showToast('Please select an examination to export', 'error');
            return;
        }

        const id = this.currentExam.id;

        if (format === 'pdf_student') {
            window.open(`${API_BASE}/export/${id}/pdf`, '_blank');
        } else if (format === 'pdf_teacher') {
            window.open(`${API_BASE}/export/${id}/solution-pdf`, '_blank');
        } else if (format === 'docx_student') {
            window.location.href = `${API_BASE}/export/${id}/docx`;
        } else if (format === 'docx_teacher') {
            window.location.href = `${API_BASE}/export/${id}/solution-docx`;
        } else if (format === 'csv') {
            window.location.href = `${API_BASE}/export/${id}/csv`;
        } else if (format === 'gift') {
            window.location.href = `${API_BASE}/export/${id}/gift`;
        } else if (format === 'json') {
            window.location.href = `${API_BASE}/export/${id}/json`;
        }
    }

    copyShareLink() {
        const input = document.getElementById('share-exam-url');
        input.select();
        navigator.clipboard.writeText(input.value);

        const btnText = document.getElementById('copy-link-text');
        btnText.textContent = 'Link Copied!';
        setTimeout(() => {
            btnText.textContent = 'Copy Link';
        }, 2000);

        this.showToast('Direct exam link copied to clipboard!', 'success');
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
        this.showToast('Engine settings saved successfully', 'success');
    }

    updateProviderBadge() {
        const label = document.getElementById('provider-label');
        if (!label) return;

        if (this.settings.provider === 'gemini') {
            label.textContent = 'Gemini AI';
        } else if (this.settings.provider === 'openai') {
            label.textContent = 'OpenAI';
        } else {
            label.textContent = 'Demo Engine';
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
        this.renderIcons();
    }

    closeSettings() {
        document.getElementById('modal-settings').classList.add('hidden');
    }

    handleProviderChange(provider) {
        const geminiBox = document.getElementById('settings-gemini-box');
        const openaiBox = document.getElementById('settings-openai-box');

        geminiBox.classList.toggle('hidden', provider !== 'gemini');
        openaiBox.classList.toggle('hidden', provider !== 'openai');
    }

    async testApiConnection() {
        const statusEl = document.getElementById('settings-test-status');
        statusEl.textContent = 'Testing connection...';
        statusEl.className = 'text-xs font-semibold text-indigo-600';

        try {
            const res = await fetch(`${API_BASE}/system/info`);
            if (res.ok) {
                const info = await res.json();
                statusEl.textContent = `Backend operational (${info.version || 'v2.4'})`;
                statusEl.className = 'text-xs font-semibold text-emerald-600';
            } else {
                statusEl.textContent = 'Backend unreachable';
                statusEl.className = 'text-xs font-semibold text-rose-600';
            }
        } catch (e) {
            statusEl.textContent = 'Connection failed';
            statusEl.className = 'text-xs font-semibold text-rose-600';
        }
    }

    // -------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let iconName = 'info';
        if (type === 'success') iconName = 'check-circle-2';
        if (type === 'error') iconName = 'alert-circle';

        toast.innerHTML = `
            <i data-lucide="${iconName}" class="w-4 h-4"></i>
            <span>${this.escapeHtml(message)}</span>
        `;

        container.appendChild(toast);
        this.renderIcons();

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    formatSeconds(sec) {
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        return `${m}m ${s}s`;
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
let appState;
document.addEventListener('DOMContentLoaded', () => {
    appState = new AppState();
});
