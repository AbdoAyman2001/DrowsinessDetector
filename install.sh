#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

echo "=== Drowsiness Detector Setup ==="

# Create venv with system site-packages (for picamera2, pygame, numpy)
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment with system site-packages..."
    python3 -m venv --system-site-packages "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# Activate and install
source "$VENV_DIR/bin/activate"
echo "Installing dependencies (dlib compilation may take 10-20 min on RPi)..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

# Download shape predictor model if not present
MODEL_FILE="$SCRIPT_DIR/shape_predictor_68_face_landmarks.dat"
if [ ! -f "$MODEL_FILE" ]; then
    echo "Downloading dlib shape predictor model..."
    wget -q -O "$MODEL_FILE.bz2" "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
    bunzip2 "$MODEL_FILE.bz2"
    echo "Model downloaded."
else
    echo "Shape predictor model already exists."
fi

echo ""
echo "=== Setup complete ==="
echo "Activate with: source $VENV_DIR/bin/activate"
echo "Run with:      python3 $SCRIPT_DIR/main.py"
