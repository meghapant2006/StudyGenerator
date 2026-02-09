# Development Guide

## Architecture Overview

The Exam Generator follows a modular, clean architecture:

```
┌─────────────┐
│   Browser   │ ← User Interface (HTML/CSS/JS)
└──────┬──────┘
       │ HTTP/REST
┌──────▼──────────────────────────────────┐
│         Flask Backend API               │
│  ┌────────────────────────────────┐    │
│  │  app.py - Routes & Controllers │    │
│  └────────────────────────────────┘    │
│          ▲      ▲       ▲      ▲       │
│          │      │       │      │       │
│  ┌───────┴───┐  │  ┌───┴────┐ │       │
│  │pdf_       │  │  │ai_     │ │       │
│  │extractor  │  │  │generator│ │       │
│  └───────────┘  │  └────────┘ │       │
│                 │              │       │
│          ┌──────┴─────┐  ┌────▼────┐  │
│          │  models.py  │  │database │  │
│          │  (Data)     │  │(SQLite) │  │
│          └────────────┘  └─────────┘  │
└─────────────────────────────────────────┘
```

## Module Breakdown

### 1. config.py
- Central configuration
- Environment variables
- File paths and constants
- Easily customizable settings

### 2. models.py
- Data structures using `@dataclass`
- Clean serialization with `to_dict()` and `from_dict()`
- Type hints for better IDE support
- Validation logic

### 3. pdf_extractor.py
**Key Features:**
- PyMuPDF for fast PDF processing
- Automatic OCR fallback for scanned pages
- Context manager for resource management
- Text extraction with page mapping
- Section detection heuristics

**How it works:**
1. Opens PDF with PyMuPDF
2. Tries to extract text directly
3. If text is sparse (<50 chars), triggers OCR
4. Returns page-wise text dictionary

**Extending:**
- Add table extraction: Use `page.find_tables()`
- Better section detection: Use NLP for heading classification
- Language support: Modify `OCR_LANGUAGE` in config

### 4. ai_generator.py
**Key Features:**
- OpenAI GPT integration (swappable)
- Structured JSON output
- Automatic validation of questions
- Regeneration capability

**How it works:**
1. Prepares content summary (max 4000 chars)
2. Constructs detailed prompt with requirements
3. Calls AI API with JSON response format
4. Validates: 4 answers, 1 correct answer
5. Returns Question objects

**Extending:**
- Add other AI providers (Anthropic, Cohere):
  ```python
  if provider == "anthropic":
      # Use Anthropic API
  elif provider == "openai":
      # Use OpenAI API
  ```
- Add question type variations (true/false, fill-in-blank)
- Implement difficulty calibration

### 5. database.py
**Key Features:**
- SQLite for zero-config storage
- Foreign key constraints
- JSON serialization for complex fields
- Context manager for connections

**Schema:**
```
pdfs
├─ id (PK)
├─ filename
├─ upload_date
└─ ...

exams
├─ id (PK)
├─ pdf_id (FK)
├─ title
└─ ...

questions
├─ id (PK)
├─ exam_id (FK)
├─ question_text
├─ answers (JSON)
└─ ...

exam_attempts
├─ id (PK)
├─ exam_id (FK)
├─ answers (JSON)
├─ score
└─ ...
```

**Extending:**
- Add user accounts table
- Track question analytics (difficulty, success rate)
- Add tags/categories for questions

### 6. app.py
**Flask Routes:**
- `POST /api/upload` - Upload PDF
- `POST /api/generate-exam` - Generate questions
- `GET /api/exam/<id>` - Get exam details
- `POST /api/submit-attempt` - Submit answers
- `GET /api/attempts/<exam_id>` - Get past attempts

**Extending:**
- Add authentication middleware
- Implement rate limiting
- Add WebSocket for real-time updates
- Create admin panel

### 7. Frontend (app.js)
**State Management:**
- `currentPdf` - Uploaded PDF metadata
- `currentExam` - Generated exam data
- `userAnswers` - User's selections
- `examStartTime` - For timing

**Flow:**
1. Upload → API call → Display PDF info
2. Configure → API call → Generate exam
3. Display questions → User answers
4. Submit → API call → Show results

**Extending:**
- Add drag-and-drop for files
- Implement keyboard navigation
- Add progress saving (localStorage)
- Create mobile-responsive design

## Adding New Features

### Example 1: Add True/False Questions

**1. Update models.py:**
```python
@dataclass
class Question:
    question_type: str = "multiple_choice"  # or "true_false"
    # ... rest of fields
```

**2. Update ai_generator.py:**
```python
def generate_questions(self, ..., question_type="multiple_choice"):
    if question_type == "true_false":
        # Modify prompt for yes/no
        # Validate only 2 answers
```

**3. Update frontend:**
```javascript
if (question.question_type === 'true_false') {
    // Render true/false buttons
} else {
    // Render multiple choice
}
```

### Example 2: Add User Authentication

**1. Add users table:**
```python
# In database.py
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password_hash TEXT,
        created_date TEXT
    )
""")
```

**2. Add auth routes:**
```python
# In app.py
@app.route('/api/register', methods=['POST'])
def register():
    # Hash password, save user
    
@app.route('/api/login', methods=['POST'])
def login():
    # Verify credentials, return JWT
```

**3. Protect routes:**
```python
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        # Verify JWT
        return f(*args, **kwargs)
    return decorated

@app.route('/api/generate-exam', methods=['POST'])
@require_auth
def generate_exam():
    # ...
```

### Example 3: Deploy to Desktop with Electron

**1. Install Electron:**
```bash
npm install -g electron
```

**2. Create electron.js:**
```javascript
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');

let flaskProcess;

app.on('ready', () => {
    // Start Flask backend
    flaskProcess = spawn('python', ['backend/app.py']);
    
    // Create window
    const win = new BrowserWindow({
        width: 1200,
        height: 800
    });
    
    // Load frontend
    win.loadURL('http://127.0.0.1:5000');
});

app.on('quit', () => {
    flaskProcess.kill();
});
```

**3. Package:**
```bash
electron-packager . ExamGenerator --platform=win32 --arch=x64
```

## Performance Optimization

### 1. Caching
- PDF content is cached in memory
- Add Redis for distributed caching
- Cache AI responses for similar content

### 2. Async Processing
- Use Celery for background tasks
- Generate questions asynchronously
- Send email when exam ready

### 3. Database
- Add indexes on frequently queried fields
- Use connection pooling
- Consider PostgreSQL for production

## Testing

### Unit Tests
```python
# test_pdf_extractor.py
def test_extract_text():
    with PDFExtractor('test.pdf') as extractor:
        text = extractor.extract_all_text()
        assert len(text) > 0
```

### Integration Tests
```python
# test_api.py
def test_upload_pdf():
    response = client.post('/api/upload', data={'file': ...})
    assert response.status_code == 200
    assert 'pdf' in response.json
```

## Security Best Practices

1. **API Keys:** Never commit to git, use environment variables
2. **File Upload:** Validate file types, scan for malware
3. **SQL Injection:** Use parameterized queries (already done)
4. **CORS:** Configure properly for production
5. **Rate Limiting:** Add to prevent abuse

## Deployment Options

### Local Desktop
✓ Current setup works out of the box
- Package with Electron
- Distribute as installer

### Cloud Deployment
- Deploy Flask to: Heroku, AWS Elastic Beanstalk, Azure
- Use PostgreSQL instead of SQLite
- Serve static files from CDN
- Add HTTPS/SSL

### Mobile Apps
- Keep Flask backend
- Create React Native or Flutter frontend
- Connect to backend API
- Consider offline mode with local storage

## Troubleshooting

### Common Issues

**OCR not working**
- Check Tesseract installation
- Verify PATH includes Tesseract
- Test: `tesseract --version`

**AI generation fails**
- Check API key is valid
- Verify internet connection
- Check OpenAI API status
- Monitor token usage/limits

**Database locked**
- Increase `DB_TIMEOUT` in config
- Use PostgreSQL for concurrent access

## Resources

- **PyMuPDF Docs:** https://pymupdf.readthedocs.io/
- **Flask Docs:** https://flask.palletsprojects.com/
- **OpenAI API:** https://platform.openai.com/docs
- **Electron:** https://www.electronjs.org/docs

## Contributing

To contribute:
1. Fork the repository
2. Create feature branch
3. Write tests for new features
4. Submit pull request

## License

This is a learning project. Feel free to use and modify!
