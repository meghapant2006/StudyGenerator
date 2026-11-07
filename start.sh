#!/usr/bin/env bash
# StudyGenerator Exam - Quick Start & Management Script for Linux / macOS

echo "====================================="
echo "  StudyGenerator Exam Platform"
echo "  AI Assessment & Examination System"
echo "====================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python command
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[ERROR] Python not found. Please install Python 3.8+"
    exit 1
fi

echo "[OK] Using $($PY_CMD --version)"

# Check flags
ACTION="$1"

if [ "$ACTION" = "--test" ]; then
    echo "[INFO] Running automated test suites..."
    echo "--- 1. Authentication & Mobile Login Tests ---"
    $PY_CMD backend/tests/test_auth.py
    echo "--- 2. AI Exam Generator Tests ---"
    $PY_CMD backend/tests/test_generator.py
    exit 0
fi

if [ "$ACTION" = "--stop" ]; then
    echo "[INFO] Stopping any running server instances..."
    pkill -f "python.*app.py" 2>/dev/null || true
    echo "[OK] Server stopped."
    exit 0
fi

if [ "$ACTION" = "--restart" ]; then
    echo "[INFO] Restarting server..."
    pkill -f "python.*app.py" 2>/dev/null || true
    sleep 1
fi

# Check if port 5000 is currently active
PORT_PID=$(lsof -ti:5000 2>/dev/null || fuser 5000/tcp 2>/dev/null || true)
if [ -n "$PORT_PID" ]; then
    echo "[INFO] Port 5000 is already in use (PID: $PORT_PID)."
    echo "[INFO] StudyGenerator Exam is already running at: http://127.0.0.1:5000/"
    echo ""
    echo "Tips:"
    echo "  - Open http://127.0.0.1:5000 in your browser to use the app"
    echo "  - Run './start.sh --restart' to force restart the server"
    echo "  - Run './start.sh --stop' to terminate the server"
    echo "  - Run './start.sh --test' to run all automated tests"
    exit 0
fi

# Start Flask backend
cd backend
echo "[INFO] Starting server at http://127.0.0.1:5000 ..."
$PY_CMD app.py
