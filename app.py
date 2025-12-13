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
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from PIL import Image, ExifTags
import shutil

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

try:
    from zeroconf import ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    print("Warning: zeroconf not installed. mDNS service will not be available.")

app = Flask(__name__)

# Add global error handler to ensure ALL errors return JSON
@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON errors for all exceptions"""
    import traceback
    traceback.print_exc()

    # Print detailed error info
    print(f"\n=== ERROR TRACEBACK ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    print(f"===================\n")

    # For API routes, return JSON
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}',
            'error_type': type(e).__name__
        }), 500

    # For other routes, return HTML error page
    return str(e), 500

# Configuration
MUSIC_FOLDER = os.path.join(os.path.dirname(__file__), 'music')
PICTURES_FOLDER = os.path.join(os.path.dirname(__file__), 'pictures')
DOCUMENTS_FOLDER = os.path.join(os.path.dirname(__file__), 'documents')
THUMBNAILS_FOLDER = os.path.join(os.path.dirname(__file__), '.thumbnails')

METADATA_CACHE = [] # Music cache
PICTURES_CACHE = []
DOCUMENTS_CACHE = []
FILE_CHANGE_LOCK = threading.Lock()

# mDNS Configuration
ZEROCONF_INSTANCE = None
SERVICE_NAME = "cubie"
SERVICE_TYPE = "_http._tcp.local."
SERVICE_PORT = 5001

# WiFi Configuration
WIFI_CONFIG_PATH = "/etc/wpa_supplicant/wpa_supplicant.conf"
INTERNET_AVAILABLE = False

class MusicEventHandler(FileSystemEventHandler):
    """Handle file system events for music folder"""

    def __init__(self):
        super().__init__()
        self.debounce_delay = 0.5
        self.last_change_time = 0

    def on_created(self, event):
        if event.is_directory:
            return

        # Check extension
        is_music = event.src_path.lower().endswith('.mp3')
        is_picture = event.src_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'))
        is_doc = not event.is_directory and not is_music and not is_picture and not os.path.basename(event.src_path).startswith('.')

        if is_music or is_picture or is_doc:
            print(f"File created: {event.src_path}")
            self._trigger_reload()

    def on_deleted(self, event):
        if event.is_directory:
            return

        # Check extension
        is_music = event.src_path.lower().endswith('.mp3')
        is_picture = event.src_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'))
        is_doc = not event.is_directory and not is_music and not is_picture and not os.path.basename(event.src_path).startswith('.')

        if is_music or is_picture or is_doc:
            print(f"File deleted: {event.src_path}")
            self._trigger_reload()

    def on_modified(self, event):
        if event.is_directory:
            return

        # Check extension to decide if reload is needed
        is_music = event.src_path.lower().endswith('.mp3')
        is_picture = event.src_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'))
        is_doc = not event.is_directory and not is_music and not is_picture and not os.path.basename(event.src_path).startswith('.')

        if is_music or is_picture or is_doc:
            print(f"File modified: {event.src_path}")
            self._trigger_reload()

    def _trigger_reload(self):
        current_time = time.time()
        if current_time - self.last_change_time < self.debounce_delay:
            return

        self.last_change_time = current_time
        time.sleep(self.debounce_delay)

        print("Acquiring lock for metadata reload...")
        with FILE_CHANGE_LOCK:
            print("Lock acquired. Reloading metadata...")
            load_metadata()
            load_picture_metadata()
            load_document_metadata()
            print("Metadata reload complete.")

def decode_text(data):
    """
    Decode bytes or string with automatic encoding detection.
    Handles: ASCII with nulls, mixed ASCII+UTF-16-LE, or pure UTF-16-LE.

    Args:
        data: bytes object or string

    Returns:
        str: decoded text
    """
    # Convert string to bytes if needed
    if isinstance(data, str):
        data = data.encode('latin-1')

    # Check if it starts with ASCII (no null bytes in first ~10 bytes suggest ASCII timestamp)
    first_null = data.find(b'\x00')

    if first_null > 5:  # Likely has ASCII prefix (like "0:05:22")
        # Split at first null byte and decode remaining as UTF-16-LE
        remaining = data[first_null + 1:]
        if remaining:
            try:
                text = remaining.decode('utf-16-le', errors='ignore')
                text = text.replace('\x00', '')
                return text.strip()
            except:
                return ""
        return ""

    # Check if this looks like UTF-16-LE (every other byte is \x00)
    null_count = data[:20].count(b'\x00')  # Check first 20 bytes
    if null_count > len(data[:20]) * 0.3:  # More than 30% nulls suggests UTF-16-LE
        # UTF-16-LE: decode and remove prefix before first null character
        try:
            text = data.decode('utf-16-le', errors='ignore')
            null_pos = text.find('\x00')
            if null_pos != -1:
                text = text[null_pos + 1:]
            text = text.replace('\x00', '')
            return text.strip()
        except Exception as e:
            return ""
    else:
        # Plain ASCII with some null/control bytes - extract only printable ASCII
        try:
            # Decode as ASCII and keep only printable characters
            text = data.decode('ascii', errors='ignore')
            # Remove all control characters (keeping only printable ASCII)
            text = ''.join(char for char in text if char.isprintable() or char.isspace())
            return text.strip()
        except:
            return ""

def get_exif_data(image_path):
    """Extract EXIF and IPTC data from image (compatible with Pillow 6.x+)"""
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        # Try to get EXIF data safely
        exif = {}
        try:
            raw_exif = img._getexif()
            if raw_exif:
                exif = { ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items() }
        except (AttributeError, TypeError):
            pass
        
        title = ""
        caption = ""
        
        # Try IPTC first (this is what macOS uses for Title)
        try:
            from PIL import IptcImagePlugin
            iptc = IptcImagePlugin.getiptcinfo(img)
            if iptc:
                # IPTC Object Name (2, 5) = Title/Headline
                if (2, 5) in iptc:
                    val = iptc[(2, 5)]
                    if isinstance(val, bytes):
                        title = val.decode('utf-8', errors='ignore').strip()
                    elif isinstance(val, list) and val:
                        title = val[0].decode('utf-8', errors='ignore').strip() if isinstance(val[0], bytes) else str(val[0]).strip()
                    else:
                        title = str(val).strip()
                
                # IPTC Headline (2, 105) as backup title
                if not title and (2, 105) in iptc:
                    val = iptc[(2, 105)]
                    if isinstance(val, bytes):
                        title = val.decode('utf-8', errors='ignore').strip()
                    else:
                        title = str(val).strip()
                
                # IPTC Caption/Abstract (2, 120)
                if (2, 120) in iptc:
                    val = iptc[(2, 120)]
                    if isinstance(val, bytes):
                        caption = val.decode('utf-8', errors='ignore').strip()
                    else:
                        caption = str(val).strip()
        except Exception as e:
            print(f"IPTC read error: {e}")
        
        # Fall back to EXIF if no IPTC title

        # XPTitle (Windows)
        for key in list(exif.keys()):
            if key == 0x9c9b or key == 'XPTitle':
                try:
                    val = exif[key]
                    if isinstance(val, bytes):
                        decoded = decode_text(val)
                        if decoded and not title:
                            title = decoded
                except Exception as _e:
                    pass
            if key == 0x9c9c or key == 'XPComment':
                try:
                    val = exif[key]
                    if isinstance(val, bytes):
                        decoded = decode_text(val)
                        if decoded and not caption:
                            caption = decoded
                except Exception as _e:
                    pass

        # if not title and 'DocumentName' in exif:
        if 'DocumentName' in exif:
            title = str(exif['DocumentName']).strip()

        # if not caption and 'ImageDescription' in exif:
        if 'ImageDescription' in exif:
            val = exif['ImageDescription']
            if isinstance(val, bytes):
                try:
                    caption = val.decode('utf-8').strip()
                except Exception as _e:
                    caption = val.decode('latin-1', errors='ignore').strip()
            else:
                caption = decode_text(val)

        # Get date - try EXIF first
        date_taken = str(exif.get('DateTimeOriginal', ''))
        
        # Try IPTC date if no EXIF date
        if not date_taken:
            try:
                from PIL import IptcImagePlugin
                iptc = IptcImagePlugin.getiptcinfo(img)
                if iptc:
                    # IPTC Date Created (2, 55) + Time Created (2, 60)
                    if (2, 55) in iptc:
                        val = iptc[(2, 55)]
                        if isinstance(val, bytes):
                            date_taken = val.decode('utf-8', errors='ignore').strip()
                        else:
                            date_taken = str(val).strip()
            except Exception as _e:
                pass
        
        # Fall back to file modification date if still no date
        if not date_taken:
            try:
                import os
                mtime = os.path.getmtime(image_path)
                from datetime import datetime
                date_taken = datetime.fromtimestamp(mtime).strftime('%Y:%m:%d %H:%M:%S')
            except Exception as _e:
                pass
                
        return {
            'width': width,
            'height': height,
            'title': title,
            'caption': caption,
            'make': str(exif.get('Make', '')),
            'model': str(exif.get('Model', '')),
            'date_taken': date_taken
        }

    except Exception as e:
        print(f"Error reading metadata from {image_path}: {e}")
        try:
            img = Image.open(image_path)
            w, h = img.size
            return {'width': w, 'height': h, 'title': '', 'caption': '', 'make': '', 'model': '', 'date_taken': ''}
        except:
            return {'width': 0, 'height': 0, 'title': '', 'caption': '', 'make': '', 'model': '', 'date_taken': ''}



def generate_thumbnail(image_path, thumb_path):

    """Generate thumbnail for image"""
    try:
        if os.path.exists(thumb_path):
            return True
            
        img = Image.open(image_path)
        img.thumbnail((300, 300))
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        
        # Save as JPEG
        img.save(thumb_path, "JPEG", quality=70)
        return True
    except Exception as e:
        print(f"Error generating thumbnail for {image_path}: {e}")
        return False

def load_picture_metadata():
    """Load metadata from pictures folder"""
    global PICTURES_CACHE
    print("Loading picture metadata...")
    pictures = []
    
    if not os.path.exists(PICTURES_FOLDER):
        os.makedirs(PICTURES_FOLDER)
        PICTURES_cache = []
        return

    if not os.path.exists(THUMBNAILS_FOLDER):
        os.makedirs(THUMBNAILS_FOLDER)

    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
    files = [f for f in os.listdir(PICTURES_FOLDER) if f.lower().endswith(valid_extensions)]
    
    for filename in files:
        filepath = os.path.join(PICTURES_FOLDER, filename)
        thumb_filename = f"{os.path.splitext(filename)[0]}.jpg"
        thumb_path = os.path.join(THUMBNAILS_FOLDER, thumb_filename)
        
        try:
            # Generate thumbnail if needed
            generate_thumbnail(filepath, thumb_path)
            
            # Get metadata
            exif_data = get_exif_data(filepath)
            file_stat = os.stat(filepath)
            
            picture = {
                'filename': filename,
                'thumbnail_url': f'/api/pictures/{filename}/thumbnail',
                'url': f'/api/pictures/{filename}',
                'title': exif_data['title'] or filename,
                'caption': exif_data['caption'],
                'width': exif_data['width'],
                'height': exif_data['height'],
                'date_taken': exif_data.get('date_taken', ''),
                'created': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            }
            pictures.append(picture)
        except Exception as e:
            print(f"Error processing picture {filename}: {e}")
            
    pictures.sort(key=lambda x: x['filename'])
    PICTURES_CACHE = pictures
    print(f"Loaded {len(pictures)} pictures.")

def load_document_metadata():
    """Load metadata from documents folder"""
    global DOCUMENTS_CACHE
    print("Loading document metadata...")
    documents = []
    
    if not os.path.exists(DOCUMENTS_FOLDER):
        os.makedirs(DOCUMENTS_FOLDER)
        DOCUMENTS_CACHE = []
        return
        
    for filename in os.listdir(DOCUMENTS_FOLDER):
        if filename.startswith('.'): continue
        
        filepath = os.path.join(DOCUMENTS_FOLDER, filename)
        if os.path.isdir(filepath): continue
        
        try:
            file_stat = os.stat(filepath)
            
            doc = {
                'filename': filename,
                'url': f'/api/documents/{filename}',
                'size': file_stat.st_size,
                'created': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'type': os.path.splitext(filename)[1].lower().replace('.', '')
            }
            documents.append(doc)
        except Exception as e:
            print(f"Error processing document {filename}: {e}")
            
    documents.sort(key=lambda x: x['filename'])
    DOCUMENTS_CACHE = documents
    print(f"Loaded {len(documents)} documents.")

def load_metadata():
    """Load metadata from all MP3 files in the music folder"""
    global METADATA_CACHE
    print("Starting load_metadata function...")
    metadata_list = []

    if not os.path.exists(MUSIC_FOLDER):
        print(f"Music folder not found: {MUSIC_FOLDER}. Creating it.")
        os.makedirs(MUSIC_FOLDER)
        METADATA_CACHE = metadata_list
        return

    files = [f for f in os.listdir(MUSIC_FOLDER) if f.endswith('.mp3')]
    print(f"Found {len(files)} MP3 files to process.")

    for filename in files:
        filepath = os.path.join(MUSIC_FOLDER, filename)
        # print(f"  Processing: {filename}") 

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
            except (ID3NoHeaderError, AttributeError, Exception) as e:
                print(f"    Warning: Could not read ID3 tags for {filename}: {e}")

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
            print(f"  Error processing {filename}: {e}")
            continue

    metadata_list.sort(key=lambda x: x['filename'])
    METADATA_CACHE = metadata_list
    print(f"Finished load_metadata. Cache updated with {len(metadata_list)} items.")

def get_music_folder():
    """Get the music folder path (for local services on same machine)"""
    return MUSIC_FOLDER

@app.route('/')
def index():
    """Serve the main web interface"""
    # Check if internet is available
    check_internet_connection()
    if not INTERNET_AVAILABLE:
        # Redirect to WiFi setup page if offline
        from flask import redirect
        return redirect('/setup-wifi')
    return send_from_directory('static', 'index.html')

@app.route('/api/tailscale/status')
def tailscale_status():
    """Get TailScale status"""
    try:
        import subprocess
        result = subprocess.run(['tailscale', 'status', '--json'],
                              capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            return jsonify({
                'installed': False,
                'running': False,
                'error': result.stderr
            }), 200

        import json
        status_data = json.loads(result.stdout)

        # Parse status
        installed = True
        running = status_data.get('BackendState') == 'Running'

        return jsonify({
            'installed': installed,
            'running': running,
            'status': status_data,
            'url': status_data.get('Self', {}).get('ID', ''),
            'addresses': status_data.get('Self', {}).get('TailscaleIPs', []),
            'version': status_data.get('Version', '')
        }), 200

    except subprocess.TimeoutExpired:
        return jsonify({
            'installed': True,
            'running': False,
            'error': 'Command timed out'
        }), 200
    except FileNotFoundError:
        return jsonify({
            'installed': False,
            'running': False,
            'error': 'TailScale not installed'
        }), 200
    except Exception as e:
        return jsonify({
            'installed': True,
            'running': False,
            'error': str(e)
        }), 200

@app.route('/api/tailscale/up', methods=['POST'])
def tailscale_up():
    """Enable TailScale"""
    try:
        import subprocess
        result = subprocess.run(['sudo', 'tailscale', 'up'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'message': 'TailScale enabled successfully'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.stderr
            }), 500

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/tailscale/down', methods=['POST'])
def tailscale_down():
    """Disable TailScale"""
    try:
        import subprocess
        result = subprocess.run(['sudo', 'tailscale', 'down'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'message': 'TailScale disabled successfully'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.stderr
            }), 500

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/music')
def get_music():
    """Return JSON array of music files with metadata"""
    print("Received request: GET /api/music")
    
    # Check if cache is empty and try to load if it is
    if not METADATA_CACHE:
        print("Cache is empty. Attempting to load metadata...")
        # We don't use the lock here to avoid potential deadlock if the lock is already held by a stuck observer?
        # Actually, if we are here, we are in a request thread.
        # If observer holds the lock, we wait.
        with FILE_CHANGE_LOCK:
             if not METADATA_CACHE: # Double check
                 load_metadata()
    
    print("Acquiring lock to read metadata...")
    with FILE_CHANGE_LOCK:
        print(f"Returning {len(METADATA_CACHE)} tracks.")
        return jsonify(METADATA_CACHE)

@app.route('/music/<filename>')
def stream_music(filename):
    """Stream MP3 file for playback"""
    return send_from_directory(MUSIC_FOLDER, filename, mimetype='audio/mpeg')

@app.route('/api/pictures')
def get_pictures():
    """Return JSON array of picture files"""
    with FILE_CHANGE_LOCK:
        if not PICTURES_CACHE:
            load_picture_metadata()
        return jsonify(PICTURES_CACHE)

@app.route('/api/pictures/<filename>')
def get_picture(filename):
    """Serve picture file"""
    return send_from_directory(PICTURES_FOLDER, filename)

@app.route('/api/pictures/<filename>/thumbnail')
def get_thumbnail(filename):
    """Serve thumbnail file"""
    thumb_filename = f"{os.path.splitext(filename)[0]}.jpg"
    
    # Check if thumbnail exists
    if not os.path.exists(os.path.join(THUMBNAILS_FOLDER, thumb_filename)):
        # Try to generate it on demand
        if os.path.exists(os.path.join(PICTURES_FOLDER, filename)):
            generate_thumbnail(
                os.path.join(PICTURES_FOLDER, filename),
                os.path.join(THUMBNAILS_FOLDER, thumb_filename)
            )
            
    return send_from_directory(THUMBNAILS_FOLDER, thumb_filename)

@app.route('/api/documents')
def get_documents():
    """Return JSON array of document files"""
    with FILE_CHANGE_LOCK:
        if not DOCUMENTS_CACHE:
            load_document_metadata()
        return jsonify(DOCUMENTS_CACHE)

@app.route('/api/documents/<filename>')
def get_document(filename):
    """Serve/download document file"""
    return send_from_directory(DOCUMENTS_FOLDER, filename, as_attachment=True)

@app.route('/api/config/folders')
def get_folders_config():
    """Return folder paths for discovery"""
    return jsonify({
        'music': MUSIC_FOLDER,
        'pictures': PICTURES_FOLDER,
        'documents': DOCUMENTS_FOLDER
    })

@app.route('/api/refresh', methods=['POST'])
def refresh_metadata():
    """Manually trigger metadata reload"""
    print("Received request: POST /api/refresh")
    with FILE_CHANGE_LOCK:
        load_metadata()
        load_picture_metadata()
        load_document_metadata()
    return jsonify({
        'status': 'success', 
        'music_count': len(METADATA_CACHE),
        'pictures_count': len(PICTURES_CACHE),
        'documents_count': len(DOCUMENTS_CACHE)
    })

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

@app.route('/api/config')
def get_config():
    """Return configuration for voice assistant and other services"""
    return jsonify({
        'music_folder': MUSIC_FOLDER,
        'server_url': f'http://localhost:{SERVICE_PORT}',
        'server_port': SERVICE_PORT,
        'service_name': SERVICE_NAME
    })

@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_track(filename):
    """Delete a music file"""
    try:
        # Decode the filename
        filename = filename.replace('/', '')
        filepath = os.path.join(MUSIC_FOLDER, filename)

        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({
                'status': 'error',
                'message': 'File not found'
            }), 404

        # Delete the file
        os.remove(filepath)

        # Reload metadata
        with FILE_CHANGE_LOCK:
            load_metadata()

        return jsonify({
            'status': 'success',
            'message': 'File deleted successfully'
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/support')
def support_page():
    """Serve the support page"""
    return send_from_directory('static', 'support.html')

@app.route('/setup-wifi')
def wifi_setup_page():
    """Serve the WiFi setup page"""
    return send_from_directory('static', 'wifi-setup.html')

@app.route('/<path:path>')
def catch_all(path):
    """Catch-all route for captive portal redirection"""
    # If we are serving static files, let them through (though Flask usually handles this before)
    if path.startswith('static/'):
        return send_from_directory('static', path[7:])
        
    # Check connectivity
    check_internet_connection()
    
    # If offline (hotspot mode), redirect everything to wifi setup
    if not INTERNET_AVAILABLE:
        from flask import redirect
        return redirect('/setup-wifi')
        
    return "Not Found", 404

@app.route('/api/wifi/networks')
def wifi_networks():
    """Get list of available WiFi networks"""
    try:
        result = scan_wifi_networks()
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error scanning networks: {str(e)}'
        }), 500

@app.route('/api/wifi/configure', methods=['POST'])
def wifi_configure():
    """Configure WiFi with provided credentials"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        ssid = data.get('ssid')
        password = data.get('password')

        if not ssid:
            return jsonify({
                'success': False,
                'error': 'SSID is required'
            }), 400

        if not password:
            return jsonify({
                'success': False,
                'error': 'Password is required'
            }), 400

        # Validate password length for WPA/WPA2
        if len(password) < 8 or len(password) > 63:
            return jsonify({
                'success': False,
                'error': 'WPA/WPA2 passwords must be between 8 and 63 characters long.'
            }), 400

        result = configure_wifi(ssid, password)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/wifi/status')
def wifi_status():
    """Get current WiFi connection status"""
    return jsonify(get_wifi_status()), 200

@app.route('/api/wifi/restart', methods=['POST'])
def wifi_restart():
    """Restart the server to reconnect to WiFi"""
    try:
        # Log the restart request
        print("WiFi restart requested via API")

        # Restart the Flask app using os.execv
        # This replaces the current process with a new one
        python = sys.executable
        os.execv(python, [python] + sys.argv)

        # This line will never be reached
        return jsonify({
            'success': True,
            'message': 'Server restarting...'
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error restarting server: {str(e)}'
        }), 500

@app.route('/api/wifi/reboot', methods=['POST'])
def wifi_reboot():
    """Reboot the system to enable WiFi adapter"""
    try:
        # Log the reboot request
        print("System reboot requested via API")

        # Reboot the system using subprocess
        import subprocess
        subprocess.run(['sudo', 'reboot'], check=True)

        # This line will never be reached
        return jsonify({
            'success': True,
            'message': 'System rebooting...'
        }), 200

    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'error': f'Failed to reboot: {str(e)}'
        }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error rebooting system: {str(e)}'
        }), 500

def get_local_ip():
    """Get the local IP address of the machine, robust to offline networks"""
    # 1. Try connecting to an external server (most reliable if internet available)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    # 2. Try getting IP from hostname -I (linux)
    try:
        import subprocess
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=1)
        if result.returncode == 0:
            ips = result.stdout.strip().split()
            for ip in ips:
                # Return first non-loopback IPv4
                if '.' in ip and not ip.startswith('127.'):
                    return ip
    except Exception:
        pass

    # 3. Try parsing ip addr show
    try:
        import subprocess
        # Try standard paths
        cmds = [['ip', '-4', 'addr', 'show'], ['/sbin/ip', '-4', 'addr', 'show']]
        
        for cmd in cmds:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
                if result.returncode == 0:
                    output = result.stdout
                    # Simple parsing for inet
                    import re
                    # Look for wlan0 first
                    wlan_match = re.search(r'wlan0.*?inet\s+(\d+\.\d+\.\d+\.\d+)', output, re.DOTALL)
                    if wlan_match:
                        return wlan_match.group(1)
                    
                    # Look for any inet
                    matches = re.findall(r'inet\s+(\d+\.\d+\.\d+\.\d+)', output)
                    for ip in matches:
                        if not ip.startswith('127.'):
                            return ip
            except FileNotFoundError:
                continue
    except Exception:
        pass

    # 4. Fallback to socket.gethostbyname (might return 127.0.1.1 on Debian)
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"

def check_internet_connection():
    """Check if internet connection is available"""
    global INTERNET_AVAILABLE
    try:
        # Try to connect to a reliable external server
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.settimeout(2)
        test_socket.connect(("8.8.8.8", 53))
        ip = test_socket.getsockname()[0]
        test_socket.close()
        INTERNET_AVAILABLE = True
        return True
    except Exception:
        INTERNET_AVAILABLE = False
        return False

def scan_wifi_networks():
    """Scan for available WiFi networks using iwlist"""
    try:
        import subprocess
        print("Scanning for WiFi networks...")

        # Check if wlan0 exists first
        interface_check = subprocess.run(
            ['ip', 'link', 'show', 'wlan0'],
            capture_output=True,
            text=True,
            timeout=3
        )

        if interface_check.returncode != 0:
            print("WARNING: wlan0 not found (Pi likely in hotspot mode)")
            print("WiFi scan skipped - interface not available")
            return {
                'success': False,
                'error': 'WiFi adapter not available (Pi in hotspot mode)',
                'hotspot_mode': True
            }

        result = subprocess.run(
            ['sudo', 'iwlist', 'wlan0', 'scan'],
            capture_output=True,
            text=True,
            timeout=10
        )

        print(f"iwlist exit code: {result.returncode}")

        if result.returncode != 0:
            print(f"iwlist error: {result.stderr}")
            return {
                'success': False,
                'error': f'iwlist command failed: {result.stderr}'
            }

        networks = []
        current_network = {}
        lines = result.stdout.split('\n')

        print(f"Total lines in scan output: {len(lines)}")

        for line in lines:
            line = line.strip()

            if 'ESSID:' in line:
                essid = line.split('ESSID:')[1].strip('"')
                print(f"Found ESSID: '{essid}'")

                # Save previous network if exists
                if current_network and 'ssid' in current_network:
                    print(f"  Saving network: {current_network['ssid']}")
                    networks.append(current_network)

                # Start new network
                if essid and essid != 'off/any':
                    # Visible network
                    print(f"  Adding visible network: {essid}")
                    current_network = {'ssid': essid}
                elif essid == 'off/any':
                    # Hidden network - create placeholder
                    print("  Adding hidden network placeholder")
                    current_network = {
                        'ssid': 'Hidden Network',
                        'hidden': True
                    }
                else:
                    # Empty ESSID - treat as hidden
                    print("  Adding empty ESSID as hidden")
                    current_network = {
                        'ssid': 'Hidden Network',
                        'hidden': True
                    }

            elif 'Encryption key:' in line:
                if current_network:  # Ensure we have a network to update
                    encryption = line.split('Encryption key:')[1].strip()
                    current_network['encryption'] = 'off' if encryption == 'off' else 'on'
                    print(f"  Network {current_network.get('ssid', '?')} encryption: {current_network['encryption']}")

            elif 'IE: IEEE 802.11i/WPA2' in line:
                if current_network:
                    current_network['security'] = 'WPA2'
                    print(f"  Network {current_network.get('ssid', '?')} security: WPA2")
            elif 'IE: WPA Version' in line:
                if current_network:
                    current_network['security'] = 'WPA'
                    print(f"  Network {current_network.get('ssid', '?')} security: WPA")

            elif 'Quality=' in line:
                if current_network:
                    # Extract signal strength if available
                    quality_part = line.split('Quality=')[1].split(' ')[0]
                    current_network['signal'] = quality_part

        # Add the last network
        if current_network and 'ssid' in current_network:
            print(f"Adding final network: {current_network['ssid']}")
            networks.append(current_network)

        print(f"Total networks found: {len(networks)}")
        for net in networks:
            print(f"  - {net['ssid']}")

        # Sort by signal strength if available
        networks.sort(key=lambda x: x.get('signal', '0'), reverse=True)

        return {
            'success': True,
            'networks': networks
        }

    except subprocess.TimeoutExpired:
        print("WiFi scan timed out after 10 seconds")
        return {
            'success': False,
            'error': 'WiFi scan timed out'
        }
    except FileNotFoundError:
        print("iwlist command not found")
        return {
            'success': False,
            'error': 'iwlist command not found. Make sure wireless-tools is installed.'
        }
    except Exception as e:
        print(f"Exception during WiFi scan: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': f'Error scanning WiFi: {str(e)}'
        }

def restart_mdns_service():
    """Restart mDNS service to update IP address"""
    print("Restarting mDNS service...")
    unregister_mdns_service()
    
    # Wait for IP address update
    import time
    max_retries = 10
    for i in range(max_retries):
        # Check if we have a valid non-loopback IP
        ip = get_local_ip()
        if ip and not ip.startswith("127."):
            print(f"✓ Network connection established (IP: {ip})")
            break
            
        print(f"Waiting for network connection... ({i+1}/{max_retries})")
        time.sleep(1)
        
    return register_mdns_service()

def configure_wifi(ssid, password):
    """Configure WiFi by writing to wpa_supplicant.conf"""
    try:
        # Escape double quotes in SSID and password by doubling them
        # wpa_supplicant requires quotes around SSID and PSK
        escaped_ssid = ssid.replace('"', '\\"')
        escaped_password = password.replace('"', '\\"')
        
        # Create wpa_supplicant config content with proper quotes
        config_content = f'''country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{escaped_ssid}"
    psk="{escaped_password}"
    key_mgmt=WPA-PSK
}}
'''

        # Write config file using Python's write with sudo via tee
        import subprocess

        # Use tee to write the content safely
        write_command = [
            'sudo', 'tee', WIFI_CONFIG_PATH
        ]

        result = subprocess.run(
            write_command,
            input=config_content,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return {
                'success': False,
                'error': f'Failed to write config: {result.stderr}'
            }

        print("WiFi configuration written to wpa_supplicant.conf")
        print(f"SSID: {ssid}")
        print(f"Password: {'*' * len(password)}")

        # Check if wlan0 interface exists
        print("Checking for WiFi interface (wlan0)...")
        interface_check = subprocess.run(
            ['ip', 'link', 'show', 'wlan0'],
            capture_output=True,
            text=True,
            timeout=3
        )

        if interface_check.returncode != 0:
            print("WARNING: WiFi interface wlan0 not found!")
            print("This is NORMAL when the Pi is in hotspot mode.")
            print("The Pi needs to reboot to exit hotspot mode and connect to WiFi.")
            print("WiFi configuration has been saved and will be applied on reboot.")

            return {
                'success': True,
                'message': 'WiFi configuration saved successfully. A system reboot is required to connect to the new network.',
                'reboot_required': True
            }

        print("WiFi interface wlan0 detected")
        # Try to bring up the interface if it's down
        print("Ensuring WiFi interface is up...")
        subprocess.run(
            ['sudo', 'ip', 'link', 'set', 'wlan0', 'up'],
            capture_output=True,
            timeout=3
        )

        # Try to reload wpa_supplicant configuration (will fail if offline/hotspot mode)
        print("Attempting to reload WiFi configuration...")
        reconfigure_result = subprocess.run(
            ['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if reconfigure_result.returncode == 0:
            print("WiFi configuration reloaded successfully")
            print(f"wpa_cli output: {reconfigure_result.stdout.strip()}")

            # Check if we can see the new SSID in scan results
            status_result = subprocess.run(
                ['sudo', 'iwconfig', 'wlan0'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if status_result.returncode == 0:
                print("WiFi interface status:")
                print(status_result.stdout[:200] + "..." if len(status_result.stdout) > 200 else status_result.stdout)

                # Update mDNS service with new IP
                if ZEROCONF_AVAILABLE:
                    restart_mdns_service()

                return {
                    'success': True,
                    'message': 'WiFi connected! mDNS service updated. You can now access the server at http://cubie.local:5001',
                    'reboot_required': False
                }
        else:
            # wpa_cli failed - config is saved, needs reboot to apply
            print(f"wpa_cli reconfigure failed: {reconfigure_result.stderr}")
            return {
                'success': True,
                'message': 'WiFi configuration saved. A reboot is required to connect to the new network.',
                'reboot_required': True
            }
    except FileNotFoundError:
        # wpa_cli not found - this is OK, just save the config
        print("wpa_cli not found - WiFi configuration saved for next restart")
        return {
            'success': True,
            'message': 'WiFi configuration saved. Please restart the server to connect to the new network.',
            'reboot_required': False
        }
    except subprocess.TimeoutExpired:
        print("Timeout trying to reload WiFi - configuration saved for restart")
        return {
            'success': True,
            'message': 'WiFi configuration saved. Please restart the server to connect to the new network.',
            'reboot_required': False
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': f'Error configuring WiFi: {str(e)}'
        }

def get_wifi_status():
    """Get current WiFi connection status using iwconfig or iw"""
    import subprocess
    import shutil

    # Helper to run command
    def run_cmd(cmd_list):
        try:
            return subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=5
            )
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error running {cmd_list[0]}: {e}")
            return None

    # 1. Try iwconfig (legacy but common)
    # Check common paths if not in PATH
    # Added sudo versions as fallback
    iwconfig_cmds = [
        ['iwconfig', 'wlan0'], 
        ['/sbin/iwconfig', 'wlan0'], 
        ['/usr/sbin/iwconfig', 'wlan0'],
        ['sudo', 'iwconfig', 'wlan0'],
        ['sudo', '/sbin/iwconfig', 'wlan0']
    ]
    
    for cmd in iwconfig_cmds:
        result = run_cmd(cmd)
        if result and result.returncode == 0:
            output = result.stdout
            if 'ESSID:' in output:
                try:
                    essid = output.split('ESSID:')[1].split('\n')[0].strip().strip('"')
                    
                    signal = "N/A"
                    if 'Signal level=' in output:
                        signal_part = output.split('Signal level=')[1].split()[0]
                        # Sometimes it is quality=xx/xx, sometimes level=-xx dBm
                        if 'dBm' in output or (signal_part.lstrip('-').isdigit() and int(signal_part) < 0): # Check if it's a negative number
                             signal = f"{signal_part} dBm"
                        else:
                             # quality is xx/xx
                             try:
                                 quality_val = int(signal_part.split('/')[0])
                                 if quality_val >= 70: signal = "Excellent"
                                 elif quality_val >= 40: signal = "Good"
                                 else: signal = "Fair"
                             except ValueError:
                                 signal = f"Quality: {signal_part}"
                                 
                    if essid and essid != 'off/any':
                        return {
                            'connected': True,
                            'ssid': essid,
                            'signal': signal,
                            'interface': 'wlan0'
                        }
                except Exception as e:
                    print(f"Error parsing iwconfig: {e}")
            
            # If we ran successfully but didn't return, it might be disconnected or parsing failed
            if 'ESSID:off/any' in output or 'ESSID:""' in output:
                 return {'connected': False, 'interface': 'wlan0'}

    # 2. Try iw (modern replacement)
    # iw dev wlan0 link
    # Added sudo versions as fallback
    iw_cmds = [
        ['iw', 'dev', 'wlan0', 'link'], 
        ['/usr/sbin/iw', 'dev', 'wlan0', 'link'], 
        ['/sbin/iw', 'dev', 'wlan0', 'link'],
        ['sudo', 'iw', 'dev', 'wlan0', 'link'],
        ['sudo', '/usr/sbin/iw', 'dev', 'wlan0', 'link']
    ]
    
    for cmd in iw_cmds:
        result = run_cmd(cmd)
        if result:
            if result.returncode == 0:
                output = result.stdout
                if 'Not connected' in output:
                    return {'connected': False, 'interface': 'wlan0'}
                
                try:
                    # Parse iw output
                    ssid = "Unknown"
                    signal = "N/A"
                    
                    for line in output.split('\n'):
                        line = line.strip()
                        if line.startswith('SSID:'):
                            ssid = line.split('SSID:')[1].strip().strip('"')
                        elif line.startswith('signal:'):
                            signal = line.split('signal:')[1].strip()
                    
                    if ssid != "Unknown":
                        return {
                            'connected': True,
                            'ssid': ssid,
                            'signal': signal,
                            'interface': 'wlan0'
                        }
                except Exception as e:
                    print(f"Error parsing iw: {e}")
            else:
                # iw failed (maybe interface down?)
                pass

    return {
        'connected': False,
        'error': 'Could not determine WiFi status (iwconfig/iw missing or failed)'
    }

def register_mdns_service():
    """Register mDNS service for network discovery"""
    global ZEROCONF_INSTANCE

    if not ZEROCONF_AVAILABLE:
        print("mDNS not available (zeroconf not installed)")
        print("Install with: pip install zeroconf")
        return None

    # Check network connectivity using the new function
    import time
    print("Checking network connectivity...")
    
    local_ip = get_local_ip()
    has_internet = check_internet_connection()
    
    if has_internet:
        print("✓ Internet connection available")
    elif local_ip and not local_ip.startswith("127."):
        print(f"✓ Local network connected (IP: {local_ip})")
        print("  ⚠ No internet access (Local Mode)")
    else:
        print("⚠ No network connection detected")
        print("  WiFi setup required. Visit /setup-wifi to configure WiFi")

    hostname = socket.gethostname()
    # Use the robust IP we just fetched
    ip_address = local_ip

    # The .local hostname will be based on the actual system's hostname
    server_local_hostname = f"{hostname}.local."
    service_display_name = f"{SERVICE_NAME} (on {hostname})" # Display actual system hostname

    if not ip_address or ip_address.startswith("127."):
        # Bail out early with a clear message instead of letting zeroconf throw
        print("⚠ Warning: Could not register mDNS service")
        print("  Error: No usable IP address available for mDNS (got loopback/offline)")
        print("  Troubleshooting:")
        print("  - Connect to WiFi or Ethernet and restart the service")
        print("  - Check network status: hostname -I")
        print("  - Verify wlan0 is up: ip link show wlan0")
        print(f"  You can still access the server at: http://{ip_address or 'localhost'}:{SERVICE_PORT}")
        print(f"  Or: http://{hostname}.local:{SERVICE_PORT}")
        return None

    try:
        # Create service info
        service_name = f"{SERVICE_NAME}.{SERVICE_TYPE}" # e.g., "cubie._http._tcp.local."
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
            server=server_local_hostname # This will be based on the system's hostname (e.g., "cubie.local" or "raspberrypi.local")
        )

        # Register the service
        zeroconf = Zeroconf()
        zeroconf.register_service(info)

        ZEROCONF_INSTANCE = zeroconf

        print(f"✓ mDNS service '{SERVICE_NAME}' registered: http://{server_local_hostname}:{SERVICE_PORT}")
        print(f"  - Service Display Name: {service_display_name}")
        print(f"  - Local IP: {ip_address}")
        print(f"  - System Hostname: {hostname}")
        print(f"  - Interface: wlan0")
        print(f"  - Access URLs:")
        print(f"    • http://{server_local_hostname}:{SERVICE_PORT}")
        print(f"    • http://{ip_address}:{SERVICE_PORT}")

        if hostname.lower() != SERVICE_NAME.lower():
            print(f"  - Note: If your system hostname ('{hostname}') differs from the preferred service name ('{SERVICE_NAME}'),")
            print(f"          you may need to access it at http://{hostname}.local:{SERVICE_PORT} or change your system hostname to '{SERVICE_NAME}'.")

        # Verify the service is registered on the correct interface
        import subprocess
        try:
            result = subprocess.run(
                ['avahi-browse', '-a', '-t'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'cubie-server' in result.stdout:
                print(f"  - mDNS service visible on network")
            else:
                print(f"  - Warning: Service not visible in avahi-browse")
        except:
            pass

        return zeroconf
    except Exception as e:
        import traceback
        error_msg = str(e) if str(e) else repr(e)
        print(f"⚠ Warning: Could not register mDNS service")
        print(f"  Error: {error_msg}")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Context:")
        print(f"    - Hostname: {hostname}")
        print(f"    - IP address: {ip_address}")
        print(f"    - Service name: {SERVICE_NAME}")
        print(f"  Traceback (most recent call last):")
        traceback.print_exc()
        print(f"  You can still access the server at: http://{ip_address}:{SERVICE_PORT}")
        print(f"  Or: http://{hostname}.local:{SERVICE_PORT}")
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
    
    # Ensure folders exist
    for folder in [MUSIC_FOLDER, PICTURES_FOLDER, DOCUMENTS_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            
    observer.schedule(event_handler, MUSIC_FOLDER, recursive=False)
    observer.schedule(event_handler, PICTURES_FOLDER, recursive=False)
    observer.schedule(event_handler, DOCUMENTS_FOLDER, recursive=False)
    
    observer.start()
    print(f"Started file monitor on music, pictures, and documents")
    return observer

if __name__ == '__main__':
    print("=" * 50)
    print("AIY Music Server - Pi Zero Music Server")
    print("=" * 50)

    get_exif_data("pictures/image_1765229010_A_cute_robot_painter_in_a_futu.jpg")

    print(f"Music folder: {MUSIC_FOLDER}")

    # Check internet connectivity on startup
    print("\nChecking internet connection...")
    if check_internet_connection():
        print("✓ Internet connection available")
    else:
        print("⚠ No internet connection detected")
        print("  WiFi setup is required to get internet access")
        print("  Visit http://localhost:5001/setup-wifi to configure WiFi")

    load_metadata()

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
