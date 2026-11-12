#!/usr/bin/env bash
# ============================================================
# PennyWise — Local Development Launcher
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "💰 PennyWise — Smart Personal Finance & Wealth Tracker"
echo "============================================================"

# 1. Activate Virtual Environment
if [ -d ".venv" ]; then
    echo "⚙️  Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "⚙️  Activating virtual environment (venv)..."
    source venv/bin/activate
else
    echo "❌ No virtual environment found. Run: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

# 2. Check for .env file
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "⚠️  No .env file found. Copying .env.example to .env..."
    cp .env.example .env
fi

# 3. Environment flags
export FLASK_APP="app:create_app('development')"
export FLASK_DEBUG="1"
export PYTHONUNBUFFERED="1"

PORT=5001

echo "🚀 Starting PennyWise local server on http://127.0.0.1:${PORT}"
echo "   Demo Account: demo@pennywise.app / demo1234"
echo "   Press Ctrl+C to stop the server."
echo "============================================================"

exec python3 -m flask run --host=127.0.0.1 --port=${PORT}
