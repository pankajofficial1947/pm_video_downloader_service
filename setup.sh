#!/bin/bash

###############################################################################
# Video Downloader Service
# Project Setup Script
#
# This script:
#   1. Checks the Python installation
#   2. Creates a virtual environment
#   3. Activates the virtual environment
#   4. Upgrades pip and build tools
#   5. Installs all required packages
#   6. Creates project directories
#   7. Creates a .env file (if missing)
#   8. Checks for ffmpeg (required by yt-dlp to merge/convert media)
#
# Usage:
#     chmod +x setup.sh
#     ./setup.sh
###############################################################################

set -e

echo "====================================================="
echo " Video Downloader Service"
echo " Environment Setup"
echo "====================================================="

###############################################
# Check Python
###############################################

if ! command -v python3 &> /dev/null
then
    echo "ERROR: Python 3 is not installed."
    exit 1
fi

echo "Python found:"
python3 --version

###############################################
# Create Virtual Environment
###############################################

if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo ""
    echo "Virtual environment already exists."
fi

###############################################
# Activate Virtual Environment
###############################################

echo ""
echo "Activating virtual environment..."

source .venv/bin/activate

###############################################
# Upgrade pip
###############################################

echo ""
echo "Upgrading pip..."

python -m pip install --upgrade pip setuptools wheel

###############################################
# Install Requirements
###############################################

echo ""
echo "Installing project dependencies..."

pip install -r requirements.txt

###############################################
# Create Project Directories
###############################################

echo ""
echo "Creating project folders..."

mkdir -p downloads
mkdir -p logs
mkdir -p tests

###############################################
# Create .env
###############################################

if [ ! -f ".env" ]; then

    if [ -f ".env.example" ]; then

        echo ""
        echo "Creating .env file..."

        cp .env.example .env

    else

        echo ""
        echo "Creating blank .env..."

        touch .env

    fi

fi

###############################################
# Check ffmpeg
###############################################

echo ""

if command -v ffmpeg &> /dev/null; then
    echo "ffmpeg found: $(ffmpeg -version | head -n 1)"
else
    echo "WARNING: ffmpeg was not found on PATH."
    echo "yt-dlp needs it to merge separate video/audio streams and to"
    echo "extract audio-only downloads. Install it with:"
    echo "    macOS:   brew install ffmpeg"
    echo "    Ubuntu:  sudo apt install ffmpeg"
    echo "    Windows: https://ffmpeg.org/download.html"
fi

###############################################
# Finished
###############################################

echo ""
echo "====================================================="
echo "Setup Complete!"
echo "====================================================="
echo ""
echo "To activate the environment later, run:"
echo ""
echo "    source .venv/bin/activate"
echo ""
echo "To start the project:"
echo ""
echo "    uvicorn src.app:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Then open http://localhost:8000 in your browser."
echo ""
echo "Happy Coding!"
echo ""
