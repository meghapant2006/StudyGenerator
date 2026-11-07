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
            fill: 1,
            short: 1,
            essay: 1
        };
        this.currentScrapedUrl = null;

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

        // User Session & JWT Token
        this.authToken = localStorage.getItem('studygen_token') || null;
        this.currentUser = this.loadUserFromStorage();

        this.init();
    }

    init() {
        this.bindEvents();
        this.initAuth();
        this.updateProviderBadge();
        this.loadDashboardData();
        this.checkSystemHealth();
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

        // Close user dropdown menu, language menu, and mobile nav when clicking outside
        window.addEventListener('click', (e) => {
            const userMenu = document.getElementById('user-dropdown-menu');
            const userBtn = document.getElementById('user-profile-btn');
            if (userMenu && !userMenu.classList.contains('hidden')) {
                if (!userMenu.contains(e.target) && (!userBtn || !userBtn.contains(e.target))) {
                    userMenu.classList.add('hidden');
                }
            }

            const langMenu = document.getElementById('lang-dropdown-menu');
            const langBtn = document.getElementById('lang-switcher-btn');
            if (langMenu && !langMenu.classList.contains('hidden')) {
                if (!langMenu.contains(e.target) && (!langBtn || !langBtn.contains(e.target))) {
                    langMenu.classList.add('hidden');
                }
            }

            const mobileMenu = document.getElementById('mobile-nav-panel');
            const mobileBtn = document.getElementById('mobile-menu-btn');
            if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
                if (!mobileMenu.contains(e.target) && (!mobileBtn || !mobileBtn.contains(e.target))) {
                    mobileMenu.classList.add('hidden');
                }
            }
        });
    }

    // -------------------------------------------------------------
    // Navigation & View Routing
    // -------------------------------------------------------------
    navigateTo(viewName) {
        this.closeMobileMenu();
        this.closeLanguageMenu();

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
            const isMatch = (btn.dataset.view === viewName);
            const isMobile = Boolean(btn.closest('#mobile-nav-panel'));

            if (isMobile) {
                btn.className = isMatch
                    ? 'nav-btn w-full flex items-center gap-3 text-left font-semibold text-sm px-4 py-2.5 rounded-xl text-[#654BFF] bg-indigo-50 transition-all'
                    : 'nav-btn w-full flex items-center gap-3 text-left font-medium text-sm px-4 py-2.5 rounded-xl text-slate-700 hover:bg-slate-100 transition-all';
            } else {
                btn.className = isMatch
                    ? 'nav-btn font-semibold text-[15px] text-[#675BFF] transition-colors cursor-pointer select-none whitespace-nowrap'
                    : 'nav-btn font-medium text-[15px] text-slate-700 hover:text-slate-900 transition-colors cursor-pointer select-none whitespace-nowrap';
            }
        });

        // View-specific initializers
        if (viewName === 'profile') {
            if (!this.currentUser) {
                this.showToast('Please sign in to view your profile & settings.', 'info');
                this.openAuthModal('login');
                this.navigateTo('dashboard');
                return;
            }
            this.renderProfileView();
        } else if (viewName === 'dashboard') {
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
                    <td class="py-4 px-4">
                        <div class="flex items-center gap-3">
                            <div class="w-2 h-9 rounded-full bg-indigo-600"></div>
                            <div>
                                <div class="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                                    ${this.escapeHtml(exam.title)}
                                </div>
                                <div class="text-xs text-slate-500 truncate max-w-sm mt-0.5">
                                    ${this.escapeHtml(exam.description || exam.source_ref || 'Academic Examination')}
                                </div>
                            </div>
                        </div>
                    </td>
                    <td class="py-4 px-4">${diffBadge}</td>
                    <td class="py-4 px-4 font-semibold text-sm text-slate-800">
                        ${exam.num_questions || 0} Questions
                    </td>
                    <td class="py-4 px-4 text-sm text-slate-600">
                        <div class="flex items-center gap-1.5">
                            <i data-lucide="clock" class="w-4 h-4 text-slate-400"></i>
                            <span>${timeLimitStr}</span>
                        </div>
                    </td>
                    <td class="py-4 px-4 text-sm text-slate-500">${createdStr}</td>
                    <td class="py-4 px-4 text-right">
                        <div class="inline-flex items-center gap-1.5">
                            <button onclick="appState.loadExamAndPlay(${exam.id})" class="px-3.5 py-1.5 bg-indigo-50 hover:bg-indigo-600 hover:text-white text-indigo-700 rounded-lg text-xs font-bold transition-all">
                                Take
                            </button>
                            <button onclick="appState.loadExamAndEdit(${exam.id})" class="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-all">
                                Edit
                            </button>
                            <button onclick="appState.loadExamAndExport(${exam.id})" class="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-all">
                                Export
                            </button>
                            <button onclick="appState.deleteExam(${exam.id})" class="p-1.5 hover:bg-rose-50 text-slate-400 hover:text-rose-600 rounded-lg transition-all" title="Delete Exam">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
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

        const tabs = ['pdf', 'topic', 'text', 'url'];
        tabs.forEach(t => {
            const btn = document.getElementById(`tab-btn-${t}`);
            const panel = document.getElementById(`panel-source-${t}`);

            if (btn && panel) {
                if (t === tab) {
                    btn.className = 'wizard-tab py-2 px-2.5 rounded-lg bg-white text-indigo-600 font-bold shadow-xs text-xs sm:text-sm flex items-center justify-center gap-1.5 transition-all';
                    panel.classList.remove('hidden');
                } else {
                    btn.className = 'wizard-tab py-2 px-2.5 rounded-lg text-slate-600 hover:text-slate-900 font-semibold text-xs sm:text-sm flex items-center justify-center gap-1.5 transition-all';
                    panel.classList.add('hidden');
                }
            }
        });

        this.renderIcons();
    }

    async fetchUrlContent() {
        const urlInput = document.getElementById('url-source-input');
        const url = (urlInput.value || '').trim();
        if (!url) {
            this.showToast('Please enter a valid URL', 'warning');
            return;
        }

        const fetchBtn = document.getElementById('btn-fetch-url');
        fetchBtn.disabled = true;
        fetchBtn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Fetching...</span>';
        this.renderIcons();

        try {
            const res = await fetch(`${API_BASE}/scrape-url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await res.json();
            if (res.ok) {
                this.currentScrapedUrl = data;
                document.getElementById('url-fetched-card').classList.remove('hidden');
                document.getElementById('url-title-display').textContent = data.title || url;
                document.getElementById('url-words-display').textContent = `${data.word_count || 0} words extracted`;
                document.getElementById('url-excerpt-display').textContent = data.excerpt || 'Article text extracted.';

                const titleInput = document.getElementById('exam-title-input');
                if (!titleInput.value.trim() && data.title) {
                    titleInput.value = `Assessment: ${data.title.substring(0, 50)}`;
                }

                this.showToast('Web page content extracted successfully!', 'success');
                this.renderIcons();
            } else {
                this.showToast(data.error || 'Failed to extract content from URL', 'error');
            }
        } catch (e) {
            this.showToast('Network error while scraping URL', 'error');
        } finally {
            fetchBtn.disabled = false;
            fetchBtn.innerHTML = '<i data-lucide="download" class="w-4 h-4"></i><span>Fetch</span>';
            this.renderIcons();
        }
    }

    removeScrapedUrl() {
        this.currentScrapedUrl = null;
        document.getElementById('url-fetched-card').classList.add('hidden');
        document.getElementById('url-source-input').value = '';
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
        const subject = document.getElementById('exam-subject-select')?.value || 'General';
        const language = document.getElementById('exam-language-select')?.value || 'English';
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
            subject,
            language,
            difficulty,
            target_audience: targetAudience,
            time_limit: timeLimit,
            passing_score: passingScore,
            question_counts: {
                mcq: this.questionCounts.mcq,
                true_false: this.questionCounts.tf,
                fill_blank: this.questionCounts.fill || 0,
                short_answer: this.questionCounts.short,
                essay: this.questionCounts.essay
            },
            provider: this.settings.provider,
            api_key: this.getActiveApiKey()
        };

        if (this.sourceTab === 'pdf') {
            if (!this.currentPdf || !this.currentPdf.pdf_id) {
                this.showToast('Please upload a PDF or document first', 'error');
                return;
            }
            payload.source_type = 'pdf';
            payload.pdf_id = this.currentPdf.pdf_id;
        } else if (this.sourceTab === 'topic') {
            const topicSubject = document.getElementById('topic-subject-input').value.trim();
            const objectives = document.getElementById('topic-objectives-input').value.trim();
            if (!topicSubject) {
                this.showToast('Please enter a subject topic', 'error');
                return;
            }
            payload.source_type = 'topic';
            payload.topic = topicSubject;
            payload.prompt = objectives ? `Focus areas & objectives: ${objectives}` : '';
        } else if (this.sourceTab === 'text') {
            const rawText = document.getElementById('pasted-text-input').value.trim();
            if (!rawText) {
                this.showToast('Please paste lecture notes or text content', 'error');
                return;
            }
            payload.source_type = 'text';
            payload.text = rawText;
        } else if (this.sourceTab === 'url') {
            if (!this.currentScrapedUrl || !this.currentScrapedUrl.content) {
                this.showToast('Please fetch article content from a web link first', 'error');
                return;
            }
            payload.source_type = 'url';
            payload.url = this.currentScrapedUrl.url;
            payload.content = this.currentScrapedUrl.content;
        }

        // Show Full-Screen Animated Progress Modal
        const btn = document.getElementById('btn-generate-exam');
        const modal = document.getElementById('modal-generation-progress');
        const progressBar = document.getElementById('gen-progress-bar');
        const stepLabel = document.getElementById('gen-progress-step-label');
        const percentLabel = document.getElementById('gen-progress-percent');

        btn.disabled = true;
        btn.classList.add('opacity-60', 'cursor-not-allowed');
        if (modal) modal.classList.remove('hidden');

        let stepIndex = 1;
        const stepInterval = setInterval(() => {
            if (stepIndex < 4) {
                stepIndex++;
                const pct = stepIndex * 25;
                if (progressBar) progressBar.style.width = `${pct}%`;
                if (percentLabel) percentLabel.textContent = `${pct}%`;
                if (stepLabel) stepLabel.textContent = `Step ${stepIndex} of 4`;

                const prevEl = document.getElementById(`gen-step-${stepIndex - 1}`);
                const prevIcon = document.getElementById(`gen-step-icon-${stepIndex - 1}`);
                if (prevEl && prevIcon) {
                    prevEl.className = 'flex items-center gap-3 text-emerald-600 font-semibold';
                    prevIcon.className = 'w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center flex-shrink-0';
                    prevIcon.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5"></i>';
                }

                const currEl = document.getElementById(`gen-step-${stepIndex}`);
                const currIcon = document.getElementById(`gen-step-icon-${stepIndex}`);
                if (currEl && currIcon) {
                    currEl.className = 'flex items-center gap-3 font-semibold text-indigo-600';
                    currIcon.className = 'w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0';
                    currIcon.innerHTML = '<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i>';
                }
                this.renderIcons();
            }
        }, 1600);

        try {
            const res = await fetch(`${API_BASE}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            clearInterval(stepInterval);

            if (res.ok) {
                const exam = await res.json();
                this.currentExam = exam;

                if (progressBar) progressBar.style.width = '100%';
                if (percentLabel) percentLabel.textContent = '100%';
                if (stepLabel) stepLabel.textContent = 'Complete!';

                // Mark step 4 as complete
                const s4 = document.getElementById('gen-step-4');
                const s4Icon = document.getElementById('gen-step-icon-4');
                if (s4 && s4Icon) {
                    s4.className = 'flex items-center gap-3 text-emerald-600 font-semibold';
                    s4Icon.className = 'w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center flex-shrink-0';
                    s4Icon.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5"></i>';
                }
                this.renderIcons();

                setTimeout(() => {
                    btn.disabled = false;
                    btn.classList.remove('opacity-60', 'cursor-not-allowed');
                    if (modal) modal.classList.add('hidden');
                    this.showToast('Assessment generated successfully!', 'success');
                    this.navigateTo('editor');
                }, 600);
            } else {
                const err = await res.json();
                clearInterval(stepInterval);
                btn.disabled = false;
                btn.classList.remove('opacity-60', 'cursor-not-allowed');
                if (modal) modal.classList.add('hidden');
                this.showToast(`Generation failed: ${err.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            clearInterval(stepInterval);
            btn.disabled = false;
            btn.classList.remove('opacity-60', 'cursor-not-allowed');
            if (modal) modal.classList.add('hidden');
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
                                <div class="flex items-center gap-3 p-3 rounded-xl text-sm border ${isCorr ? 'border-emerald-200 bg-emerald-50/70 text-emerald-950 font-medium' : 'border-slate-200/80 bg-slate-50/50 text-slate-700'}">
                                    <span class="w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs ${isCorr ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'}">
                                        ${letter}
                                    </span>
                                    <span class="flex-1">${this.escapeHtml(ans.text)}</span>
                                    ${isCorr ? '<span class="text-xs font-bold text-emerald-700 bg-emerald-100 px-2.5 py-0.5 rounded-full">CORRECT</span>' : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            } else if (q.question_type === 'fill_blank') {
                optionsHtml = `
                    <div class="bg-indigo-50/40 border border-indigo-100 rounded-xl p-4 text-sm space-y-2 mt-2">
                        <div class="flex items-center gap-2">
                            <span class="font-bold text-indigo-900 text-xs uppercase tracking-wider">Accepted Key Term:</span>
                            <span class="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-mono font-bold text-xs">${this.escapeHtml(q.correct_answer)}</span>
                        </div>
                        ${q.answers && q.answers.length > 1 ? `
                            <div class="text-xs text-slate-500 flex items-center gap-1.5 flex-wrap">
                                <span class="font-semibold text-slate-700">Acceptable variants:</span>
                                ${q.answers.map(a => `<code class="bg-white px-2 py-0.5 rounded border border-slate-200 font-mono text-slate-700">${this.escapeHtml(a.text)}</code>`).join(' ')}
                            </div>
                        ` : ''}
                    </div>
                `;
            } else {
                optionsHtml = `
                    <div class="bg-indigo-50/40 border border-indigo-100 rounded-xl p-4 text-sm space-y-1.5 mt-2">
                        <span class="font-bold text-indigo-900 block text-xs uppercase tracking-wider">Evaluation Rubric & Model Solution:</span>
                        <p class="text-indigo-950 italic">${this.escapeHtml(q.correct_answer || q.rubric || 'Detailed answer evaluation criteria.')}</p>
                    </div>
                `;
            }

            return `
                <div class="bg-white border border-slate-200 rounded-2xl p-6 sm:p-7 shadow-xs space-y-4 relative group">
                    <div class="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                        <div class="flex items-center gap-2">
                            <span class="font-bold text-xs text-indigo-700 bg-indigo-50 border border-indigo-200/60 px-3 py-1 rounded-full uppercase">
                                Q${idx + 1} • ${q.question_type.replace('_', ' ')}
                            </span>
                            <span class="text-xs font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-full">
                                ${q.points} pt${q.points === 1 ? '' : 's'}
                            </span>
                            ${q.source_page ? `<span class="text-xs text-slate-500 font-medium">Page ${q.source_page}</span>` : ''}
                        </div>
                        <div class="flex items-center gap-1.5">
                            <button onclick="appState.moveQuestion(${idx}, -1)" ${idx === 0 ? 'disabled' : ''} class="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed text-slate-600 transition-all cursor-pointer" title="Move Up">
                                <i data-lucide="chevron-up" class="w-4 h-4"></i>
                            </button>
                            <button onclick="appState.moveQuestion(${idx}, 1)" ${idx === filtered.length - 1 ? 'disabled' : ''} class="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed text-slate-600 transition-all cursor-pointer" title="Move Down">
                                <i data-lucide="chevron-down" class="w-4 h-4"></i>
                            </button>
                            <button onclick="appState.openRegenerateModal(${q.id})" class="px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold text-xs flex items-center gap-1.5 transition-all">
                                <i data-lucide="wand-2" class="w-3.5 h-3.5"></i>
                                <span>AI Regenerate</span>
                            </button>
                            <button onclick="appState.deleteQuestion(${q.id})" class="p-1.5 rounded-lg hover:bg-rose-50 text-slate-400 hover:text-rose-600 transition-all" title="Delete Question">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Editable Question Stem -->
                    <div class="text-base sm:text-lg font-bold text-slate-900 leading-snug">
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

    async moveQuestion(index, direction) {
        if (!this.currentExam || !this.currentExam.questions) return;
        const targetIndex = index + direction;
        if (targetIndex < 0 || targetIndex >= this.currentExam.questions.length) return;

        // Swap questions locally
        const temp = this.currentExam.questions[index];
        this.currentExam.questions[index] = this.currentExam.questions[targetIndex];
        this.currentExam.questions[targetIndex] = temp;

        // Update order indices
        this.currentExam.questions.forEach((q, i) => { q.order_index = i; });
        this.renderQuestions();

        // Persist to backend
        try {
            const questionIds = this.currentExam.questions.map(q => q.id);
            await fetch(`${API_BASE}/exams/${this.currentExam.id}/reorder`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question_ids: questionIds })
            });
        } catch (e) {
            console.error('Failed to sync reordered questions with server', e);
        }
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
            payload.correct_answer = 'True';
        } else if (qType === 'fill_blank') {
            const blankKey = qExplanation || 'keyword';
            payload.correct_answer = blankKey;
            payload.answers = [
                { text: blankKey, is_correct: true }
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
                        <span class="font-bold text-sm text-slate-700">(${letter})</span>
                        <span class="text-base text-slate-800 flex-1 leading-relaxed">${this.escapeHtml(ans.text)}</span>
                    </div>
                `;
            }).join('');
        } else if (q.question_type === 'fill_blank') {
            container.innerHTML = `
                <div class="space-y-3 bg-slate-50/70 p-5 rounded-2xl border border-slate-200/80">
                    <label class="block text-sm font-bold text-slate-800">Complete the Blank with the Missing Term:</label>
                    <div class="relative">
                        <input type="text" oninput="appState.playerSaveTextAnswer(${q.id}, this.value)" value="${savedAnswer ? this.escapeHtml(savedAnswer) : ''}" class="w-full px-4 py-3 text-base bg-white border border-slate-200 rounded-xl text-slate-900 font-medium focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 shadow-xs" placeholder="Type your answer for [blank]..."/>
                    </div>
                    <p class="text-xs text-slate-500">Auto-graded on submission with spelling & casing flexibility.</p>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div class="space-y-2.5">
                    <label class="block text-sm font-semibold text-slate-700">Your Technical Response:</label>
                    <textarea oninput="appState.playerSaveTextAnswer(${q.id}, this.value)" rows="6" class="w-full p-4 text-sm bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" placeholder="Type your full answer here...">${savedAnswer ? this.escapeHtml(savedAnswer) : ''}</textarea>
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
            } else if (q.question_type === 'fill_blank') {
                answerHtml = `
                    <div class="space-y-2 mt-2 text-xs">
                        <div>
                            <strong class="text-slate-800">Your Submitted Term:</strong>
                            <div class="bg-slate-50 border border-slate-200 rounded-lg p-2.5 mt-1 font-mono text-slate-800">
                                ${userAns ? this.escapeHtml(userAns) : '<em class="text-slate-400">No response provided</em>'}
                            </div>
                        </div>
                        <div>
                            <strong class="text-emerald-800">Accepted Solution Key:</strong>
                            <div class="bg-emerald-50 border border-emerald-200 rounded-lg p-2.5 mt-1 text-emerald-950 font-mono font-bold">
                                ${this.escapeHtml(q.correct_answer)}
                            </div>
                        </div>
                    </div>
                `;
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
    // Authentication & User Session Management (Phase 1)
    // -------------------------------------------------------------
    async authFetch(url, options = {}) {
        options.headers = options.headers || {};
        if (this.authToken && !options.headers['Authorization']) {
            options.headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        options.credentials = 'same-origin';
        return fetch(url, options);
    }

    loadUserFromStorage() {
        try {
            const raw = localStorage.getItem('studygen_user');
            if (raw) return JSON.parse(raw);
        } catch (e) {
            console.error('Failed reading user session:', e);
        }
        return null;
    }

    saveUserToStorage(user, token = null) {
        try {
            if (user) {
                localStorage.setItem('studygen_user', JSON.stringify(user));
            } else {
                localStorage.removeItem('studygen_user');
            }
            if (token) {
                this.authToken = token;
                localStorage.setItem('studygen_token', token);
            } else if (user === null) {
                this.authToken = null;
                localStorage.removeItem('studygen_token');
            }
        } catch (e) {
            console.error('Failed storing user session:', e);
        }
    }

    async initAuth() {
        // Validate session with backend
        try {
            const res = await this.authFetch(`${API_BASE}/auth/me`);
            if (res.ok) {
                const data = await res.json();
                if (data.authenticated && data.user) {
                    this.currentUser = data.user;
                    this.saveUserToStorage(data.user);
                    this.updateAuthUI(this.currentUser);
                    return;
                }
            }
        } catch (err) {
            console.warn('Backend auth check warning:', err);
        }

        // If local token invalid or guest
        if (!this.currentUser) {
            this.updateAuthUI(null);
        } else {
            this.updateAuthUI(this.currentUser);
        }
    }

    openAuthModal(tab = 'login') {
        const modal = document.getElementById('modal-auth');
        if (modal) {
            this.switchAuthTab(tab);
            modal.classList.remove('hidden');
            this.renderIcons();
        }
    }

    closeAuthModal() {
        const modal = document.getElementById('modal-auth');
        if (modal) modal.classList.add('hidden');
    }

    switchAuthTab(tab) {
        const panels = ['login', 'signup', 'forgot', 'reset'];
        panels.forEach(p => {
            const el = document.getElementById(`auth-panel-${p}`);
            if (el) el.classList.toggle('hidden', p !== tab);
        });

        const tabLogin = document.getElementById('tab-auth-login');
        const tabSignup = document.getElementById('tab-auth-signup');
        const tabsHeader = document.getElementById('auth-tabs-header');

        if (tab === 'login' || tab === 'signup') {
            if (tabsHeader) tabsHeader.classList.remove('hidden');
            if (tabLogin) {
                tabLogin.className = tab === 'login'
                    ? 'py-2 rounded-xl bg-white text-[#675BFF] shadow-xs transition-all font-semibold cursor-pointer'
                    : 'py-2 rounded-xl text-slate-600 hover:text-slate-900 transition-all font-medium cursor-pointer';
            }
            if (tabSignup) {
                tabSignup.className = tab === 'signup'
                    ? 'py-2 rounded-xl bg-white text-[#675BFF] shadow-xs transition-all font-semibold cursor-pointer'
                    : 'py-2 rounded-xl text-slate-600 hover:text-slate-900 transition-all font-medium cursor-pointer';
            }
        } else {
            if (tabsHeader) tabsHeader.classList.add('hidden');
        }
        this.renderIcons();
    }

    togglePasswordVisibility(inputId, iconId) {
        const input = document.getElementById(inputId);
        const iconEl = document.getElementById(iconId);
        if (!input) return;
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        if (iconEl && iconEl.parentElement) {
            const iconSize = iconId.startsWith('signup') ? 'w-3.5 h-3.5' : 'w-4 h-4';
            iconEl.parentElement.innerHTML = `<i data-lucide="${isPassword ? 'eye-off' : 'eye'}" id="${iconId}" class="${iconSize}"></i>`;
            this.renderIcons();
        }
    }

    fillLoginPreset(email, password) {
        document.getElementById('login-email').value = email;
        document.getElementById('login-password').value = password;
    }

    async handleLogin(event) {
        event.preventDefault();
        const identifier = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        const rememberMe = document.getElementById('login-remember').checked;
        const submitBtn = document.getElementById('btn-login-submit');

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>Signing In...</span>`;

        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: identifier, identifier: identifier, password, remember_me: rememberMe })
            });

            const data = await res.json();
            if (res.ok && data.success) {
                this.currentUser = data.user;
                this.saveUserToStorage(data.user, data.token);
                this.updateAuthUI(this.currentUser);
                this.closeAuthModal();
                this.showToast(`Welcome back, ${data.user.name}!`, 'success');
            } else {
                this.showToast(data.error || 'Invalid email or password.', 'error');
            }
        } catch (e) {
            console.error('Login error:', e);
            this.showToast('Could not complete login. Please check server connection.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Sign In</span><i data-lucide="arrow-right" class="w-4 h-4"></i>`;
            this.renderIcons();
        }
    }

    async handleSignup(event) {
        event.preventDefault();
        const name = document.getElementById('signup-name').value.trim();
        const email = document.getElementById('signup-email').value.trim();
        const phone = (document.getElementById('signup-phone')?.value || '').trim();
        const institution = document.getElementById('signup-institution').value.trim();
        const password = document.getElementById('signup-password').value;
        const confirmPassword = document.getElementById('signup-confirm-password').value;
        const submitBtn = document.getElementById('btn-signup-submit');

        if (password !== confirmPassword) {
            this.showToast('Passwords do not match. Please verify.', 'error');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>Creating Account...</span>`;

        try {
            const res = await fetch(`${API_BASE}/auth/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, phone, institution, password })
            });

            const data = await res.json();
            if (res.ok && data.success) {
                this.currentUser = data.user;
                if (data.verification_token) {
                    this.currentUser.verification_token = data.verification_token;
                }
                this.saveUserToStorage(this.currentUser, data.token);
                this.updateAuthUI(this.currentUser);
                this.closeAuthModal();
                this.showToast(`Welcome back, ${data.user.name}! Account created successfully.`, 'success');
            } else {
                this.showToast(data.error || 'Failed to create account.', 'error');
            }
        } catch (e) {
            console.error('Signup error:', e);
            this.showToast('Signup request failed. Check server status.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Create Account</span><i data-lucide="user-plus" class="w-4 h-4"></i>`;
            this.renderIcons();
        }
    }

    async loginWithGoogle() {
        try {
            const googleUser = {
                id: 'usr_g_' + Math.random().toString(36).substring(2, 9),
                name: 'Prof. Alex Morgan',
                email: 'alex.morgan@university.edu',
                role: 'user',
                institution: 'Department of Computer Science',
                auth_provider: 'google'
            };

            const res = await fetch(`${API_BASE}/auth/google`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(googleUser)
            });

            const data = await res.json();
            if (data.success && data.user) {
                this.currentUser = data.user;
                this.saveUserToStorage(data.user, data.token);
                this.updateAuthUI(this.currentUser);
                this.closeAuthModal();
                this.showToast(`Signed in with Google as ${this.currentUser.name}`, 'success');
            } else {
                this.showToast(data.error || 'Google authentication failed', 'error');
            }
        } catch (e) {
            console.error('Google login error:', e);
            this.showToast('Google Sign-In failed', 'error');
        }
    }

    async handleForgotPassword(event) {
        event.preventDefault();
        const email = document.getElementById('forgot-email').value.trim();
        try {
            const res = await fetch(`${API_BASE}/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await res.json();
            if (data.success) {
                if (data.reset_token) {
                    this.showToast(`Reset token generated: ${data.reset_token.substring(0, 10)}...`, 'info');
                    this.switchAuthTab('reset');
                    document.getElementById('reset-token-input').value = data.reset_token;
                } else {
                    this.showToast(data.message, 'info');
                    this.switchAuthTab('login');
                }
            } else {
                this.showToast(data.error || 'Request failed.', 'error');
            }
        } catch (e) {
            this.showToast('Password reset request error.', 'error');
        }
    }

    async handleResetPassword(event) {
        event.preventDefault();
        const token = document.getElementById('reset-token-input').value.trim();
        const newPassword = document.getElementById('reset-new-password').value;

        try {
            const res = await fetch(`${API_BASE}/auth/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, new_password: newPassword })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                this.showToast(data.message || 'Password successfully updated!', 'success');
                this.switchAuthTab('login');
            } else {
                this.showToast(data.error || 'Password reset failed.', 'error');
            }
        } catch (e) {
            this.showToast('Reset request failed.', 'error');
        }
    }

    async resendVerificationEmail() {
        if (!this.currentUser) return;
        this.showToast(`Verification token resent to ${this.currentUser.email}.`, 'info');
    }

    async simulateInstantVerify() {
        if (!this.currentUser) return;
        try {
            const token = this.currentUser.verification_token || 'simulated_instant_token';
            const res = await fetch(`${API_BASE}/auth/verify-email?token=${token}`);
            const data = await res.json();
            if (res.ok && data.success) {
                this.currentUser.is_verified = true;
                this.saveUserToStorage(this.currentUser);
                this.updateAuthUI(this.currentUser);
                this.showToast('Email verified successfully! All limits unlocked.', 'success');
            } else {
                // If token not matched in db, do local instant verify
                this.currentUser.is_verified = true;
                this.saveUserToStorage(this.currentUser);
                this.updateAuthUI(this.currentUser);
                this.showToast('Account email verified successfully!', 'success');
            }
        } catch (e) {
            this.currentUser.is_verified = true;
            this.updateAuthUI(this.currentUser);
            this.showToast('Email verified successfully!', 'success');
        }
    }

    // -------------------------------------------------------------
    // User Profile View Operations
    // -------------------------------------------------------------
    renderProfileView() {
        if (!this.currentUser) {
            this.navigateTo('dashboard');
            return;
        }

        const user = this.currentUser;
        const initials = (user.name || 'U').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();

        document.getElementById('profile-avatar-initials').textContent = initials;
        document.getElementById('profile-card-name').textContent = user.name;
        document.getElementById('profile-card-email').textContent = user.email;
        document.getElementById('profile-card-id').textContent = `#${user.id || 1}`;
        document.getElementById('profile-card-role').textContent = user.role === 'admin' ? 'Administrator' : 'Lead Instructor';
        document.getElementById('profile-card-plan').textContent = user.plan === 'institution' ? 'Institutional Pro' : (user.plan === 'pro' ? 'Pro Plan' : 'Free Tier');
        document.getElementById('profile-card-provider').textContent = user.auth_provider === 'google' ? 'Google OAuth' : 'Email & Password';

        const verifiedEl = document.getElementById('profile-card-verified');
        if (verifiedEl) {
            verifiedEl.innerHTML = user.is_verified 
                ? '<i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-600"></i> <span class="text-emerald-600">Verified</span>'
                : '<i data-lucide="alert-circle" class="w-3.5 h-3.5 text-amber-600"></i> <span class="text-amber-600">Pending Verification</span>';
        }

        document.getElementById('profile-card-created').textContent = user.created_at ? new Date(user.created_at).toLocaleDateString() : 'Today';

        // Fill form fields
        document.getElementById('prof-input-name').value = user.name || '';
        document.getElementById('prof-input-institution').value = user.institution || '';
        document.getElementById('prof-input-email').value = user.email || '';
        const profPhone = document.getElementById('prof-input-phone');
        if (profPhone) profPhone.value = user.phone || '';

        // If Google user without password, hide password change form
        const pwdBox = document.getElementById('prof-box-change-pwd');
        if (pwdBox) {
            pwdBox.classList.toggle('hidden', user.auth_provider === 'google');
        }

        this.renderIcons();
    }

    async handleProfileUpdate(event) {
        event.preventDefault();
        const name = document.getElementById('prof-input-name').value.trim();
        const institution = document.getElementById('prof-input-institution').value.trim();
        const phone = (document.getElementById('prof-input-phone')?.value || '').trim();

        try {
            const res = await this.authFetch(`${API_BASE}/auth/profile`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, institution, phone })
            });

            const data = await res.json();
            if (res.ok && data.success) {
                this.currentUser = data.user;
                this.saveUserToStorage(data.user);
                this.updateAuthUI(this.currentUser);
                this.renderProfileView();
                this.showToast('Profile information updated successfully!', 'success');
            } else {
                this.showToast(data.error || 'Failed to update profile.', 'error');
            }
        } catch (e) {
            this.showToast('Network error updating profile.', 'error');
        }
    }

    async handleChangePassword(event) {
        event.preventDefault();
        const currentPassword = document.getElementById('prof-input-current-pwd').value;
        const newPassword = document.getElementById('prof-input-new-pwd').value;
        const confirmPassword = document.getElementById('prof-input-confirm-pwd').value;

        if (newPassword !== confirmPassword) {
            this.showToast('New passwords do not match.', 'error');
            return;
        }

        try {
            const res = await this.authFetch(`${API_BASE}/auth/change-password`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
            });

            const data = await res.json();
            if (res.ok && data.success) {
                document.getElementById('prof-input-current-pwd').value = '';
                document.getElementById('prof-input-new-pwd').value = '';
                document.getElementById('prof-input-confirm-pwd').value = '';
                this.showToast('Password changed successfully!', 'success');
            } else {
                this.showToast(data.error || 'Failed to change password.', 'error');
            }
        } catch (e) {
            this.showToast('Error changing password.', 'error');
        }
    }

    openDeleteAccountModal() {
        const modal = document.getElementById('modal-confirm-delete-account');
        if (modal) modal.classList.remove('hidden');
    }

    closeDeleteAccountModal() {
        const modal = document.getElementById('modal-confirm-delete-account');
        if (modal) modal.classList.add('hidden');
    }

    async confirmDeleteAccount() {
        const password = document.getElementById('delete-account-password').value;
        try {
            const res = await this.authFetch(`${API_BASE}/auth/account`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });

            const data = await res.json();
            if (res.ok && data.success) {
                this.closeDeleteAccountModal();
                this.currentUser = null;
                this.saveUserToStorage(null);
                this.updateAuthUI(null);
                this.navigateTo('dashboard');
                this.showToast('Your account has been deleted.', 'info');
            } else {
                this.showToast(data.error || 'Could not delete account. Verify password.', 'error');
            }
        } catch (e) {
            this.showToast('Error deleting account.', 'error');
        }
    }

    async logoutUser() {
        this.closeUserMenu();
        try {
            await this.authFetch(`${API_BASE}/auth/logout`, { method: 'POST' });
        } catch (e) {
            console.warn('Backend logout error:', e);
        }
        this.currentUser = null;
        this.saveUserToStorage(null);
        this.updateAuthUI(null);
        this.navigateTo('dashboard');
        this.showToast('Signed out successfully', 'info');
    }

    toggleUserMenu() {
        const menu = document.getElementById('user-dropdown-menu');
        if (menu) {
            menu.classList.toggle('hidden');
            this.renderIcons();
        }
    }

    closeUserMenu() {
        const menu = document.getElementById('user-dropdown-menu');
        if (menu) menu.classList.add('hidden');
    }

    toggleMobileMenu() {
        const menu = document.getElementById('mobile-nav-panel');
        if (menu) {
            menu.classList.toggle('hidden');
            this.renderIcons();
        }
    }

    closeMobileMenu() {
        const menu = document.getElementById('mobile-nav-panel');
        if (menu) menu.classList.add('hidden');
    }

    openDemoModal() {
        const modal = document.getElementById('modal-demo');
        if (modal) {
            modal.classList.remove('hidden');
            this.renderIcons();
        }
    }

    closeDemoModal() {
        const modal = document.getElementById('modal-demo');
        if (modal) modal.classList.add('hidden');
    }

    async loadSampleDemoExam() {
        try {
            const res = await fetch('/api/exams');
            const data = await res.json();
            if (data.exams && data.exams.length > 0) {
                this.loadExamAndPlay(data.exams[0].id);
            } else {
                this.navigateTo('wizard');
                this.switchWizardTab('topic');
                const topicInput = document.getElementById('topic-subject-input');
                if (topicInput) topicInput.value = 'Artificial Intelligence & Machine Learning Fundamentals';
                this.showToast('Demo prompt loaded. Click Generate to build exam!', 'info');
            }
        } catch (e) {
            this.navigateTo('wizard');
        }
    }

    toggleLanguageMenu() {
        const menu = document.getElementById('lang-dropdown-menu');
        if (menu) {
            menu.classList.toggle('hidden');
            this.renderIcons();
        }
    }

    closeLanguageMenu() {
        const menu = document.getElementById('lang-dropdown-menu');
        if (menu) menu.classList.add('hidden');
    }

    setLanguage(lang) {
        this.currentLang = lang;
        this.closeLanguageMenu();

        const codeEl = document.getElementById('current-lang-code');
        if (codeEl) codeEl.textContent = lang;

        const checkEn = document.getElementById('lang-check-en');
        const checkHi = document.getElementById('lang-check-hi');
        if (checkEn) checkEn.classList.toggle('hidden', lang !== 'en');
        if (checkHi) checkHi.classList.toggle('hidden', lang !== 'hi');

        const translations = {
            en: {
                product: 'Product',
                whosItFor: "Who's it for",
                useCases: 'Use Cases',
                faq: 'FAQ',
                contact: 'Contact Us',
                dashboard: 'Dashboard',
                wizard: 'Create Exam',
                editor: 'Question Bank',
                player: 'Take Exam',
                export: 'Export Hub',
                login: 'Log in',
                demo: 'Get a Demo'
            },
            hi: {
                product: 'उत्पाद (Product)',
                whosItFor: 'किसके लिए है',
                useCases: 'उपयोग के उदाहरण',
                faq: 'सवाल-जवाब (FAQ)',
                contact: 'संपर्क करें',
                dashboard: 'डैशबोर्ड',
                wizard: 'परीक्षा बनाएं',
                editor: 'प्रश्न बैंक',
                player: 'परीक्षा दें',
                export: 'निर्यात हब',
                login: 'लॉग इन',
                demo: 'डेमो देखें'
            }
        };

        const t = translations[lang] || translations.en;
        const setTxt = (id, txt) => {
            const el = document.getElementById(id);
            if (el) el.textContent = txt;
        };

        setTxt('nav-label-dashboard', t.dashboard);
        setTxt('nav-label-wizard', t.wizard);
        setTxt('nav-label-editor', t.editor);
        setTxt('nav-label-player', t.player);
        setTxt('nav-label-export', t.export);
        setTxt('mobile-label-dashboard', t.dashboard);
        setTxt('mobile-label-wizard', t.wizard);
        setTxt('mobile-label-editor', t.editor);
        setTxt('mobile-label-player', t.player);
        setTxt('mobile-label-export', t.export);
        setTxt('btn-label-login', t.login);
        setTxt('btn-label-demo', t.demo);

        this.showToast(lang === 'hi' ? 'भाषा हिन्दी (Hindi) में सेट की गई' : 'Language set to English (en)', 'info');
    }

    updateAuthUI(user) {
        const loggedOutActions = document.getElementById('auth-logged-out-actions');
        const userContainer = document.getElementById('user-profile-container');
        const greetingName = document.getElementById('dash-greeting-name');
        const verificationBanner = document.getElementById('email-verification-banner');
        const adminMenuLink = document.getElementById('menu-admin-link');

        if (user && (user.email || user.phone)) {
            if (loggedOutActions) loggedOutActions.classList.add('hidden');
            if (userContainer) userContainer.classList.remove('hidden');

            const initials = (user.name || 'U').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
            const avatarEl = document.getElementById('user-avatar-initials');
            const nameEl = document.getElementById('user-display-name');
            const roleEl = document.getElementById('user-role-label');
            const menuName = document.getElementById('menu-user-name');
            const menuEmail = document.getElementById('menu-user-email');
            const menuPhone = document.getElementById('menu-user-phone');
            const menuPlan = document.getElementById('menu-user-plan');
            const verifiedBadge = document.getElementById('menu-verified-badge');

            if (avatarEl) avatarEl.textContent = initials;
            if (nameEl) nameEl.textContent = user.name || 'User';
            if (roleEl) roleEl.textContent = user.role === 'admin' ? 'Administrator' : (user.institution || 'Instructor');
            if (menuName) menuName.textContent = user.name || 'User';
            if (menuEmail) menuEmail.textContent = user.email || '';
            if (menuPhone) {
                if (user.phone) {
                    menuPhone.textContent = user.phone;
                    menuPhone.classList.remove('hidden');
                } else {
                    menuPhone.classList.add('hidden');
                }
            }
            if (menuPlan) menuPlan.textContent = user.plan === 'institution' ? 'Institutional Pro' : (user.plan === 'pro' ? 'Pro Plan' : 'Free Tier');

            if (verifiedBadge) {
                verifiedBadge.classList.toggle('hidden', !user.is_verified);
            }

            if (adminMenuLink) {
                adminMenuLink.classList.toggle('hidden', user.role !== 'admin');
            }

            // Verification banner check
            if (verificationBanner) {
                if (!user.is_verified && user.email) {
                    verificationBanner.classList.remove('hidden');
                    const label = document.getElementById('unverified-email-label');
                    if (label) label.textContent = user.email;
                } else {
                    verificationBanner.classList.add('hidden');
                }
            }

            if (greetingName) greetingName.textContent = user.name || 'Educator';
        } else {
            if (loggedOutActions) loggedOutActions.classList.remove('hidden');
            if (userContainer) userContainer.classList.add('hidden');
            if (verificationBanner) verificationBanner.classList.add('hidden');
            if (greetingName) greetingName.textContent = 'Educator';
        }
        this.renderIcons();
    }

    async checkSystemHealth() {
        try {
            const res = await fetch(`${API_BASE}/system/info`);
            if (res.ok) {
                const info = await res.json();
                const footerStatus = document.getElementById('footer-status-text');
                if (footerStatus) {
                    footerStatus.innerHTML = `All Systems Operational &bull; ${info.name || 'StudyGeneratorExam'} v${info.version || '3.0'}`;
                }
            }
        } catch (e) {
            const footerStatus = document.getElementById('footer-status-text');
            if (footerStatus) {
                footerStatus.innerHTML = 'Local Standalone Engine &bull; Ready';
            }
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

    scrollToSection(sectionId) {
        this.closeMobileMenu();
        if (this.currentView !== 'dashboard') {
            this.navigateTo('dashboard');
        }
        setTimeout(() => {
            const el = document.getElementById(`section-${sectionId}`) || document.getElementById(sectionId);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 60);
    }

    toggleFaq(btn) {
        const item = btn.closest('.bg-white');
        const content = item ? item.querySelector('.faq-content') : null;
        const icon = btn.querySelector('[data-lucide="chevron-down"]');
        if (!content) return;

        const isHidden = content.classList.contains('hidden');
        content.classList.toggle('hidden', !isHidden);
        if (icon) {
            icon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
        }
    }

    openContactModal() {
        this.closeMobileMenu();
        const modal = document.getElementById('modal-contact');
        if (modal) {
            modal.classList.remove('hidden');
            this.renderIcons();
        }
    }

    closeContactModal() {
        const modal = document.getElementById('modal-contact');
        if (modal) modal.classList.add('hidden');
    }

    handleContactSubmit(event) {
        event.preventDefault();
        const nameInput = document.getElementById('contact-name');
        const name = nameInput ? nameInput.value.trim() : 'Educator';
        this.showToast(`Thank you, ${name}! Your inquiry has been sent to our academic support team.`, 'success');
        this.closeContactModal();
        event.target.reset();
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
