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
SERVICE_DESCRIPTION="AIY Server (mDNS: cubie.local)"

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

# Make scripts executable
SCRIPTS_DIR="${WORKING_DIR}/scripts"
chmod +x "${SCRIPTS_DIR}/run.sh"

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
ExecStart=/bin/bash -c "${SCRIPTS_DIR}/run.sh"

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

# Android mDNS Setup
echo ""
read -p "Setup mDNS for Android compatibility? (recommended for phones) (y/n) " -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running Android mDNS setup..."
    if [ -f "./setup_android_mdns.sh" ]; then
        sudo bash ./setup_android_mdns.sh
        echo ""
        echo -e "${GREEN}✓ Android mDNS setup complete${NC}"
    else
        echo -e "${RED}Error: setup_android_mdns.sh not found${NC}"
    fi
fi

# Captive Portal Setup
echo ""
read -p "Enable Captive Portal (redirects port 80 to music server)? (y/n) " -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Setting up Captive Portal..."
    echo ""

    # Install dependencies
    if ! dpkg -s iptables-persistent >/dev/null 2>&1; then
        echo "Installing iptables-persistent..."
        apt-get update && apt-get install -y iptables-persistent
    fi

    # Enable IP forwarding
    echo "Enabling IP forwarding..."
    echo 1 > /proc/sys/net/ipv4/ip_forward
    sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/g' /etc/sysctl.conf

    # Add initial redirect rule (will be updated after server starts)
    echo "Adding initial iptables redirect rule..."
    iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 5000 2>/dev/null || true

    # Save rules
    echo "Saving iptables rules..."
    iptables-save > /etc/iptables/rules.v4

    echo ""
    echo "✓ Captive Portal configured"
    echo ""
    echo "The server will automatically update the redirect when it starts."
    echo "Users connecting to this Pi's WiFi will be redirected from port 80"
    echo "to the actual server port (auto-detected, usually 5000)."
    echo ""
fi

echo ""
echo "=================================================="
echo -e "${GREEN}  Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "  📱 Android: http://cubie:5000"
echo "  🖥️  Desktop: http://cubie.local:5000"
echo "  🌐 Captive Portal: http://<wifi-ip> (if enabled)"
echo ""
echo "  Server auto-detects port, starting from 5000"
echo "=================================================="