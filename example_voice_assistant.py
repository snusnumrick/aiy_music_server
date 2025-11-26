#!/usr/bin/env python3
"""
Example: Voice Assistant Integration with cubie-server

This script demonstrates how a voice assistant can:
1. Discover the music folder path
2. Download and save music files
3. Trigger metadata refresh

Run this script to see how it works:
    python3 example_voice_assistant.py
"""

import requests
import os
import sys
from pathlib import Path

class CubieServerClient:
    """Client for interacting with cubie-server music server"""

    def __init__(self, server_url='http://cubie-server.local:5001'):
        self.server_url = server_url
        self.config = None
        self.music_folder = None

    def discover_server(self):
        """Discover cubie-server and get configuration"""
        try:
            print(f"🔍 Discovering cubie-server at {self.server_url}...")
            response = requests.get(f'{self.server_url}/api/config', timeout=5)

            if response.status_code == 200:
                self.config = response.json()
                self.music_folder = self.config['music_folder']
                print(f"✅ Server discovered!")
                print(f"   Service: {self.config['service_name']}")
                print(f"   Music folder: {self.music_folder}")
                return True
            else:
                print(f"❌ Server returned status {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to server: {e}")
            print(f"\n💡 Make sure cubie-server is running:")
            print(f"   cd /home/pi/music_server")
            print(f"   source music_server/bin/activate")
            print(f"   python app.py")
            return False

    def get_music_folder(self):
        """Get the path to the music folder"""
        if not self.music_folder:
            if not self.discover_server():
                return None
        return self.music_folder

    def download_music(self, url, filename=None):
        """Download music from URL to the music folder"""
        if not self.music_folder:
            print("❌ Music folder not discovered")
            return None

        # Determine filename
        if not filename:
            filename = url.split('/')[-1]
            if '?' in filename:
                filename = filename.split('?')[0]

        # Ensure .mp3 extension
        if not filename.endswith('.mp3'):
            filename += '.mp3'

        # Sanitize filename
        filename = self._sanitize_filename(filename)
        filepath = os.path.join(self.music_folder, filename)

        # Download file
        print(f"\n📥 Downloading from: {url}")
        print(f"💾 Saving to: {filepath}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            file_size = os.path.getsize(filepath)
            print(f"✅ Downloaded {filename} ({file_size} bytes)")

            return filepath

        except Exception as e:
            print(f"❌ Download failed: {e}")
            return None

    def refresh_library(self):
        """Tell cubie-server to refresh its music library"""
        try:
            response = requests.post(f'{self.server_url}/api/refresh', timeout=5)
            if response.status_code == 200:
                result = response.json()
                print(f"\n🔄 Music library refreshed! ({result['count']} tracks)")
                return True
            else:
                print(f"⚠️ Refresh returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️ Could not refresh library: {e}")
            return False

    def list_music(self):
        """List all music in the server"""
        try:
            response = requests.get(f'{self.server_url}/api/music', timeout=5)
            if response.status_code == 200:
                music_list = response.json()
                print(f"\n📚 Music Library ({len(music_list)} tracks):")
                for i, track in enumerate(music_list[:10], 1):
                    print(f"   {i}. {track['title']} - {track['artist']}")
                if len(music_list) > 10:
                    print(f"   ... and {len(music_list) - 10} more")
                return music_list
            return []
        except Exception as e:
            print(f"⚠️ Could not fetch music list: {e}")
            return []

    def _sanitize_filename(self, filename):
        """Remove invalid characters from filename"""
        # Remove invalid characters
        invalid = '<>:"/\\|?*'
        for char in invalid:
            filename = filename.replace(char, '_')

        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext

        return filename


def main():
    """Demonstration of voice assistant integration"""
    print("=" * 70)
    print("  Voice Assistant Integration Example")
    print("  (cubie-server music server)")
    print("=" * 70)

    # Create client
    client = CubieServerClient()

    # Discover server
    if not client.discover_server():
        sys.exit(1)

    # Get music folder
    music_folder = client.get_music_folder()
    print(f"\n📁 Music folder: {music_folder}")

    # Check if folder is writable
    if os.access(music_folder, os.W_OK):
        print("✅ Music folder is writable")
    else:
        print(f"❌ No write permission for {music_folder}")
        print(f"   Try: sudo chown -R $USER:$USER {music_folder}")

    # List current music
    client.list_music()

    # Example: Download a test file (if you have a URL)
    print("\n" + "=" * 70)
    print("To download music from voice assistant:")
    print("=" * 70)
    print("""
# Example 1: Direct download
client = CubieServerClient()
client.discover_server()

# User says: "Download Shape of You"
url = "https://example.com/shape_of_you.mp3"
filepath = client.download_music(url, "Shape of You.mp3")
client.refresh_library()

# Example 2: Using in voice command handler
def handle_download_command(song_name, song_url):
    client = CubieServerClient()
    if client.discover_server():
        filepath = client.download_music(song_url, f"{song_name}.mp3")
        if filepath:
            client.refresh_library()
            return f"Downloaded {song_name}"
        return "Download failed"
    return "Cannot connect to music server"
    """)

    # Test API endpoints
    print("\n" + "=" * 70)
    print("Testing API Endpoints")
    print("=" * 70)

    try:
        # Test /api/health
        response = requests.get(f'{client.server_url}/api/health', timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"\n✅ Health check: {health['status']}")
            print(f"   Tracks: {health['files_count']}")
            print(f"   mDNS: {health['mdns_enabled']}")

        # Test /api/config
        response = requests.get(f'{client.server_url}/api/config', timeout=5)
        if response.status_code == 200:
            config = response.json()
            print(f"\n✅ Configuration retrieved")
            print(f"   Server URL: {config['server_url']}")
            print(f"   Service Name: {config['service_name']}")

    except Exception as e:
        print(f"⚠️ API test failed: {e}")

    print("\n" + "=" * 70)
    print("✅ Integration example complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Integrate this code into your voice assistant")
    print("  2. Call client.discover_server() on startup")
    print("  3. Use client.download_music() when user requests downloads")
    print("  4. Always call client.refresh_library() after downloading")
    print("\nSee VOICE_ASSISTANT_INTEGRATION.md for complete guide")


if __name__ == '__main__':
    main()
