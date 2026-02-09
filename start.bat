@echo off
REM Exam Generator - Quick Start Script for Windows Command Prompt

echo =====================================
echo   Exam Generator - Quick Start
echo =====================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b
)
echo [OK] Python found

echo.
echo Checking dependencies...
pip show Flask >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r backend\requirements.txt
)
echo [OK] Dependencies ready

echo.
echo Checking API key...
if "%OPENAI_API_KEY%"=="" (
    echo [WARNING] OPENAI_API_KEY not set
    echo Set it with: set OPENAI_API_KEY=your-key-here
    echo Or enter it now:
    set /p OPENAI_API_KEY="API Key (or press Enter to skip): "
)

if not "%OPENAI_API_KEY%"=="" (
    echo [OK] API key configured
) else (
    echo [WARNING] No API key - generation will not work
)

echo.
echo =====================================
echo   Starting Application...
echo =====================================
echo.
echo Backend server: http://127.0.0.1:5000
echo Open this URL in your browser
echo.
echo Press Ctrl+C to stop the server
echo.

cd backend
python app.py
