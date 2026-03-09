# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AIY Media Server (cubie-server)** - A lightweight Flask server for Raspberry Pi Zero that serves MP3 music, pictures, and documents through a mobile-friendly web interface with mDNS discovery (`cubie.local`).

## Development Commands

```bash
# Setup virtual environment (from music_server directory)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run server
python app.py

# Run with custom port
SERVICE_PORT=8080 python app.py
```

The server auto-detects an available port starting from 5000 and binds to `0.0.0.0`.

## Testing

There are no automated tests. Testing is manual:

```bash
# Generate test MP3 files (requires ffmpeg)
python create_test_music.py

# Test API endpoints
curl http://localhost:5000/api/health | jq
curl http://localhost:5000/api/music | jq
curl http://localhost:5000/api/pictures | jq
curl http://localhost:5000/api/documents | jq

# Force metadata reload
curl -X POST http://localhost:5000/api/refresh

# Check mDNS registration (Linux)
avahi-browse -a -t | grep -i cubie
```

## Environment Variables

- `SERVICE_PORT=8080` - Override preferred port (auto-detects if in use)
- `SERVICE_NAME="my-server"` - Override mDNS service name

## Architecture

### Backend: Single-file Flask app (`app.py`, ~2000 lines)

All server logic lives in `app.py`. Key subsystems:

- **Media metadata** — Scans `music/`, `pictures/`, `documents/` directories, extracts ID3 tags (mutagen), EXIF data (Pillow). Metadata stored in global lists (`METADATA_CACHE`, `PICTURES_CACHE`, `DOCUMENTS_CACHE`) protected by `FILE_CHANGE_LOCK`.
- **File monitoring** — `MusicEventHandler` (watchdog) watches all three media directories with 0.5s debounce to avoid partial reads.
- **mDNS discovery** — Dual registration via Python `zeroconf` library and spawned `avahi-publish-service` processes. Registers `_http._tcp`, `_workstation._tcp`, and `_tcp` service types for cross-platform compatibility.
- **Captive portal** — Writes port to `/tmp/music_server_port.txt`, configures iptables to redirect port 80 to the server port. Catch-all route redirects to `/setup-wifi` when offline.
- **WiFi management** — Endpoints to scan networks (`iwlist wlan0 scan`), configure wpa_supplicant, restart services, and reboot the system. These require sudo and are designed for Pi deployment.
- **Image processing** — Generates 300x300 JPEG thumbnails in `.thumbnails/` directory.

### Frontend: SPA in `static/`

- `index.html` — Main interface with three tabs: Music, Pictures, Documents
- `app.js` — Frontend logic (~780 lines) including a custom markdown-to-HTML renderer
- `shared-styles.js` — Reusable Tailwind components
- `wifi-setup.html` / `wifi-setup.js` — WiFi configuration page
- All CSS/JS assets bundled locally (Tailwind CSS, Lucide icons) for offline operation

### Autohotspot (`autohotspot/`)

Bash script (`autohotspotN`) that switches between WiFi client and hotspot mode based on whether configured SSIDs are in range. Managed by a systemd service.

### Startup via systemd

`scripts/run.sh` is the service entry point: waits for network (up to 5 min), optionally pulls git updates, then starts `app.py`.

## Key API Endpoints

```
GET  /                             → Root redirect
GET  /support                      → Support page
GET  /server-info                  → Server info page
GET  /setup-wifi                   → WiFi setup page (captive portal)
GET  /<path:path>                  → Catch-all (redirects to / when offline)

GET  /api/music                    → Music metadata (supports ?page=N&per_page=N)
GET  /music/<filename>             → Stream MP3 (range requests, caching)
GET  /api/pictures                 → Pictures with EXIF/IPTC metadata
GET  /api/pictures/<file>          → Serve picture file
GET  /api/pictures/<file>/thumbnail → 300x300 JPEG thumbnail
GET  /api/documents                → Document list with extracted titles
GET  /api/documents/<filename>     → Serve document file
POST /api/refresh                  → Force metadata reload
GET  /api/health                   → Health check with mDNS status
GET  /api/config                   → Server config for external tools
GET  /api/config/folders           → Folder paths config
DELETE /api/delete/<filename>      → Delete a music file
GET  /api/wifi/networks            → Scan WiFi networks
POST /api/wifi/configure           → Configure wpa_supplicant
GET  /api/wifi/status              → Current WiFi status
POST /api/wifi/restart             → Restart WiFi service
POST /api/wifi/reboot              → Reboot the Pi
GET  /api/tailscale/status         → Tailscale status
POST /api/tailscale/up             → Enable Tailscale
POST /api/tailscale/down           → Disable Tailscale
```

## Configuration

All config is module-level constants in `app.py`:

| Constant | Default | Env Override |
|---|---|---|
| `PREFERRED_SERVICE_PORT` | `5000` | `SERVICE_PORT` |
| `SERVICE_NAME` | hostname | `SERVICE_NAME` |
| `MUSIC_FOLDER` | `./music` | — |
| `PICTURES_FOLDER` | `./pictures` | — |
| `DOCUMENTS_FOLDER` | `./documents` | — |
| `THUMBNAILS_FOLDER` | `./.thumbnails` | — |

## Coding Conventions

- **Python**: PEP 8, type hints on new/changed functions, use `FILE_CHANGE_LOCK` for cache modifications
- **JavaScript/CSS**: Keep existing modular structure, kebab-case for DOM IDs/classes
- **File naming**: snake_case for Python, kebab-case for static assets

## Extending the Server

**Adding a new content type:**
1. Create cache dict and loading function following `load_picture_metadata()` pattern
2. Add file extensions to `MusicEventHandler` event filters
3. Add API routes following existing patterns (`@app.route('/api/newtype')`)
4. Update frontend tabs in `app.js`

**Adding a new API endpoint:**
```python
@app.route('/api/feature', methods=['GET'])
def get_feature():
    with FILE_CHANGE_LOCK:
        # Access caches safely
        pass
    return jsonify(result)
```

## Dependencies

Python: Flask, mutagen (MP3 tags), watchdog (filesystem events), zeroconf (mDNS), Pillow (images).

System (on Pi): ffmpeg, avahi-daemon, hostapd, dnsmasq, wpasupplicant, iptables-persistent.

## Pi Zero Constraints

- **512MB RAM**: Keep metadata in memory, avoid large objects
- **Single core**: File processing is debounced, no blocking operations
- **Storage**: Thumbnails cached to disk, originals streamed on-demand
