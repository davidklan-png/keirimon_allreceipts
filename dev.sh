#!/bin/bash
# dev.sh — start frontend and backend for local development

set -e

# Get local IP for sharing with other Macs
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")

echo "────────────────────────────────────────"
echo "  Receipt Capture App — Dev Server"
echo "────────────────────────────────────────"
echo "  Local:    http://localhost:5173"
echo "  Network:  http://$LOCAL_IP:5173"
echo "  API:      http://$LOCAL_IP:8000/docs"
echo "────────────────────────────────────────"

# Start backend
echo "Starting backend..."
cd "$(dirname "$0")/backend"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

if [ ! -f ".env" ]; then
  echo "⚠️  No .env found — copying .env.example"
  cp .env.example .env
  echo "⚠️  Edit backend/.env before continuing."
  exit 1
fi

pip install -r requirements.txt -q

uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend..."
cd ../frontend

if [ ! -d "node_modules" ]; then
  echo "Installing npm dependencies..."
  npm install
fi

npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

# Trap Ctrl+C to kill both
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait
