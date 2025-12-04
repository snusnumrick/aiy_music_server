# Changelog

All notable changes to the AIY Music Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-12-03

### Added
- **WiFi Setup Page Enhancements**
  - Displays currently connected WiFi network and signal strength.
  - Client-side and server-side password length validation (8-63 characters for WPA/WPA2).
- **Captive Portal Feature**
  - Automatically redirects devices connected to the Pi's hotspot to the WiFi setup page.
  - Implemented via `iptables` rule (Port 80 to 5001 redirection) and Flask catch-all route.
  - Integrated into `setup.sh` as an optional configuration step.

### Changed
- **mDNS Service Name Standardization**: Standardized service name to `cubie.local` across documentation and code.
- **Robust WiFi Status (get_wifi_status)**:
  - Improved detection by trying multiple paths for `iwconfig` and falling back to `iw` (modern tool).
  - Added `sudo` fallback for `iwconfig` and `iw` commands.
  - Enhanced SSID parsing to correctly strip quotes.
  - Improved signal strength display (e.g., "Excellent", "Good", "Fair").
- **Robust Local IP Detection (get_local_ip)**:
  - Fallback to `hostname -I` and `ip addr` parsing if socket connection fails.
  - Better handling for offline LAN scenarios.
- **Improved Network Connectivity Logging**:
  - `register_mdns_service` distinguishes between "Internet available" and "Local network connected (No Internet)".
  - `restart_mdns_service` waits for any valid local IP instead of strict internet access.

### Fixed
- **Tailwind `ReferenceError`**: Resolved by renaming `tailwind.min.css` to `tailwind.js` and updating HTML references to load it as a script.
- **SSID display bug**: Corrected parsing to prevent extra quotes in displayed network names.

### Documentation
- Updated `WIFI_SETUP_GUIDE.md` with captive portal details and required packages.
- Updated `README.md` and `QUICKSTART.md` with WiFi setup guide reference, directory structure, and mDNS consistency.

---

## [1.2.0] - 2025-11-25

### Added
- **mDNS Service Discovery** - Automatic network discovery using zeroconf
  - Service registered as "cubie.local" on port 5001
  - Accessible via `http://cubie.local:5001` from any device on network
  - No need to remember IP addresses!
  - Includes health check endpoint showing mDNS status
- **Service Monitoring** - Added verification commands for mDNS discovery

### Technical
- **Dependencies** - Added `zeroconf==0.148.0` to requirements.txt
- **Network Discovery** - Implemented ServiceInfo registration with Zeroconf
- **Graceful Shutdown** - Service unregisters properly on shutdown
- **Hostname Integration** - Uses system hostname + .local for registration
- **Logging Improvements** - Fixed mDNS registration status reporting

### Fixed
- **Conflicting Log Messages** - Startup messages now accurately reflect mDNS registration status
  - Success: Shows "✓ mDNS enabled" only when registration succeeds
  - Failure: Shows "⚠ mDNS disabled" with helpful alternative URLs

### Documentation
- Added mDNS troubleshooting section to README.md
- Updated Quick Start guide with mDNS access instructions
- Added service verification commands for different platforms

---

## [1.1.0] - 2025-11-25

### Added
- **Fullscreen Lyrics View** - New immersive full-screen lyrics display with adjustable font size
  - Dark gradient background for better readability
  - Three font size options: Small (A-), Medium (default), Large (A+)
  - Multiple exit options: Close button (×), "← Back" button, ESC key, tap outside
- **Fullscreen Button** - Added "📖 Fullscreen" button next to "📄 Lyrics" button
- **Favicon** - Added music note emoji (🎵) favicon to prevent 404 errors

### Changed
- **Default Port** - Changed from 5000 to 5001 to avoid conflicts with macOS AirPlay Receiver
- **Button Layout** - Improved action button layout with better spacing and mobile responsiveness
- **Static File Paths** - Fixed CSS and JavaScript paths to use `/static/` prefix for proper Flask serving

### Fixed
- **USLT Tag Reading** - Fixed lyrics not displaying in API responses
  - Now properly reads USLT tags from MP3 files (ID3v2.3/2.4 format)
  - Handles 'USLT::XXX' tag format created by ffmpeg
  - Properly extracts lyrics text using `.text` attribute
- **Test File Generation** - Fixed invalid MP3 file creation in `create_test_music.py`
  - Now uses ffmpeg to generate valid MP3 files with proper headers
  - Ensures metadata is properly embedded and readable

### Technical
- **Dependencies** - Added ffmpeg requirement for test file generation
- **Metadata Extraction** - Updated `load_metadata()` in `app.py` to handle USLT tags correctly
- **Code Quality** - Fixed duplicate ID checks in metadata extraction (TIT2, TPE1)

### Documentation
- Updated README.md with fullscreen lyrics feature details
- Added port 5001 information to troubleshooting sections
- Updated QUICKSTART.md with ffmpeg prerequisite and fullscreen lyrics usage
- Added comprehensive troubleshooting section for USLT tag issues

---

## [1.0.0] - 2025-11-25

### Added
- Initial release
- Flask backend with file monitoring (Watchdog)
- Metadata extraction using Mutagen library
- Mobile-responsive web interface
- HTML5 audio player with controls
- Search and filter functionality
- Modal lyrics display
- Real-time file detection (debounced)
- Systemd service support
- Automated setup script
- Test MP3 file generator

### Features
- Automatic MP3 file detection from music folder
- Reads ID3 tags: Title (TIT2), Artist (TPE1), Lyrics (USLT)
- Fallback to filename for missing metadata
- RESTful API with 5 endpoints
- Auto-refresh every 3 seconds
- Dark/light theme support
- Mobile-optimized touch controls
- Graceful error handling

### Endpoints
- `GET /` - Web interface
- `GET /api/music` - Music list with metadata (JSON)
- `GET /music/<filename>` - Stream MP3 file
- `POST /api/refresh` - Manual metadata refresh
- `GET /api/health` - Health check

---

## Migration Guide

### Upgrading from v1.0.0 to v1.1.0

1. **Update your browser bookmarks** to use port 5001 instead of 5000
   - Old: `http://192.168.x.x:5000`
   - New: `http://192.168.x.x:5001`

2. **If you have existing MP3 files**, test that lyrics display correctly:
   ```bash
   curl http://localhost:5001/api/music | jq
   ```

3. **Install ffmpeg** (if not already installed):
   ```bash
   # macOS
   brew install ffmpeg

   # Raspberry Pi
   sudo apt install ffmpeg
   ```

4. **Recreate test files** (optional):
   ```bash
   python create_test_music.py
   ```

### Port Configuration

If you prefer to use a different port, edit `app.py`:

```python
# Line 204 (approximately)
app.run(host='0.0.0.0', port=5001, debug=False)
```

Change `port=5001` to your preferred port.

---

## Known Issues

- None at this time

---

## Support

For issues or questions:
- Check README.md "Troubleshooting" section
- Review `/var/log/syslog` for system errors
- Enable debug mode by setting `debug=True` in `app.run()`
