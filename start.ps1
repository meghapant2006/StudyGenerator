# Exam Generator - Quick Start Script
# This script helps you run the application easily

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Exam Generator - Quick Start" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if running from correct directory
if (-not (Test-Path "backend\app.py")) {
    Write-Host "ERROR: Please run this script from the project root directory" -ForegroundColor Red
    Write-Host "Current location: $(Get-Location)" -ForegroundColor Yellow
    pause
    exit
}

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.8+" -ForegroundColor Red
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    pause
    exit
}

# Check if dependencies are installed
Write-Host ""
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$pipList = pip list 2>&1
if ($pipList -match "Flask") {
    Write-Host "✓ Dependencies appear to be installed" -ForegroundColor Green
} else {
    Write-Host "! Dependencies not found. Installing..." -ForegroundColor Yellow
    Write-Host ""
    pip install -r backend\requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
        pause
        exit
    }
}

# Check for API key
Write-Host ""
Write-Host "Checking OpenAI API key..." -ForegroundColor Yellow
if ($env:OPENAI_API_KEY) {
    $keyPreview = $env:OPENAI_API_KEY.Substring(0, [Math]::Min(10, $env:OPENAI_API_KEY.Length)) + "..."
    Write-Host "✓ API key found: $keyPreview" -ForegroundColor Green
} else {
    Write-Host "✗ OPENAI_API_KEY not set" -ForegroundColor Red
    Write-Host ""
    Write-Host "Enter your OpenAI API key (or press Enter to skip):" -ForegroundColor Yellow
    Write-Host "Get your key from: https://platform.openai.com/api-keys" -ForegroundColor Cyan
    $apiKey = Read-Host "API Key"
    
    if ($apiKey) {
        $env:OPENAI_API_KEY = $apiKey
        Write-Host "✓ API key set for this session" -ForegroundColor Green
    } else {
        Write-Host "⚠ Continuing without API key. Question generation will not work." -ForegroundColor Yellow
    }
}

# Check Tesseract (optional)
Write-Host ""
Write-Host "Checking Tesseract OCR (optional for scanned PDFs)..." -ForegroundColor Yellow
try {
    $tesseractVersion = tesseract --version 2>&1
    if ($tesseractVersion -match "tesseract") {
        Write-Host "✓ Tesseract OCR found" -ForegroundColor Green
    }
} catch {
    Write-Host "! Tesseract not found (optional - only needed for scanned PDFs)" -ForegroundColor Yellow
    Write-Host "  Download from: https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Cyan
}

# Start the application
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Starting Application..." -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend server starting on: http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "Open this URL in your browser to use the application" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Change to backend directory and run
Set-Location backend
python app.py
