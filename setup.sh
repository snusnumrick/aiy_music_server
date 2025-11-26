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
    echo ""
    echo "Choose your installation type:"
    echo "  1) Default: For user 'pi' (standard Raspberry Pi setup)"
    echo "  2) Custom: For any username (e.g., 'bob', 'alex', etc.)"
    read -p "Select option (1 or 2): " -n 1 -r
    echo ""

    # Check if running as root or with sudo
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}⚠${NC} This script requires sudo for systemd setup"
        echo ""
        if [[ $REPLY =~ ^[1]$ ]]; then
            echo "Run these commands for default 'pi' user:"
            echo "  sudo cp music-server.service /etc/systemd/system/"
            echo "  sudo systemctl daemon-reload"
            echo "  sudo systemctl enable music-server"
            echo "  sudo systemctl start music-server"
        else
            echo "Run these commands for custom username:"
            echo "  sudo cp music-server@.service /etc/systemd/system/"
            echo "  sudo systemctl daemon-reload"
            echo "  sudo systemctl enable music-server@YOUR_USERNAME"
            echo "  sudo systemctl start music-server@YOUR_USERNAME"
        fi
        echo ""
    else
        # Running as root - handle service installation properly
        if [[ $REPLY =~ ^[1]$ ]]; then
            TARGET_USER="pi"
            echo "Installing service for user: $TARGET_USER"

            # Check if target user exists
            if ! id "$TARGET_USER" &>/dev/null; then
                echo -e "${RED}Error: User '$TARGET_USER' does not exist${NC}"
                echo "Please create the user first or choose option 2 for a custom username"
                exit 1
            fi

            # Get target user's home directory
            TARGET_HOME=$(getent passwd $TARGET_USER | cut -d: -f6)

            # Check if music_server directory exists for this user
            if [ ! -d "$TARGET_HOME/music_server" ]; then
                echo -e "${YELLOW}⚠${NC} Music server not found in $TARGET_HOME/music_server"
                echo "Current directory: $(pwd)"
                echo "Should the service use: $(pwd)/music_server ?"
                read -p "Continue? (y/n) " -n 1 -r
                echo ""
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    exit 1
                fi
            fi

            cp music-server.service /etc/systemd/system/
            systemctl daemon-reload
            systemctl enable music-server
            systemctl start music-server

            echo -e "${GREEN}✓${NC} Systemd service installed and enabled for user '$TARGET_USER'"
            echo "Service is running as user: $(systemctl show -p MainPID music-server | cut -d= -f2)"
            echo ""
            echo "Check status with: sudo systemctl status music-server"
            echo "View logs with: sudo journalctl -u music-server -f"
        else
            read -p "Enter username to run service as: " username
            if [ ! -z "$username" ]; then
                echo "Installing service for user: $username"

                # Check if target user exists
                if ! id "$username" &>/dev/null; then
                    echo -e "${RED}Error: User '$username' does not exist${NC}"
                    echo "Create the user first, then re-run this script"
                    exit 1
                fi

                # Get target user's home directory
                TARGET_HOME=$(getent passwd $username | cut -d: -f6)

                # Check if music_server directory exists for this user
                if [ ! -d "$TARGET_HOME/music_server" ]; then
                    echo -e "${YELLOW}⚠${NC} Music server not found in $TARGET_HOME/music_server"
                    echo "Current directory: $(pwd)"
                    echo "Should the service use: $(pwd)/music_server ?"
                    read -p "Continue? (y/n) " -n 1 -r
                    echo ""
                    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                        exit 1
                    fi
                fi

                cp music-server@.service /etc/systemd/system/
                systemctl daemon-reload
                systemctl enable music-server@$username
                systemctl start music-server@$username

                echo -e "${GREEN}✓${NC} Systemd service installed and enabled for user '$username'"
                echo "Service is running as user: $(systemctl show -p MainPID music-server@$username | cut -d= -f2)"
                echo ""
                echo "Check status with: sudo systemctl status music-server@$username"
                echo "View logs with: sudo journalctl -u music-server@$username -f"
            fi
        fi
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
