from flask import Flask, jsonify, send_from_directory, request
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError
import os
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

app = Flask(__name__)

# Configuration
MUSIC_FOLDER = os.path.join(os.path.dirname(__file__), 'music')
METADATA_CACHE = []
FILE_CHANGE_LOCK = threading.Lock()

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

                    if 'USLT' in tags:
                        lyrics = str(tags['USLT'][0])
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
        'music_folder': MUSIC_FOLDER
    })

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

    try:
        observer = start_file_monitor()
    except Exception as e:
        print(f"Warning: Could not start file monitor: {e}")
        observer = None

    try:
        print("\nStarting server on http://0.0.0.0:5000")
        print("Access from phone: http://[PI_IP]:5000")
        print("\nPress Ctrl+C to stop")
        print("=" * 50)
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if observer:
            observer.stop()
            observer.join()
