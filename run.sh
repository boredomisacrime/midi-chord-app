#!/bin/bash
cd "$(dirname "$0")"

# Create a virtual environment on first run
if [ ! -d ".venv" ]; then
  echo ""
  echo "  First-time setup: creating a virtual environment..."
  python3 -m venv .venv
fi

# Activate it
source .venv/bin/activate

echo ""
echo "  Installing dependencies (only needed the first time)..."
pip install -r requirements.txt -q

echo ""
echo "  Starting MIDI Chord Helper..."
echo "  Open this in your browser → http://localhost:5001"
echo ""
python app.py
