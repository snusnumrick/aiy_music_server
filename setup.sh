#!/bin/bash

# AIY Music Server - Setup Script for Raspberry Pi Zero
# This script automates the initial setup process

set -e

echo "=================================================="
echo "  AIY Music Server - Setup Script"
echo "=================================================="
echo ""

# Define variables
SERVICE_NAME="cubie-server"
SERVICE_DESCRIPTION="AIY Server (mDNS: cubie-server.local)"

# Get the directory where this script is located
WORKING_DIR="$(dirname "$(readlink -f "$0")")"

# Check for sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo"
    exit 1
fi

# Determine the actual user (who ran sudo)
if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
else
    REAL_USER=$(whoami)
fi
REAL_GROUP=$(id -gn "$REAL_USER")

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

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "${WORKING_DIR}/music_server" ]; then
    # Use absolute path for safety
    python3 -m venv "${WORKING_DIR}/music_server"
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${YELLOW}⚠${NC} Virtual environment already exists"
fi

# Install dependencies
echo ""
echo "Installing Python dependencies..."
# direct call to venv pip to ensure correct environment
"${WORKING_DIR}/music_server/bin/pip" install --upgrade pip > /dev/null 2>&1
if [ -f "${WORKING_DIR}/requirements.txt" ]; then
    "${WORKING_DIR}/music_server/bin/pip" install -r "${WORKING_DIR}/requirements.txt"
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${YELLOW}⚠${NC} requirements.txt not found, skipping..."
fi

# Create music directory
echo ""
echo "Setting up music directory..."
mkdir -p "${WORKING_DIR}/music"
chown -R "$REAL_USER:$REAL_GROUP" "${WORKING_DIR}/music"
echo -e "${GREEN}✓${NC} Music directory ready"

# Create test MP3 files
echo ""
# Removed '-n 1' so it waits for Enter
read -p "Create test MP3 files? (y/n) " -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating test files..."
    if [ -f "${WORKING_DIR}/create_test_music.py" ]; then
         "${WORKING_DIR}/music_server/bin/python" "${WORKING_DIR}/create_test_music.py"
         echo -e "${GREEN}✓${NC} Test files created"
    else
         echo -e "${RED}Error: create_test_music.py not found${NC}"
    fi
fi

# Systemd service setup
echo ""
# Removed '-n 1' so it waits for Enter
read -p "Setup systemd service? (y/n) " -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Setting up systemd service..."

    # Create the service file content
    # Note: We escape $MAINPID so it writes literally to the file
    cat << EOF > "${SERVICE_NAME}.service"
[Unit]
Description=${SERVICE_DESCRIPTION}
Documentation=https://github.com/snusnumrick/aiy_media_server
After=network.target network-online.target
Wants=network-online.target
Requires=network-online.target

[Service]
Type=simple
User=${REAL_USER}
Group=${REAL_GROUP}
WorkingDirectory=${WORKING_DIR}

# Main Execution Command
ExecStart=${WORKING_DIR}/music_server/bin/python ${WORKING_DIR}/app.py

# Reload handler
ExecReload=/bin/kill -HUP \$MAINPID

# Restart policy
Restart=on-failure
RestartSec=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

[Install]
WantedBy=multi-user.target
EOF

    # Move the service file to the correct location
    mv "${SERVICE_NAME}.service" /etc/systemd/system/

    # Reload systemd to recognize the new service
    systemctl daemon-reload

    # Enable the service to start on boot
    systemctl enable "${SERVICE_NAME}.service"

    # Start the service
    systemctl restart "${SERVICE_NAME}.service"

    echo "Service ${SERVICE_NAME} has been created, enabled, and started."
    echo "Check status with: sudo systemctl status ${SERVICE_NAME}"
    echo "View logs with: sudo journalctl -u ${SERVICE_NAME} -f"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}  Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "  Access from your phone: http://${SERVICE_NAME}.local:5001"
echo "=================================================="