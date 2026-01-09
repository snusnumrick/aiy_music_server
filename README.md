# AIY Music Server (cubie-server)

A lightweight music server designed for Raspberry Pi Zero that automatically detects and serves MP3 files with embedded metadata through a mobile-friendly web interface.

**Service Name: `cubie.local`** - Access your music from any device on the network!

## Features

- 🎵 **Automatic Detection**: Watchdog file monitoring detects new MP3 files instantly
- 📱 **Mobile-Friendly**: Responsive web interface optimized for phones
- 🌐 **mDNS Discovery**: Automatic network discovery as "cubie.local" - no need to remember IPs!
- 🏷️ **Metadata Support**: Reads ID3 tags for title, artist, and lyrics (ID3v2.3/2.4)
- ⏯️ **Built-in Player**: HTML5 audio player with next/previous controls
- 🔍 **Search & Filter**: Find tracks quickly by title or artist
- 📄 **Lyrics Display**: View full lyrics in modal overlay
- 📖 **Fullscreen Lyrics**: Immersive full-screen lyrics view with adjustable font size (3 sizes)
- ⚡ **Real-time Updates**: Auto-refreshes every 3 seconds
- 🎨 **Modern UI**: Dark/light theme support with gradient backgrounds
- 🔧 **File Monitoring**: Debounced file system watcher prevents partial reads

## Quick Start

### Prerequisites

```bash
# Install ffmpeg (required for creating test files)
# On macOS:
brew install ffmpeg

# On Raspberry Pi:
sudo apt update && sudo apt install ffmpeg
```

### 1. Install Dependencies

```bash
python3 -m venv music_server
source music_server/bin/activate
pip install -r requirements.txt
```

### 2. Configure WiFi (if needed)

If your Raspberry Pi is not connected to WiFi, you can configure it via a web interface:
- **[WiFi Setup Guide](WIFI_SETUP_GUIDE.md)**: Detailed instructions on how to set up WiFi, including captive portal.

### 3. Create Test Music Files

```bash
python create_test_music.py
```

This creates 8 sample MP3 files with various metadata scenarios including lyrics.

### 4. Start the Server

```bash
python app.py
```

The server will start and register an mDNS service for automatic network discovery.

**Expected Output:**
```
✓ mDNS service registered: http://cubie.local:5001
  - Service name: Cubie
  - Local IP: 192.168.x.x
  - Hostname: pi.local
  - URL: http://pi.local:5001
```

### 5. Access from Your Phone

**📱 Android (Easiest):**
```
http://cubie:5000
```
Android automatically appends `.local`, so this becomes `http://cubie.local:5000`

**🖥️ Desktop/Mac:**
```
http://cubie.local:5000
```

**Or use IP address:**
```bash
hostname -I
```
Then open: `http://192.168.x.x:5000`

**Port Note:** The server auto-detects available ports starting from 5000. If 5000 is in use, it will use 5001, 5002, etc. Check the startup message for the actual port.

### Android-Specific Setup

For best Android compatibility, run the mDNS setup script once:

```bash
sudo ./setup_android_mdns.sh
```

This configures avahi-daemon for Android's mDNS implementation and registers additional service types (workstation, etc.) that Android can discover.

For detailed Android access instructions, see: **`ANDROID_ACCESS.md`**

### Autohotspot (Automatic WiFi/Hotspot Switching)

For portable use, autohotspot automatically switches between WiFi and hotspot modes:

- **WiFi available**: Connects to your configured WiFi networks
- **WiFi not in range**: Creates a hotspot automatically
- **Enhanced Android support**: DNS + mDNS for maximum compatibility

Note: `scripts/start_hotspot.sh` is a manual “force hotspot now” helper for debugging/QA. For an always-on device, prefer autohotspot so you don’t have competing startup paths.

**Install during setup:**
```bash
sudo ./setup.sh
# Choose "Yes" for autohotspot installation
```

**Manual installation:**
```bash
sudo ./music_server/install-autohotspot.sh
```

For detailed information, see: **`AUTOHOTSPOT_INTEGRATION.md`**

## Directory Structure

```
music_server/
├── app.py                      # Main Flask application
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── music/                       # Put your MP3 files here
├── music-server.service         # Systemd service file
├── create_test_music.py         # Generate test MP3 files
└── static/
    ├── index.html               # Web interface
    ├── style.css                # Mobile-responsive styles
    └── app.js                   # Client-side JavaScript
```

## Usage

### Adding Music

Simply copy MP3 files into the `music/` directory. The server will:
- Detect the new files automatically (within 1-2 seconds)
- Extract metadata from ID3 tags
- Update the web interface

### Supported Metadata

- **Title** (TIT2): Song title, falls back to filename
- **Artist** (TPE1): Artist name, falls back to "Unknown"
- **Lyrics** (USLT): Song lyrics, displayed in modal
- **Duration**: Automatically detected from MP3

### Web Interface Features

- **Play/Pause**: Tap any track to start playback
- **Next Track**: Auto-advances when current track ends
- **Search**: Filter tracks by title, artist, or filename
- **Refresh Button**: Manual metadata reload
- **Lyrics View**: Tap "📄 Lyrics" button to see full text in modal overlay
- **Fullscreen Lyrics**: Tap "📖 Fullscreen" button for immersive full-screen lyrics view
  - Dark gradient background for better readability
  - Adjustable font size: Small (A-), Medium (default), Large (A+)
  - Multiple exit options: Close button (×), "← Back" button, ESC key, or tap outside
- **Auto-Refresh**: Polls server every 3 seconds for new files

## Deploy to Raspberry Pi Zero

### Quick Deployment

1. **Transfer files to Pi:**
   ```bash
   scp -r music_server/ pi@192.168.X.X:~/
   ```

2. **SSH into Pi and setup:**
   ```bash
   ssh pi@192.168.X.X
   cd ~/music_server
   chmod +x setup.sh
   sudo ./setup.sh
   ```

3. **Setup systemd service (recommended for auto-start):**

   The setup script will ask you to choose:
   - **Option 1:** Default service for user "pi"
   - **Option 2:** Custom service for any username

   The script will automatically:
   - Configure the service with correct paths
   - Install and enable the service
   - Start the service

   **Or start manually:**
   ```bash
   source music_server/bin/activate
   python app.py
   ```

4. **Optional: Setup Android mDNS (for better Android compatibility):**
   ```bash
   sudo ./setup_android_mdns.sh
   ```

5. **Access from your phone:**
   - **Android:** `http://cubie:5000`
   - **Desktop/Mac:** `http://cubie.local:5000`

**That's it!** The service will be discoverable as "cubie.local" on your network.

### Verify mDNS on Pi

```bash
# Check service is registered
curl http://localhost:5001/api/health | jq

# Browse mDNS services
avahi-browse -a -t | grep -i cubie

# Check systemd service status
sudo systemctl status music-server
sudo journalctl -u music-server -f
```

## Deployment (Production)

### Systemd Service Setup (Recommended)

**Portable Configuration:** The service file uses systemd specifiers (`%h` for home directory) to automatically detect paths. This means it works regardless of:
- Username (defaults to "pi", can be overridden)
- Installation location (works in any directory)
- No manual path editing required!

**1. Copy the service file to systemd directory:**
```bash
sudo cp music-server.service /etc/systemd/system/
```

**2. Enable the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable music-server
sudo systemctl start music-server
```

**3. Verify it's running:**
```bash
sudo systemctl status music-server
```

**4. View logs:**
```bash
journalctl -u music-server -f
```

**5. Access your music server:**
```
http://cubie.local:5001
```

**Custom Username:** To use a different username instead of "pi", run the setup script:

```bash
# Use the setup script - it handles everything automatically
sudo ./setup.sh

# Select option 2 (Custom: username)
# Enter your username when prompted
```

The setup script will:
- ✅ Verify you have sudo access
- ✅ Ask which user to run the service as
- ✅ Modify the service file with actual paths (no specifiers!)
- ✅ Install the service with correct permissions
- ✅ Enable and start the service

**Note:** The script handles all sudo operations internally - just run it once with sudo!

### Alternative: Manual Startup

If you prefer not to use systemd, you can start manually:

Add to `/etc/rc.local` (before `exit 0`):
```bash
cd /home/pi/music_server
source music_server/bin/activate
python app.py &
```

## Configuration

### Server Settings

You can modify these settings in `app.py`:

```python
MUSIC_FOLDER = os.path.join(os.path.dirname(__file__), 'music')  # Music directory
DEBOUNCE_DELAY = 0.5  # File change debounce (seconds)
POLLING_INTERVAL = 3000  # Client refresh rate (milliseconds)
```

### Port Configuration

**Auto-detection:** The server automatically finds an available port starting from 5000.

To specify a preferred port:

```bash
SERVICE_PORT=8080 python app.py
```

Or edit the port in `app.py`:

```python
# Preferred port (will auto-detect if in use)
PREFERRED_SERVICE_PORT = 5000
SERVICE_PORT = find_available_port(PREFERRED_SERVICE_PORT)
```

The actual port used will be displayed on server startup.

## Troubleshooting

### Server won't start

```bash
# Check if port is in use (server auto-detects, try 5000-5010)
sudo netstat -tlnp | grep -E ':(5000|5001|5002)'

# Check Python version (need 3.6+)
python3 --version

# Verify virtual environment
which python  # Should be in music_server/bin/

# Check if ffmpeg is installed (needed for test file creation)
ffmpeg -version
```

### Port already in use

The server auto-detects available ports starting from 5000. If you see "Address already in use":

```bash
# The server will automatically try the next port
# Check the startup message to see which port was selected

# Or specify a preferred port:
SERVICE_PORT=8080 python app.py
```

### Music files not detected

```bash
# Check file permissions
ls -la music/

# Verify file monitoring
curl http://localhost:5001/api/music

# Check logs for errors
python app.py

# Ensure MP3 files are valid (not corrupted)
file music/*.mp3
```

### Lyrics not showing (Empty lyrics field)

This issue was fixed in v1.1. The server now properly reads USLT tags from MP3 files. If you see empty lyrics:

1. Ensure your MP3 files have lyrics embedded (USLT tag)
2. Check the API response:
   ```bash
   curl http://localhost:5001/api/music | jq
   ```
3. Verify MP3 has lyrics using mutagen:
   ```bash
   python3 -c "from mutagen.mp3 import MP3; print(MP3('music/song.mp3').tags)"
   ```

### Phone can't connect

```bash
# Verify server is listening on all interfaces
netstat -tlnp | grep -E ':(5000|5001|5002)'
# Should show 0.0.0.0:XXXX, not 127.0.0.1:XXXX

# Check firewall
sudo ufw status
```

### mDNS not working (cubie.local not found)

**Verify mDNS is enabled:**
```bash
# Check the API health endpoint
curl http://localhost:5000/api/health | jq

# Should show: {"mdns_enabled": true, "service_name": "Cubie", ...}
```

**Browse for services on your network:**
```bash
# On Raspberry Pi/Linux (with avahi):
avahi-browse -a -t | grep -i cubie

# On macOS:
dns-sd -B _http._tcp

# On Windows (install Bonjour SDK):
```

**Android-specific troubleshooting:**
```bash
# Run the Android mDNS setup script
sudo ./setup_android_mdns.sh

# On Android, try both methods:
# 1. http://cubie:5000 (Android auto-appends .local)
# 2. http://cubie.local:5000 (explicit)
```

**Manual connection:**
If mDNS doesn't work on your network, use the IP address:
```bash
# Get Pi's IP
hostname -I
# Then visit: http://192.168.x.x:5000
```

**Comprehensive Troubleshooting:**
For detailed mDNS troubleshooting steps, see:
- `MDNS_TROUBLESHOOTING.md` - Complete guide to mDNS issues on Raspberry Pi
- `ANDROID_ACCESS.md` - Android-specific access guide

Common fixes:
1. Run Android mDNS setup: `sudo ./setup_android_mdns.sh`
2. Ensure avahi-daemon is running: `sudo systemctl status avahi-daemon`
3. Install zeroconf: `pip install --upgrade zeroconf`
4. Check network connectivity: `ping 8.8.8.8`
5. Verify firewall settings

### Slow file detection

- Normal detection time: 0.5-2 seconds after file write completes
- Debounce delay prevents partial file reads
- Check disk space: `df -h`

## Performance Considerations

### Pi Zero Limitations

- **RAM (512MB)**: Keep metadata in memory only
- **CPU (1 core)**: Avoid heavy processing during file generation bursts
- **Storage**: Monitor disk space with `df -h`
- **Network**: Use 2.4GHz WiFi for stability

### Optimization Tips

1. **File Count**: Works well with 100-500 files
2. **Metadata Size**: Keep lyrics under 10KB per file
3. **Refresh Rate**: Increase `POLLING_INTERVAL` if needed
4. **Auto-start**: Use systemd for reliability
5. **Pagination**: Use `?page=1&per_page=50` to reduce initial payload sizes
6. **Caching**: Media files are cached for 1 hour, static assets for 1 year
7. **Conditional Requests**: ETags and Last-Modified headers enable efficient caching
8. **Range Requests**: Large files support partial downloads and seeking

## Development

### API Endpoints

```
GET  /                  → Serve index.html
GET  /api/music         → Get music files (JSON) - supports pagination (?page=1&per_page=50)
GET  /music/<filename>  → Stream MP3 file (with caching and range requests)
POST /api/refresh       → Manually reload metadata
GET  /api/health        → Health check
GET  /api/config        → Get server configuration (for voice assistant)
GET  /api/pictures      → Get picture files (JSON) - supports pagination
GET  /api/pictures/<filename> → Serve picture file (with caching)
GET  /api/pictures/<filename>/thumbnail → Serve thumbnail (with caching)
GET  /api/documents     → Get document files (JSON) - supports pagination
GET  /api/documents/<filename> → Serve/download document file (with caching)
```

### API Response Format

**GET /api/music**
```json
// Full response (no pagination params)
[
  {
    "filename": "song.mp3",
    "title": "Song Title",
    "artist": "Artist Name",
    "lyrics": "Song lyrics...",
    "duration": 180.5,
    "created": "2025-11-25T10:30:00",
    "modified": "2025-11-25T10:30:00"
  }
]

// Paginated response (?page=1&per_page=50)
{
  "tracks": [
    {
      "filename": "song.mp3",
      "title": "Song Title",
      "artist": "Artist Name",
      "lyrics": "Song lyrics...",
      "duration": 180.5,
      "created": "2025-11-25T10:30:00",
      "modified": "2025-11-25T10:30:00"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 50,
  "total_pages": 2
}
```

**GET /api/config** (for voice assistant)
```json
{
  "music_folder": "/home/pi/music_server/music",
  "server_url": "http://localhost:5001",
  "server_port": 5001,
  "service_name": "cubie-server"
}
```

### Adding Features

The code is organized for easy extension:

- **File Monitor**: Edit `MusicEventHandler` in `app.py`
- **Metadata Extraction**: Modify `load_metadata()` function
- **UI Components**: Add HTML/CSS in `static/` directory
- **JavaScript Logic**: Edit `app.js` for frontend features

## Testing

### Test MP3 Generation

Run the test script to create sample files:
```bash
python create_test_music.py
```

This creates 8 test files with various metadata scenarios.

### Manual Testing

```bash
# Test API (use the port shown in startup message)
curl http://localhost:5000/api/music | jq

# Test file serving
curl -I http://localhost:5000/music/test.mp3

# Test health endpoint
curl http://localhost:5000/api/health | jq
```

### Browser Testing

1. Open developer tools (F12)
2. Check Console for errors
3. Monitor Network tab for API calls
4. Test on actual mobile device

## License

This project is designed for educational and personal use.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review `/var/log/syslog` for system errors
3. Enable debug mode by setting `debug=True` in `app.run()`

---

**Note**: This server is optimized for Raspberry Pi Zero. For more powerful devices (Pi 3, Pi 4), you can increase file limits and add features like playlist support, WebSocket updates, and advanced playback controls.
