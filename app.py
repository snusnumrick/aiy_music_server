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

# Configuration
MUSIC_FOLDER = os.path.join(os.path.dirname(__file__), 'music')
METADATA_CACHE = []
FILE_CHANGE_LOCK = threading.Lock()

# mDNS Configuration
ZEROCONF_INSTANCE = None
SERVICE_NAME = "cubie-server"
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

        if not event.src_path.endswith('.mp3'):
            return

        print(f"File created: {event.src_path}")
        self._trigger_reload()

    def on_deleted(self, event):
        if event.is_directory:
            return

        if not event.src_path.endswith('.mp3'):
            return

        print(f"File deleted: {event.src_path}")
        self._trigger_reload()

    def on_modified(self, event):
        if event.is_directory:
            return

        if not event.src_path.endswith('.mp3'):
            return

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
            print("Metadata reload complete.")

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

@app.route('/api/refresh', methods=['POST'])
def refresh_metadata():
    """Manually trigger metadata reload"""
    print("Received request: POST /api/refresh")
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

@app.route('/api/wifi/networks')
def wifi_networks():
    """Get list of available WiFi networks"""
    result = scan_wifi_networks()
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/api/wifi/configure', methods=['POST'])
def wifi_configure():
    """Configure WiFi with provided credentials"""
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
        if check_internet_connection():
            print("✓ Network connection established")
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
                print(f"wpa_cli reconfigure failed (likely offline or in hotspot mode)")
                print(f"This is normal - configuration will take effect on server restart")

                return {
                    'success': True,
                    'message': 'WiFi configuration saved. Please restart the music server to connect to the new network.',
                    'reboot_required': False
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
    """Get current WiFi connection status"""
    try:
        import subprocess
        result = subprocess.run(
            ['iwconfig', 'wlan0'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return {
                'connected': False,
                'error': 'Could not get WiFi status'
            }

        output = result.stdout

        # Check if connected
        if 'ESSID:' in output:
            essid_line = [line for line in output.split('\n') if 'ESSID:' in line][0]
            essid = essid_line.split('ESSID:')[1].strip()

            if essid and essid != 'off/any':
                # Get signal strength
                signal_line = [line for line in output.split('\n') if 'Signal level=' in line][0]
                signal = signal_line.split('Signal level=')[1].split(' ')[0]

                return {
                    'connected': True,
                    'ssid': essid,
                    'signal': signal,
                    'interface': 'wlan0'
                }

        return {
            'connected': False,
            'interface': 'wlan0'
        }

    except Exception as e:
        return {
            'connected': False,
            'error': str(e)
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
    if check_internet_connection():
        print("✓ Internet connection available")
    else:
        print("⚠ No internet connection detected")
        print("  WiFi setup required. Visit /setup-wifi to configure WiFi")

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
        print(f"  - Interface: wlan0")
        print(f"  - Access URLs:")
        print(f"    • http://{server_hostname}:{SERVICE_PORT}")
        print(f"    • http://{ip_address}:{SERVICE_PORT}")

        if hostname != SERVICE_NAME:
            print(f"  - Note: Using {hostname}.local (was renamed from {SERVICE_NAME})")

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