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
sudo systemctl status avahi-daemon --no-pager -l

# Install Python zeroconf if not already installed
echo "4. Installing/updating Python zeroconf..."
pip install --upgrade zeroconf

# Configure avahi for better compatibility
echo "5. Configuring avahi-daemon..."
sudo tee /etc/avahi/avahi-daemon.conf > /dev/null <<'EOF'
[server]
use-ipv4=yes
use-ipv6=yes
enable-wide-area=yes
enable-reflector=no
check-response-ttl=no
use-iff-running=no

[publish]
publish-addresses=yes
publish-hinfo=yes
publish-workstation=yes
publish-domain=yes
add-service-cookie=yes

[reflector]
enable-reflector=no

[users]
safe-to-reload

[wide-area]
enable-wide-area=yes
EOF

# Restart avahi-daemon with new config
echo "6. Restarting avahi-daemon with new config..."
sudo systemctl restart avahi-daemon

echo ""
echo "============================================"
echo "✓ mDNS setup complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Start your music server:"
echo "   python app.py"
echo ""
echo "2. On your Android phone:"
echo "   - Open browser"
echo "   - Try: http://cubie.local:5000"
echo "   - If that doesn't work, use the IP address shown on the Pi"
echo ""
echo "3. To check mDNS is working on Pi:"
echo "   avahi-browse -a -t"
echo ""
echo "4. For Android troubleshooting:"
echo "   - Install 'Network Analyzer' app to find the Pi"
echo "   - Or check your router's admin page for device list"
echo ""
