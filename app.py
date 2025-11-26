from flask import Flask, jsonify, send_from_directory, request
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError
import os
import time
import socket
import signal
import sys
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

try:
    from zeroconf import ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    print("Warning: zeroconf not installed. mDNS service will not be available.")

app = Flask(__name__)

# Configuration
MUSIC_FOLDER = os.path.join(os.path.dirname(__file__), 'music')
METADATA_CACHE = []
FILE_CHANGE_LOCK = threading.Lock()

# mDNS Configuration
ZEROCONF_INSTANCE = None
SERVICE_NAME = "cubie-server"
SERVICE_TYPE = "_http._tcp.local."
SERVICE_PORT = 5001

class MusicEventHandler(FileSystemEventHandler):
    """Handle file system events for music folder"""

    def __init__(self):
        super().__init__()
        self.debounce_delay = 0.5
        self.last_change_time = 0

    def on_created(self, event):
        if event.is_directory:
            return

        if not event.src_path.endswith('.mp3'):
            return

        current_time = time.time()
        if current_time - self.last_change_time < self.debounce_delay:
            return

        self.last_change_time = current_time
        time.sleep(self.debounce_delay)

        with FILE_CHANGE_LOCK:
            load_metadata()

    def on_deleted(self, event):
        if event.is_directory:
            return

        if not event.src_path.endswith('.mp3'):
            return

        current_time = time.time()
        if current_time - self.last_change_time < self.debounce_delay:
            return

        self.last_change_time = current_time
        time.sleep(self.debounce_delay)

        with FILE_CHANGE_LOCK:
            load_metadata()

    def on_modified(self, event):
        if event.is_directory:
            return

        if not event.src_path.endswith('.mp3'):
            return

        current_time = time.time()
        if current_time - self.last_change_time < self.debounce_delay:
            return

        self.last_change_time = current_time
        time.sleep(self.debounce_delay)

        with FILE_CHANGE_LOCK:
            load_metadata()

def load_metadata():
    """Load metadata from all MP3 files in the music folder"""
    global METADATA_CACHE
    metadata_list = []

    if not os.path.exists(MUSIC_FOLDER):
        os.makedirs(MUSIC_FOLDER)
        METADATA_CACHE = metadata_list
        return

    for filename in os.listdir(MUSIC_FOLDER):
        if not filename.endswith('.mp3'):
            continue

        filepath = os.path.join(MUSIC_FOLDER, filename)

        try:
            audio = MP3(filepath)

            title = filename[:-4]
            artist = "Unknown"
            lyrics = ""

            try:
                tags = audio.tags
                if tags:
                    if 'TIT2' in tags:
                        title = str(tags['TIT2'][0])
                    elif 'TIT2' in tags:
                        title = str(tags['TIT2'][0])

                    if 'TPE1' in tags:
                        artist = str(tags['TPE1'][0])
                    elif 'TPE1' in tags:
                        artist = str(tags['TPE1'][0])

                    lyrics_keys = [k for k in tags.keys() if k.startswith('USLT')]
                    if lyrics_keys:
                        lyrics_value = tags[lyrics_keys[0]]
                        if hasattr(lyrics_value, 'text'):
                            lyrics = str(lyrics_value.text)
                        else:
                            lyrics = str(lyrics_value)
            except (ID3NoHeaderError, AttributeError, Exception):
                pass

            file_stat = os.stat(filepath)
            duration = audio.info.length if hasattr(audio.info, 'length') else 0

            metadata = {
                'filename': filename,
                'title': title,
                'artist': artist,
                'lyrics': lyrics,
                'duration': duration,
                'created': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            }

            metadata_list.append(metadata)

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

    metadata_list.sort(key=lambda x: x['filename'])
    METADATA_CACHE = metadata_list
    print(f"Loaded {len(metadata_list)} music files")

@app.route('/')
def index():
    """Serve the main web interface"""
    return send_from_directory('static', 'index.html')

@app.route('/api/music')
def get_music():
    """Return JSON array of music files with metadata"""
    with FILE_CHANGE_LOCK:
        return jsonify(METADATA_CACHE)

@app.route('/music/<filename>')
def stream_music(filename):
    """Stream MP3 file for playback"""
    return send_from_directory(MUSIC_FOLDER, filename, mimetype='audio/mpeg')

@app.route('/api/refresh', methods=['POST'])
def refresh_metadata():
    """Manually trigger metadata reload"""
    with FILE_CHANGE_LOCK:
        load_metadata()
    return jsonify({'status': 'success', 'count': len(METADATA_CACHE)})

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'files_count': len(METADATA_CACHE),
        'music_folder': MUSIC_FOLDER,
        'mdns_enabled': ZEROCONF_AVAILABLE,
        'service_name': SERVICE_NAME if ZEROCONF_AVAILABLE else None
    })

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def register_mdns_service():
    """Register mDNS service for network discovery"""
    global ZEROCONF_INSTANCE

    if not ZEROCONF_AVAILABLE:
        print("mDNS not available (zeroconf not installed)")
        print("Install with: pip install zeroconf")
        return None

    # Wait for network to be ready (helps on Pi Zero with slow WiFi)
    import time
    print("Checking network connectivity...")
    for i in range(5):
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.settimeout(1)
            test_socket.connect(("8.8.8.8", 53))
            ip = test_socket.getsockname()[0]
            test_socket.close()
            print(f"✓ Network ready")
            break
        except Exception:
            time.sleep(1)
            if i == 4:
                print(f"⚠ Network not fully ready - continuing anyway")

    hostname = socket.gethostname()
    ip_address = get_local_ip()

    # If hostname is "cubie", use "cubie.local"
    # If hostname is anything else (e.g., "cubie-2"), use that as hostname.local
    if hostname == SERVICE_NAME:
        # Hostname matches service name, use it
        server_hostname = f"{SERVICE_NAME.lower()}.local."
        service_display_name = f"{SERVICE_NAME} ({hostname})"
    else:
        # Hostname is different (e.g., cubie-2), use it
        server_hostname = f"{hostname}.local."
        service_display_name = f"{SERVICE_NAME} (on {hostname})"

    try:
        # Create service info
        service_name = f"{SERVICE_NAME}.{SERVICE_TYPE}"
        addresses = [socket.inet_aton(ip_address)]

        info = ServiceInfo(
            SERVICE_TYPE,
            service_name,
            addresses=addresses,
            port=SERVICE_PORT,
            properties={
                'path': '/',
                'description': 'Music Server'
            },
            server=server_hostname
        )

        # Register the service
        zeroconf = Zeroconf()
        zeroconf.register_service(info)

        ZEROCONF_INSTANCE = zeroconf

        print(f"✓ mDNS service registered: http://{server_hostname}:{SERVICE_PORT}")
        print(f"  - Service: {service_display_name}")
        print(f"  - Local IP: {ip_address}")
        print(f"  - Hostname: {hostname}.local")
        print(f"  - Access URLs:")
        print(f"    • http://{server_hostname}:{SERVICE_PORT}")
        print(f"    • http://{ip_address}:{SERVICE_PORT}")

        if hostname != SERVICE_NAME:
            print(f"  - Note: Using {hostname}.local (was renamed from {SERVICE_NAME})")

        return zeroconf
    except Exception as e:
        import traceback
        error_msg = str(e) if str(e) else "Unknown error"
        print(f"⚠ Warning: Could not register mDNS service")
        print(f"  Error: {error_msg}")
        print(f"  You can still access the server at: http://{ip_address}:5001")
        print(f"  Or: http://{hostname}.local:5001")
        print(f"  ")
        print(f"  Troubleshooting:")
        print(f"  - Ensure network is ready before starting")
        print(f"  - Check if avahi-daemon is running: sudo systemctl status avahi-daemon")
        print(f"  - Verify network connectivity: ping 8.8.8.8")
        print(f"  - Try manual service registration with avahi-browse")
        return None

def unregister_mdns_service():
    """Unregister mDNS service on shutdown"""
    global ZEROCONF_INSTANCE
    if ZEROCONF_INSTANCE:
        try:
            ZEROCONF_INSTANCE.close()
            print("✓ mDNS service unregistered")
        except Exception as e:
            print(f"Error unregistering mDNS service: {e}")
        finally:
            ZEROCONF_INSTANCE = None

def start_file_monitor():
    """Start the file system monitor"""
    event_handler = MusicEventHandler()
    observer = Observer()
    observer.schedule(event_handler, MUSIC_FOLDER, recursive=False)
    observer.start()
    print(f"Started file monitor on {MUSIC_FOLDER}")
    return observer

if __name__ == '__main__':
    print("=" * 50)
    print("AIY Music Server - Pi Zero Music Server")
    print("=" * 50)

    print(f"Music folder: {MUSIC_FOLDER}")

    load_metadata()

    print(f"Loaded {len(METADATA_CACHE)} music files")

    # Register mDNS service
    zeroconf_instance = None
    if ZEROCONF_AVAILABLE:
        zeroconf_instance = register_mdns_service()

    try:
        observer = start_file_monitor()
    except Exception as e:
        print(f"Warning: Could not start file monitor: {e}")
        observer = None

    try:
        print("\nStarting server on http://0.0.0.0:5001")
        if zeroconf_instance:
            print(f"✓ mDNS enabled: Access via http://cubie.local:5001")
        else:
            print("⚠ mDNS disabled: Using IP address instead")
        print("Press Ctrl+C to stop")
        print("=" * 50)
        app.run(host='0.0.0.0', port=5001, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if observer:
            observer.stop()
            observer.join()
        if zeroconf_instance:
            unregister_mdns_service()
