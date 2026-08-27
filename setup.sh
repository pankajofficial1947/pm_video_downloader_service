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
echo "(ffmpeg comes bundled via the imageio-ffmpeg package - no"
echo " separate system install needed.)"

pip install -r requirements.txt

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
echo "    streamlit run src/app.py"
echo ""
echo "Then open http://localhost:8501 in your browser."
echo ""
echo "Happy Coding!"
echo ""
