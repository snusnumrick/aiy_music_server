# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AIY Media Server (cubie-server)** - A lightweight Flask server for Raspberry Pi Zero that auto-detects and serves MP3 files, images, and documents through a mobile-friendly web interface with mDNS discovery (`cubie.local`).

## Development Commands

```bash
# Setup (from music_server directory)
cd music_server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run server
python app.py

# Generate test MP3 files (requires ffmpeg)
python create_test_music.py

# Test API
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

### Backend (`music_server/app.py`)

Single Flask application with these subsystems:

1. **Port Auto-Detection** - Scans 5000-5099, writes active port to `/tmp/music_server_port.txt`
2. **File Monitor** - Watchdog observer on `music/`, `pictures/`, `documents/` with 0.5s debounce
3. **Metadata Extraction**:
   - Music: mutagen reads ID3v2 tags (TIT2, TPE1, USLT for title/artist/lyrics)
   - Pictures: Pillow extracts EXIF/IPTC metadata, generates 300x300 thumbnails to `.thumbnails/`
   - Documents: Basic file stats
4. **mDNS Registration** - zeroconf registers `_http._tcp` and `_workstation._tcp` (Android-friendly)
5. **REST API** - JSON endpoints with pagination, ETags, range requests

Key globals: `MUSIC_CACHE`, `PICTURES_CACHE`, `DOCUMENTS_CACHE`, `FILE_CHANGE_LOCK` (thread safety)

### Frontend (`music_server/static/`)

- `index.html` - Main SPA with Tailwind CSS
- `app.js` - Tab navigation (Music/Pictures/Documents), 3s polling, search, full-screen viewers
- `shared-styles.js` - Reusable Tailwind components
- `wifi-setup.html` - Captive portal WiFi configuration

### API Endpoints

```
GET  /api/music                 → JSON list (supports ?page=N&per_page=N)
GET  /api/pictures              → JSON list with EXIF/IPTC metadata
GET  /api/documents             → JSON list
GET  /api/pictures/<file>/thumbnail → 300x300 JPEG
GET  /music/<filename>          → Stream with range request support
POST /api/refresh               → Force metadata reload
GET  /api/health                → Health check with mDNS status
GET  /api/config                → Server config for external tools
```

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

## Pi Zero Constraints

- **512MB RAM**: Keep metadata in memory, avoid large objects
- **Single core**: File processing is debounced, no blocking operations
- **Storage**: Thumbnails cached to disk, originals streamed on-demand
