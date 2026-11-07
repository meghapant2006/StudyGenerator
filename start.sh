#!/usr/bin/env bash
# StudyWise AI Exam Generator - Quick Start Script for Linux / macOS

echo "====================================="
echo "  StudyWise AI Exam Generator"
echo "  Modeled after exam-generator.com"
echo "====================================="
echo ""

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

echo "✔ Using $($PY_CMD --version)"

# Start Flask backend
cd backend
echo "🚀 Starting server at http://127.0.0.1:5000 ..."
$PY_CMD app.py
