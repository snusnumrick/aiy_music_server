#!/bin/bash

# AIY Music Server - Setup Script for Raspberry Pi Zero
# This script automates the initial setup process

set -e

echo "=================================================="
echo "  AIY Music Server - Setup Script"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
echo "Checking system..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Install with: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓${NC} Python version: $PYTHON_VERSION"

# Check Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    PI_MODEL=$(cat /proc/device-tree/model)
    echo -e "${GREEN}✓${NC} Detected: $PI_MODEL"
else
    echo -e "${YELLOW}⚠${NC} Not a Raspberry Pi (or model not detected)"
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "music_server" ]; then
    python3 -m venv music_server
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${YELLOW}⚠${NC} Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source music_server/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed"

# Create music directory
echo ""
echo "Setting up music directory..."
mkdir -p music
echo -e "${GREEN}✓${NC} Music directory ready"

# Create test MP3 files
echo ""
read -p "Create test MP3 files? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating test files..."
    python3 create_test_music.py
    echo -e "${GREEN}✓${NC} Test files created"
fi

# Systemd service setup
echo ""
read -p "Setup systemd service? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Setting up systemd service..."

    # Check if running as root or with sudo
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}⚠${NC} This script requires sudo for systemd setup"
        echo "Run: sudo cp music-server.service /etc/systemd/system/"
        echo "Then: sudo systemctl daemon-reload"
        echo "And: sudo systemctl enable music-server"
    else
        cp music-server.service /etc/systemd/system/
        sed -i 's|/home/pi/music_server|'$(pwd)'|g' /etc/systemd/system/music-server.service
        systemctl daemon-reload
        systemctl enable music-server
        echo -e "${GREEN}✓${NC} Systemd service installed and enabled"
        echo "Start with: sudo systemctl start music-server"
    fi
fi

echo ""
echo "=================================================="
echo -e "${GREEN}  Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Start the server:"
echo "     source music_server/bin/activate"
echo "     python app.py"
echo ""
echo "  2. Or start as service:"
echo "     sudo systemctl start music-server"
echo ""
echo "  3. Access from your phone:"
echo "     Easy way: http://cubie-server.local:5001"
echo "     Manual: http://[YOUR_IP]:5001"
echo ""
echo "  4. Add MP3 files:"
echo "     Copy files to: $(pwd)/music/"
echo ""
echo "  5. Troubleshooting:"
echo "     mDNS issues: See MDNS_TROUBLESHOOTING.md"
echo "     Full docs: README.md"
echo "=================================================="
