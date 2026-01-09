#!/bin/bash
# Setup mDNS for Android compatibility
# Run this once on your Pi

echo "============================================"
echo "Setting up mDNS for Android Compatibility"
echo "============================================"
echo ""

# Update package list
echo "1. Updating packages..."
sudo apt-get update -qq

# Install avahi-daemon (mDNS service)
echo "2. Installing avahi-daemon..."
sudo apt-get install -y avahi-daemon avahi-utils

# Enable and start avahi-daemon
echo "3. Enabling avahi-daemon..."
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
echo -e "\nAvahi-daemon status:"
sudo systemctl status avahi-daemon --no-pager -l

# Install Python zeroconf if not already installed
echo "\n4. Installing/updating Python zeroconf..."
pip install --upgrade zeroconf

# Configure avahi for better compatibility
echo "\n5. Configuring avahi-daemon for Android..."
# Backup original config
if [ ! -f /etc/avahi/avahi-daemon.conf.bak ]; then
    sudo cp /etc/avahi/avahi-daemon.conf /etc/avahi/avahi-daemon.conf.bak
    echo "  ✓ Backed up original config to /etc/avahi/avahi-daemon.conf.bak"
fi

# Create optimized config for Android
sudo tee /etc/avahi/avahi-daemon.conf > /dev/null <<'EOF'
[server]
use-ipv4=yes
use-ipv6=yes
enable-wide-area=yes
enable-reflector=no
check-response-ttl=no
use-iff-running=no
# Hotspot setups sometimes use `ap0`/`uap0` instead of `wlan0`.
allow-interfaces=wlan0,uap0,ap0,wlan1,eth0

[publish]
publish-addresses=yes
publish-hinfo=yes
publish-workstation=yes
publish-domain=yes
add-service-cookie=yes
disable-publishing=no
disable-user-service-publishing=no

[reflector]
enable-reflector=no

[users]
safe-to-reload

[wide-area]
enable-wide-area=yes
EOF

# Restart avahi-daemon with new config
echo "\n6. Restarting avahi-daemon with Android-optimized config..."
sudo systemctl restart avahi-daemon
sleep 2

# Check if hostname is set correctly
HOSTNAME=$(hostname)
echo "\n7. Checking hostname configuration..."
echo "  Current hostname: $HOSTNAME"
echo "  Local domain: ${HOSTNAME}.local"

if [ "$HOSTNAME" = "cubie" ]; then
    echo "  ✓ Hostname is set to 'cubie' - perfect for Android!"
else
    echo "  ⚠ Hostname is '$HOSTNAME'. For Android, use:"
    echo "     http://${HOSTNAME}.local:5000"
fi

echo ""
echo "============================================"
echo -e "${GREEN}✓ mDNS setup complete!${NC}"
echo "============================================"
echo ""
echo "How to Access from Android:"
echo "  1. Ensure phone and Pi are on same WiFi"
echo "  2. On Android, type in browser:"
echo "     ${GREEN}http://cubie:5000${NC}"
echo "     (Android auto-appends .local)"
echo ""
echo "  3. Alternative:"
echo "     http://cubie.local:5000"
echo ""
echo "Verification:"
echo "  - Check services: ${YELLOW}avahi-browse -a -t${NC}"
echo "  - Look for: cubie._http._tcp.local"
echo "               cubie._workstation._tcp.local"
echo ""
echo "If Android can't find it:"
echo "  - Wait 30 seconds for mDNS propagation"
echo "  - Use IP: http://$(hostname -I | awk '{print $1}'):5000"
echo "  - Install 'Network Analyzer' app on Android"
echo ""
