#!/bin/bash
# Test connectivity to the music server from different methods

echo "=========================================="
echo "Music Server Connectivity Test"
echo "=========================================="
echo ""

# Get the server's IP
IP=$(hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)

# Try to detect the port from running processes
PORT=$(netstat -tlnp 2>/dev/null | grep python | grep -E ':(5000|5001|5002|8080)' | head -1 | awk '{print $4}' | rev | cut -d: -f1 | rev)
if [ -z "$PORT" ]; then
    PORT="5000"  # Default
fi

echo "Server Information:"
echo "  IP Address: $IP"
echo "  Hostname: $HOSTNAME"
echo "  Port: $PORT"
echo ""

echo "Testing different access methods:"
echo ""

# Test 1: Direct IP
echo "1. Testing direct IP access..."
if curl -s --connect-timeout 3 http://$IP:$PORT/api/health > /dev/null 2>&1; then
    echo "   ✓ SUCCESS: http://$IP:$PORT"
else
    echo "   ✗ FAILED: http://$IP:$PORT"
fi

# Test 2: Local hostname (.local)
echo "2. Testing .local hostname..."
if curl -s --connect-timeout 3 http://$HOSTNAME.local:$PORT/api/health > /dev/null 2>&1; then
    echo "   ✓ SUCCESS: http://$HOSTNAME.local:$PORT"
else
    echo "   ✗ FAILED: http://$HOSTNAME.local:$PORT"
fi

# Test 3: Android bare hostname (auto-appends .local)
echo "3. Testing Android bare hostname..."
if curl -s --connect-timeout 3 http://$HOSTNAME:$PORT/api/health > /dev/null 2>&1; then
    echo "   ✓ SUCCESS: http://$HOSTNAME:$PORT (works for Android!)"
else
    echo "   ✗ FAILED: http://$HOSTNAME:$PORT"
fi

# Test 4: Check if avahi-browse can see the service
echo ""
echo "4. Checking mDNS service visibility..."
if command -v avahi-browse &> /dev/null; then
    echo "   Running: avahi-browse -a -t | grep $HOSTNAME"
    avahi-browse -a -t 2>/dev/null | grep -i "music\|$HOSTNAME" || echo "   Service not visible via avahi-browse"
else
    echo "   avahi-browse not installed"
fi

echo ""
echo "=========================================="
echo "Troubleshooting Tips:"
echo "=========================================="
echo ""
echo "📱 For Android Users:"
echo "   Try: http://$HOSTNAME:$PORT"
echo "   (Android auto-appends .local)"
echo ""
echo "🖥️  For Desktop/Mac Users:"
echo "   Try: http://$HOSTNAME.local:$PORT"
echo ""
echo "If your phone can't see the service:"
echo ""
echo "1. **Run Android mDNS Setup** (Recommended)"
echo "   sudo ./setup_android_mdns.sh"
echo ""
echo "2. **Use IP Address Directly** (Most Reliable)"
echo "   On your phone, visit: http://$IP:$PORT"
echo ""
echo "3. **Check Network Isolation**"
echo "   Some routers have 'AP Isolation' or 'Client Isolation'."
echo "   Disable it to allow devices to see each other."
echo ""
echo "4. **Network Analyzer App**"
echo "   Install 'Network Analyzer' on your phone"
echo "   Find device named '$HOSTNAME' and tap it"
echo ""
echo "5. **Check Router Admin Page**"
echo "   Look for connected devices and find your Pi"
echo ""
echo "6. **QR Code for Easy Access**"
echo "   If qrencode is installed, scan the QR code shown on server start"
echo ""
echo "=========================================="

