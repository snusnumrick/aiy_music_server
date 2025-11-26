#!/bin/bash

# AIY Music Server - Setup Script for Raspberry Pi Zero
# This script automates the initial setup process

set -e

echo "=================================================="
echo "  AIY Music Server - Setup Script"
echo "=================================================="
echo ""

# Define variables
SERVICE_NAME="aiy-server"
SERVICE_DESCRIPTION="AIY Server (mDNS: aiy-server.local)"
USER=$(whoami)
GROUP=$(id -gn)
WORKING_DIR="$(dirname "$(readlink -f "$0")")"

# Check for sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo"
    exit 1
fi

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

    # Create the service file content
    cat << EOF > "${SERVICE_NAME}.service"
[Unit]
Description=${SERVICE_DESCRIPTION}
Documentation=https://github.com/snusnumrick/aiy_media_server
After=network.target network-online.target
Wants=network-online.target
Requires=network-online.target

[Service]
Type=simple
User=${SUDO_USER}
Group=$(id -gn ${SUDO_USER})
Environment="PATH=${WORKING_DIR}/music_server/bin:/home/${SUDO_USER}/.pyenv/shims:/home/${SUDO_USER}/.pyenv/bin:/home/${SUDO_USER}/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="HOME=/home/${SUDO_USER}"
WorkingDirectory=${WORKING_DIR}
ExecStartPre=/bin/sleep 10
ExecStart=/bin/bash -c "${SCRIPTS_DIR}/run.sh"
ExecStart=${WORKING_DIR}/music_server/bin/python ${WORKING_DIR}/app.py

# Reload handler
ExecReload=/bin/kill -HUP $MAINPID

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

    # Create logrotate configuration
    cat << EOF > "${SERVICE_NAME}-logrotate"
    ${LOGS_DIR}/*.log {
        daily
        rotate 5
        compress
        delaycompress
        missingok
        notifempty
        create 0644 ${SUDO_USER} $(id -gn ${SUDO_USER})
        su ${SUDO_USER} $(id -gn ${SUDO_USER})
        prerotate
            cd ${WORKING_DIR} && ${SCRIPTS_DIR}/check_logs.sh
        endscript
    }
    EOF

    # Move the logrotate configuration to the correct location
    mv "${SERVICE_NAME}-logrotate" /etc/logrotate.d/${SERVICE_NAME}

    # Set correct permissions for the logrotate configuration
    chmod 644 /etc/logrotate.d/${SERVICE_NAME}

    # Reload systemd to recognize the new service
    systemctl daemon-reload

    # Enable the service to start on boot
    systemctl enable "${SERVICE_NAME}.service"

    # Start the service
    systemctl start "${SERVICE_NAME}.service"

    echo "Service ${SERVICE_NAME} has been created, enabled, and started."
    echo "Logrotate configuration for ${SERVICE_NAME} has been set up."
    echo "Check status with: sudo systemctl status ${SERVICE_NAME}"
    echo "View logs with: sudo journalctl -u ${SERVICE_NAME} -f"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}  Setup Complete!${NC}"
echo "=================================================="
echo "
echo "  Access from your phone: http://${SERVICE_NAME}.local:5001"
echo "=================================================="
