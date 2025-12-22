# Architecture Overview 🏗️

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi Zero                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐         ┌──────────────────┐               │
│  │   WiFi AP   │◄────────┤  Music Server     │               │
│  │  (hostapd)  │         │   (Flask app)     │               │
│  └─────────────┘         └──────────────────┘               │
│         │                         │                         │
│         │                         │                         │
│  ┌─────────────┐         ┌──────────────────┐               │
│  │   dnsmasq   │         │   iptables       │               │
│  │  (DHCP/DNS) │         │   (Redirect 80)  │               │
│  └─────────────┘         └──────────────────┘               │
│         │                         │                         │
│         └─────────┬───────────────┘                         │
│                   │                                         │
│         ┌─────────▼──────────┐                              │
│         │  Auto-Port Detect  │                              │
│         │  (5000→5001→5002)  │                              │
│         └─────────�───────────┘                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
       ┌──────▼──────┐            ┌──────▼──────┐
       │   Android   │            │   Desktop   │
       │   Phone     │            │   / Mac     │
       └─────────────┘            └─────────────┘
              │                           │
    http://cubie:5000           http://cubie.local:5000
    (auto-append .local)          (explicit .local)
```

## Auto-Port Detection Flow

```
1. Server starts
   │
   ├─► Try port 5000
   │   ├─► Success → Use port 5000 ✓
   │   └─► Failed → Try 5001
   │
   ├─► Write port to /tmp/music_server_port.txt
   │
   ├─► Update iptables redirect (if configured)
   │   └─► port 80 → [detected port]
   │
   └─► Start mDNS services
       ├─► HTTP service (_http._tcp.local)
       └─► Workstation service (_workstation._tcp.local)
           └─► For Android compatibility ✓
```

## Setup Scripts

### setup.sh (Main Setup)
```
┌─────────────────────────────────────┐
│        setup.sh                      │
│                                     │
│  1. Python/venv setup                │
│  2. Dependencies install             │
│  3. Test files (optional)            │
│  4. Systemd service (optional)       │
│  5. Android mDNS (optional)          │
│  6. Captive Portal (optional)        │
│                                     │
│  Asks user:                          │
│  - Create test files?                │
│  - Setup systemd service?            │
│  - Setup Android mDNS?               │
│  - Enable captive portal?            │
└─────────────────────────────────────┘
          │
          └─► Calls setup_android_mdns.sh (if chosen)
          └─► Configures iptables base rules (if chosen)
```

### setup_android_mdns.sh (Android-Specific)
```
┌─────────────────────────────────────┐
│   setup_android_mdns.sh              │
│                                     │
│  1. Install avahi-daemon             │
│  2. Configure for Android            │
│  3. Enable workstation service       │
│  4. Restart avahi                    │
│                                     │
│  Result:                             │
│  - Android can discover "cubie"      │
│  - Users type: cubie:5000            │
│  - Android auto-appends .local       │
└─────────────────────────────────────┘
```

### configure_captive_portal.sh (Manual Config)
```
┌─────────────────────────────────────┐
│configure_captive_portal.sh           │
│                                     │
│  1. Read /tmp/music_server_port.txt  │
│  2. Update iptables redirect         │
│  3. Save rules                       │
│                                     │
│  Use when:                           │
│  - Manual setup                      │
│  - Port changes                      │
│  - Troubleshooting                   │
└─────────────────────────────────────┘
```

## File Structure

```
music_server/
├── app.py                           # Main Flask application
├── requirements.txt                 # Python dependencies
├── README.md                        # User documentation
├── ANDROID_ACCESS.md                # Android-specific guide
├── CAPTIVE_PORTAL.md                # Captive portal guide
├── ARCHITECTURE.md                  # This file
│
├── setup.sh                         # Main setup script
├── setup_android_mdns.sh            # Android mDNS setup
├── configure_captive_portal.sh      # Manual captive portal config
│
├── get_ip.sh                        # Quick IP lookup script
├── test_connectivity.sh             # Connectivity diagnostic
├── start_hotspot.sh                 # WiFi hotspot launcher
├── start_with_tunnel.sh             # ngrok tunnel launcher
│
├── static/                          # Web interface
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── music/                           # MP3 files (auto-detected)
├── pictures/                        # Images (auto-detected)
├── documents/                       # Documents (auto-detected)
└── .thumbnails/                     # Generated thumbnails
```

## Port Auto-Detection Logic

```python
def find_available_port(start_port=5000, max_tries=100):
    for port in range(start_port, start_port + max_tries):
        try:
            with socket.socket(AF_INET, SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError("No available port found")
```

**Benefits:**
- ✅ Never fails with "Address already in use"
- ✅ Works on any network configuration
- ✅ Multiple servers can run simultaneously
- ✅ Simple for users (no port management)

## mDNS Service Registration

```python
# Three different service types for maximum compatibility
services = [
    ("cubie", "_http._tcp.local"),      # Standard HTTP
    ("cubie", "_workstation._tcp"),     # Android-friendly
    ("cubie", "_tcp.local"),            # Direct hostname
]
```

**Why Multiple Services:**
- Different devices support different service types
- Android prefers workstation service
- Desktop systems use HTTP service
- Fallback ensures something works

## Captive Portal Configuration

```python
# app.py detects port, writes to file
with open('/tmp/music_server_port.txt', 'w') as f:
    f.write(str(SERVICE_PORT))

# app.py updates iptables redirect
subprocess.run([
    'sudo', 'iptables', '-t', 'nat', '-A', 'PREROUTING',
    '-i', 'wlan0', '-p', 'tcp', '--dport', '80',
    '-j', 'REDIRECT', '--to-port', str(SERVICE_PORT)
])
```

**Flow:**
1. Server starts → Detects port (e.g., 5002)
2. Writes "5002" to `/tmp/music_server_port.txt`
3. Updates iptables: 80 → 5002
4. Users on WiFi → Browser → Redirected to music! 🎵

## User Access Methods

### Method 1: Captive Portal (Best for Non-Technical)
```
User connects to WiFi → Opens browser → Redirected to music server
```
**No URL needed! Perfect for guests and non-technical users.**

### Method 2: mDNS (Recommended)
```
Android:  http://cubie:5000
Desktop:  http://cubie.local:5000
```
**Simple, no IP addresses to remember.**

### Method 3: IP Address (Fallback)
```
http://192.168.x.x:5000
```
**Always works, but requires knowing the IP.**

## Design Principles

1. **Zero Configuration** - Works out of the box
2. **Auto-Adaptation** - Handles port conflicts, network changes
3. **Multiple Access Methods** - Something works for every use case
4. **Android-First** - Optimized for Android compatibility
5. **Non-Technical Friendly** - Captive portal, mDNS, simple URLs
6. **Modular** - Separate scripts for different features
7. **Fail-Safe** - Graceful degradation, fallbacks everywhere

## Common Scenarios

### Scenario 1: Home Use (Pi on existing WiFi)
```
✓ Enable Android mDNS
✓ Access via: cubie:5000
✗ No captive portal needed
```

### Scenario 2: Portable Use (Pi creates WiFi)
```
✓ Enable Captive Portal
✓ Enable Android mDNS
✓ Users connect to WiFi → Automatic redirect
✓ No configuration needed!
```

### Scenario 3: Headless Server
```
✓ Enable Systemd service
✓ Enable Android mDNS
✓ Access via: cubie:5000
✓ Works remotely
```

### Scenario 4: No mDNS Support
```
✗ mDNS not available
✓ Use IP address from router
✓ Or use ngrok tunnel
```

## Summary

This architecture provides **multiple ways to access the music server**, from the simplest (captive portal) to the most technical (IP address). Auto-port detection ensures it always works, and Android optimization makes it accessible to everyone.
