# Quick Setup Guide

## Prerequisites

### 1. Install Python 3.8+
Download from: https://www.python.org/downloads/

### 2. Install Tesseract OCR
**Windows:**
- Download installer: https://github.com/UB-Mannheim/tesseract/wiki
- Default install path: C:\Program Files\Tesseract-OCR
- Add to PATH if not automatic

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### 3. Get OpenAI API Key
1. Go to https://platform.openai.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (you'll need it next)

## Installation Steps

### Step 1: Install Python Dependencies
Open PowerShell in the project folder:
```powershell
cd backend
pip install -r requirements.txt
```

### Step 2: Configure API Key
Set your OpenAI API key as an environment variable:

**PowerShell:**
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
```

**Command Prompt:**
```cmd
set OPENAI_API_KEY=your-api-key-here
```

**Or create a .env file:**
Copy `.env.example` to `.env` and add your key:
```
OPENAI_API_KEY=your-api-key-here
```

### Step 3: Run the Application
```powershell
cd backend
python app.py
```

You should see:
```
Starting exam generator API on 127.0.0.1:5000
```

### Step 4: Open in Browser
Open your web browser and go to:
```
http://127.0.0.1:5000
```

## Usage

1. **Upload PDF**: Click to upload your academic PDF document
2. **Configure**: Choose number of questions (1-50) and difficulty
3. **Generate**: Wait for AI to create your exam (takes 10-30 seconds)
4. **Take Exam**: Answer all questions
5. **Submit**: View your score and detailed explanations
6. **Review**: Check past attempts and learn from mistakes

## Troubleshooting

### "OPENAI_API_KEY not set"
- Make sure you set the environment variable before running the app
- Restart your terminal after setting the variable
- Check spelling: OPENAI_API_KEY (all caps)

### "Tesseract not found"
- Install Tesseract OCR (see prerequisites)
- On Windows, add to PATH: C:\Program Files\Tesseract-OCR

### "Module not found"
- Run: `pip install -r requirements.txt`
- Make sure you're in the backend folder

### Port 5000 already in use
Edit `backend/config.py` and change:
```python
FLASK_PORT = 5001  # or any other available port
```

## Next Steps

### Desktop App (Electron)
To package as a desktop application:
1. Install Node.js
2. Install Electron: `npm install -g electron`
3. Create electron wrapper (instructions in future update)

### Mobile Support
- Backend is already API-based
- Can create React Native or Flutter frontend
- Backend runs on local server or deploy to cloud

## Tips

- Start with 5-10 questions for testing
- Medium difficulty works best for most content
- OCR works but may have errors on complex documents
- Questions are saved - you can review later
- Each generation costs API tokens (check OpenAI pricing)

## Support

For issues, check:
1. All prerequisites installed?
2. API key set correctly?
3. Backend server running?
4. Browser console for errors (F12)
