# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIY Music Server (cubie-server) is a lightweight media server for Raspberry Pi Zero that serves MP3 music, pictures, and documents through a mobile-friendly web interface. It is discoverable on the local network via mDNS as `cubie.local`.

## Running the Server

```bash
# Setup virtual environment
python3 -m venv music_server
source music_server/bin/activate
pip install -r requirements.txt

# Run
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
curl http://localhost:5000/api/music | jq
curl http://localhost:5000/api/health | jq
curl -X POST http://localhost:5000/api/refresh
```

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
- `wifi-setup.html` / `wifi-setup.js` — WiFi configuration page
- All CSS/JS assets bundled locally (Tailwind CSS, Lucide icons) for offline operation

### Autohotspot (`autohotspot/`)

Bash script (`autohotspotN`) that switches between WiFi client and hotspot mode based on whether configured SSIDs are in range. Managed by a systemd service.

### Startup via systemd

`scripts/run.sh` is the service entry point: waits for network (up to 5 min), optionally pulls git updates, then starts `app.py`.

## Key API Endpoints

- `GET /api/music` — Music metadata (supports `?page=N&per_page=N`)
- `GET /music/<filename>` — Stream MP3 (supports range requests, caching)
- `GET /api/pictures`, `GET /api/pictures/<filename>`, `GET /api/pictures/<filename>/thumbnail`
- `GET /api/documents`, `GET /api/documents/<filename>`
- `POST /api/refresh` — Force metadata reload
- `GET /api/health` — Health check
- `DELETE /api/delete/<filename>` — Delete a music file
- `GET /api/wifi/networks`, `POST /api/wifi/configure`, `GET /api/wifi/status`
- `GET /api/tailscale/status`, `POST /api/tailscale/up`, `POST /api/tailscale/down`

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

## Dependencies

Python: Flask, mutagen (MP3 tags), watchdog (filesystem events), zeroconf (mDNS), Pillow (images).

System (on Pi): ffmpeg, avahi-daemon, hostapd, dnsmasq, wpasupplicant, iptables-persistent.
