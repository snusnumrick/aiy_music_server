# Quick Start Guide

Get your AIY Music Server (Cubie) running in 5 minutes!

## Prerequisites

**Install ffmpeg** (required for creating test files):

```bash
# macOS
brew install ffmpeg

# Raspberry Pi
sudo apt update && sudo apt install ffmpeg
```

**The server will register as `cubie.local` on your network - no need to remember IP addresses!**

## For Raspberry Pi Zero

### Option 1: Automated Setup (Recommended)

```bash
# Make setup script executable (if not already)
chmod +x setup.sh

# Run the setup script
./setup.sh
```

The setup script will:
- Check your system
- Create Python virtual environment
- Install dependencies
- Create test MP3 files
- Optionally setup systemd service

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv music_server
source music_server/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure WiFi (if needed)
#    See the dedicated guide: WIFI_SETUP_GUIDE.md

# 4. Create test files (requires ffmpeg)
python create_test_music.py

# 5. Start server
python app.py
```

### Option 3: One-Line Install

```bash
python3 -m venv music_server && source music_server/bin/activate && pip install -r requirements.txt && python create_test_music.py && python app.py
```

## Access from Your Phone

**Super Easy: Just visit the mDNS service name!**
```
http://cubie.local:5001
```

**Alternative: Find IP address manually**
```bash
hostname -I
```
Then open: `http://192.168.X.X:5001`

**Note:** The server runs on port 5001 and registers as "cubie.local" for automatic discovery!

3. **Bookmark it!** Add to home screen for app-like experience

## Using the Server

### Adding Music

Simply copy MP3 files into the `music/` folder:
```bash
cp /path/to/your/songs/*.mp3 music/
```

The server will detect them automatically within 1-2 seconds!

### Common Tasks

**Start the server:**
```bash
source music_server/bin/activate
python app.py
```

**Start as background service:**
```bash
sudo systemctl start music-server
sudo systemctl status music-server
```

**Check server logs:**
```bash
journalctl -u music-server -f
```

**Stop the service:**
```bash
sudo systemctl stop music-server
```

**Create test files:**
```bash
python create_test_music.py
```

## What You'll See

### Web Interface Features

✅ **Track List** - All your MP3 files with title and artist
✅ **Search** - Find songs quickly
✅ **Play Button** - Tap to play/pause
✅ **Lyrics** - View full lyrics in modal
✅ **Fullscreen Lyrics** - Tap "📖 Fullscreen" for immersive view with adjustable font
✅ **Auto-Refresh** - New files appear automatically
✅ **Mobile-Optimized** - Works great on phone

Each track shows 3 action buttons: **[Play]** **[Lyrics]** **[Fullscreen]**

### API Testing

Check the API directly:
```bash
# Get all music
curl http://localhost:5001/api/music

# Health check
curl http://localhost:5001/api/health

# Force refresh
curl -X POST http://localhost:5001/api/refresh
```

## Troubleshooting

### Can't connect from phone?

```bash
# Verify server is running and listening on all interfaces
netstat -tlnp | grep :5001
# Should show 0.0.0.0:5001
```

### Port already in use?

```bash
# Find and kill the process
lsof -ti:5001 | xargs kill -9
```

### No music showing?

```bash
# Check music folder
ls -la music/

# Check file permissions
chmod 644 music/*.mp3
```

### Want to change port?

Edit `app.py` and change:
```python
app.run(host='0.0.0.0', port=5001, debug=False)
```
to:
```python
app.run(host='0.0.0.0', port=8080, debug=False)
```

## Next Steps

1. **Try it out** - Test with the generated MP3 files
2. **Add your music** - Copy your favorite songs to `music/`
3. **Setup auto-start** - Use systemd service (run `./setup.sh`)
4. **Read full docs** - See `README.md` for detailed documentation

## Need Help?

- Full documentation: `README.md`
- API Reference: See README.md "API Endpoints" section
- Troubleshooting: See README.md "Troubleshooting" section
- Development: See README.md "Development" section

---

**Enjoy your music!** 🎵
