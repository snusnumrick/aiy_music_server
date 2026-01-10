#!/bin/bash
# Install autohotspot with AIY Music Server integration
# This script installs the modified autohotspot that includes:
# - Dynamic IP detection
# - Enhanced mDNS for Android
# - Music server integration

echo "============================================"
echo "  Installing Autohotspot for AIY Music Server"
echo "============================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}This will install autohotspot with AIY Music Server integration:${NC}"
echo "✓ Dynamic IP detection (works with any subnet)"
echo "✓ Enhanced mDNS for Android compatibility"
echo "✓ Automatic music server start/stop"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

echo "Installing autohotspot..."
echo ""

# Step 1: Copy autohotspot script
echo -e "${YELLOW}Step 1:${NC} Installing autohotspotN script..."
if [ -f "${PROJECT_ROOT}/autohotspot/autohotspotN" ]; then
    cp "${PROJECT_ROOT}/autohotspot/autohotspotN" /usr/bin/autohotspotN
    chmod +x /usr/bin/autohotspotN
    echo -e "${GREEN}✓${NC} autohotspotN installed to /usr/bin/"
else
    echo -e "${RED}✗${NC} autohotspotN not found!"
    exit 1
fi

# Step 2: Copy systemd service
echo ""
echo -e "${YELLOW}Step 2:${NC} Installing systemd service..."
if [ -f "${PROJECT_ROOT}/autohotspot/autohotspot.service" ]; then
    cp "${PROJECT_ROOT}/autohotspot/autohotspot.service" /etc/systemd/system/
    echo -e "${GREEN}✓${NC} Service file installed"
else
    echo -e "${RED}✗${NC} Service file not found!"
    exit 1
fi

# Step 3: Configure wpa_supplicant if needed
echo ""
echo -e "${YELLOW}Step 3:${NC} Checking WiFi configuration..."

if [ -f "/etc/wpa_supplicant/wpa_supplicant.conf" ]; then
    CONFIGURED_SSIDS=$(grep 'ssid=' /etc/wpa_supplicant/wpa_supplicant.conf | wc -l)
    if [ $CONFIGURED_SSIDS -gt 0 ]; then
        echo -e "${GREEN}✓${NC} Found $CONFIGURED_SSIDS configured SSID(s)"
        echo "  Configured networks:"
        grep 'ssid=' /etc/wpa_supplicant/wpa_supplicant.conf | sed 's/^/    /'
    else
        echo -e "${YELLOW}⚠${NC} No SSIDs configured in wpa_supplicant.conf"
        echo "  Add your WiFi networks to /etc/wpa_supplicant/wpa_supplicant.conf"
        echo "  Example:"
        echo "    network={"
        echo "        ssid=\"YourWiFiName\""
        echo "        psk=\"YourPassword\""
        echo "    }"
    fi
else
    echo -e "${RED}✗${NC} wpa_supplicant.conf not found!"
    echo "  Please configure WiFi first"
fi

# Step 4: Reload systemd
echo ""
echo -e "${YELLOW}Step 4:${NC} Reloading systemd daemon..."
systemctl daemon-reload
echo -e "${GREEN}✓${NC} Systemd daemon reloaded"

# Step 5: Enable autohotspot
echo ""
echo -e "${YELLOW}Step 5:${NC} Enabling autohotspot service..."
systemctl enable autohotspot
echo -e "${GREEN}✓${NC} Autohotspot enabled"

# Step 6: Ask user if they want to start now
echo ""
echo -e "${YELLOW}Step 6:${NC} Installation complete!"
echo ""

read -p "Do you want to start autohotspot now? (y/n) " -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting autohotspot service..."
    systemctl start autohotspot

    # Wait a moment for service to initialize
    sleep 3

    echo ""
    echo -e "${GREEN}✓${NC} Autohotspot started!"
    echo ""

    # Check status
    if systemctl is-active --quiet autohotspot; then
        echo -e "${GREEN}✓${NC} Service is running"
    else
        echo -e "${YELLOW}⚠${NC} Service may still be initializing"
    fi

    # Show recent logs
    echo ""
    echo "Recent logs:"
    journalctl -u autohotspot -n 10 --no-pager
else
    echo "To start later, run:"
    echo "  sudo systemctl start autohotspot"
fi

echo ""
echo "============================================"
echo -e "${GREEN}  Installation Complete!${NC}"
echo "============================================"
echo ""
echo "Autohotspot will now:"
echo "• Monitor for configured WiFi networks"
echo "• Connect to WiFi when available"
echo "• Create hotspot when WiFi is not in range"
echo "• Automatically start/stop music server"
echo ""
echo "Configuration:"
echo "• WiFi networks: /etc/wpa_supplicant/wpa_supplicant.conf"
echo "• Service: sudo systemctl status autohotspot"
echo "• Logs: sudo journalctl -u autohotspot -f"
echo ""
echo "Test the installation:"
echo "1. Ensure WiFi is configured in wpa_supplicant.conf"
echo "2. Reboot the Pi or run: sudo systemctl restart autohotspot"
echo "3. Check logs: sudo journalctl -u autohotspot -f"
echo ""
echo "Android Access:"
echo "• WiFi mode: http://cubie.local:5000"
echo "• Hotspot mode: http://cubie:5000"
echo ""
