#!/bin/bash
# Start Music Server in WiFi Hotspot Mode
# Perfect for non-technical users - just connect to WiFi!

echo "🎵 Music Server - WiFi Hotspot Mode"
echo "==================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# Stop conflicting services
echo "Setting up WiFi hotspot..."
systemctl stop hostapd 2>/dev/null
systemctl stop dnsmasq 2>/dev/null

# Create hostapd config
cat > /tmp/hostapd.conf << EOF
interface=wlan0
driver=nl80211
ssid=MusicServer
hw_mode=g
channel=6
wmm_enabled=1
ieee80211n=1
# Improves multicast delivery reliability (mDNS/Bonjour) to WiFi clients
multicast_to_unicast=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=music123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
EOF

# Configure wlan0 with dynamic IP
# We need to know the IP BEFORE creating dnsmasq config
echo "Configuring WiFi interface..."
ip addr flush dev wlan0
ip link set wlan0 up

# Auto-detect IP or use default
# Check if there's already an IP on wlan0
EXISTING_IP=$(ip addr show wlan0 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d/ -f1 | head -1)

if [ -z "$EXISTING_IP" ]; then
    # No existing IP, use 192.168.10.1 (standard)
    HOST_IP="192.168.10.1"
    ip addr add $HOST_IP/24 dev wlan0
    echo "Using default IP: $HOST_IP"
else
    # Use existing IP
    HOST_IP="$EXISTING_IP"
    echo "Using existing IP: $HOST_IP"
fi

# Derive DHCP range from HOST_IP
# Replace last octet with 0 to get network
NETWORK_BASE=$(echo $HOST_IP | cut -d. -f1-3)
DHCP_RANGE="${NETWORK_BASE}.10,${NETWORK_BASE}.100"

# Create dnsmasq config with local DNS for Android compatibility
# This helps Android resolve "cubie" even if mDNS fails
cat > /tmp/dnsmasq.conf << EOF
interface=wlan0
dhcp-range=$DHCP_RANGE,255.255.255.0,12h
dhcp-option=3,$HOST_IP
dhcp-option=6,$HOST_IP
log-queries
log-dhcp
listen-address=$HOST_IP,127.0.0.1

# Local DNS entries for Android compatibility
# These resolve "cubie" and "cubie.local" to the Pi's IP
# Android will resolve cubie through the Pi's DNS server
address=/cubie/$HOST_IP
address=/cubie.local/$HOST_IP
address=/music-server/$HOST_IP
address=/music-server.local/$HOST_IP
EOF

echo "dnsmasq configured with:"
echo "  Host IP: $HOST_IP"
echo "  DHCP Range: $DHCP_RANGE"

# Start dnsmasq
echo "Starting DNS/DHCP server..."
dnsmasq -C /tmp/dnsmasq.conf -d &
DNSMASQ_PID=$!

# Start hostapd
echo "Starting WiFi access point..."
hostapd -B /tmp/hostapd.conf -f /tmp/hostapd.log
HOSTAPD_PID=$!

# Wait a moment for network to establish
sleep 2

echo ""
echo "✅ WiFi Hotspot Active!"
echo "==================================="
echo ""
echo "📱 For Users:"
echo "   1. Connect to WiFi: 'MusicServer'"
echo "   2. Password: 'music123'"
echo "   3. Browser opens automatically"
echo "   OR visit: http://$HOST_IP:5000"
echo ""
echo "==================================="
echo ""

# Start music server
echo "Starting music server..."
cd "$(dirname "$0")/.."
python app.py &
SERVER_PID=$!

# Wait for server
sleep 3

echo "✅ Music server is running!"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Trap Ctrl+C and cleanup
trap "echo ''; echo 'Stopping services...'; kill $SERVER_PID $DNSMASQ_PID $HOSTAPD_PID 2>/dev/null; systemctl start NetworkManager 2>/dev/null; exit" INT

# Keep script running
wait
