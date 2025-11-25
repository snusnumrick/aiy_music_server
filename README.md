# AIY Music Server

A lightweight music server designed for Raspberry Pi Zero that automatically detects and serves MP3 files with embedded metadata through a mobile-friendly web interface.

## Features

- 🎵 **Automatic Detection**: Watchdog file monitoring detects new MP3 files instantly
- 📱 **Mobile-Friendly**: Responsive web interface optimized for phones
- 🏷️ **Metadata Support**: Reads ID3 tags for title, artist, and lyrics
- ⏯️ **Built-in Player**: HTML5 audio player with next/previous controls
- 🔍 **Search & Filter**: Find tracks quickly by title or artist
- 📄 **Lyrics Display**: View full lyrics in modal overlay
- ⚡ **Real-time Updates**: Auto-refreshes every 3 seconds
- 🎨 **Modern UI**: Dark/light theme support with gradient backgrounds

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv music_server
source music_server/bin/activate
pip install -r requirements.txt
```

### 2. Create Test Music Files

```bash
python create_test_music.py
```

This creates 8 sample MP3 files with various metadata scenarios.

### 3. Start the Server

```bash
python app.py
```

The server will start on `http://localhost:5000` (or `http://0.0.0.0:5000` for network access).

### 4. Access from Your Phone

Find your Pi's IP address:
```bash
hostname -I
```

Open your phone browser to: `http://192.168.x.x:5000`

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
- **Lyrics View**: Tap "Lyrics" button to see full text
- **Auto-Refresh**: Polls server every 3 seconds for new files

## Deployment (Production)

### Option 1: Systemd Service (Recommended)

1. Copy the service file:
```bash
sudo cp music-server.service /etc/systemd/system/
```

2. Edit the service file to update paths:
```bash
sudo nano /etc/systemd/system/music-server.service
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable music-server
sudo systemctl start music-server
sudo systemctl status music-server
```

4. View logs:
```bash
journalctl -u music-server -f
```

### Option 2: Manual Startup

Add to `/etc/rc.local` (before `exit 0`):
```bash
cd /home/pi/music_server
source music_server/bin/activate
python app.py &
```

## Configuration

### Environment Variables

You can modify these in `app.py`:

```python
MUSIC_FOLDER = os.path.join(os.path.dirname(__file__), 'music')  # Music directory
DEBOUNCE_DELAY = 0.5  # File change debounce (seconds)
POLLING_INTERVAL = 3000  # Client refresh rate (milliseconds)
PORT = 5000  # Server port
```

### Port Change

To change the default port (5000), edit `app.py`:

```python
app.run(host='0.0.0.0', port=5000, debug=False)
```

## Troubleshooting

### Server won't start

```bash
# Check if port is in use
sudo netstat -tlnp | grep :5000

# Check Python version (need 3.6+)
python3 --version

# Verify virtual environment
which python  # Should be in music_server/bin/
```

### Music files not detected

```bash
# Check file permissions
ls -la music/

# Verify file monitoring
curl http://localhost:5000/api/music

# Check logs for errors
python app.py
```

### Phone can't connect

```bash
# Verify server is listening on all interfaces
netstat -tlnp | grep :5000
# Should show 0.0.0.0:5000, not 127.0.0.1:5000

# Check firewall
sudo ufw status
```

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

## Development

### API Endpoints

```
GET  /                  → Serve index.html
GET  /api/music         → Get all music files (JSON)
GET  /music/<filename>  → Stream MP3 file
POST /api/refresh       → Manually reload metadata
GET  /api/health        → Health check
```

### API Response Format

```json
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
# Test API
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
