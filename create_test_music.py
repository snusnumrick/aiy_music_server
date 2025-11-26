#!/usr/bin/env python3
"""
Create test MP3 files with metadata for testing the AIY Music Server.
This script generates sample MP3 files with ID3 tags for testing purposes.

Prerequisites:
- ffmpeg must be installed and in PATH
  macOS: brew install ffmpeg
  Raspberry Pi: sudo apt install ffmpeg

The script creates 8 test MP3 files with various metadata scenarios,
including tracks with and without lyrics.
"""

import os
import sys
import subprocess
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, USLT

def create_test_mp3(filepath, title, artist, lyrics):
    """Create a test MP3 file with metadata using ffmpeg"""

    try:
        subprocess.run([
            'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-t', '5', '-c:a', 'libmp3lame', '-y', filepath
        ], check=True, capture_output=True)

        audio = MP3(filepath, ID3=ID3)

        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))

        if lyrics:
            audio.tags.add(USLT(encoding=3, text=lyrics))

        audio.save()
        print(f"Created: {os.path.basename(filepath)}")
        return True
    except Exception as e:
        print(f"Error creating {filepath}: {e}")
        return False

def main():
    music_dir = os.path.join(os.path.dirname(__file__), 'music')

    if not os.path.exists(music_dir):
        os.makedirs(music_dir)
        print(f"Created music directory: {music_dir}")

    test_files = [
        {
            'filename': 'morning_greeting.mp3',
            'title': 'Morning Greeting',
            'artist': 'Voice Assistant',
            'lyrics': '''Good morning! How can I help you today?
I hope you slept well.
Let me know what you need!'''
        },
        {
            'filename': 'evening_summary.mp3',
            'title': 'Evening Summary',
            'artist': 'Voice Assistant',
            'lyrics': '''Here's your day summary:
- 5 messages received
- 3 meetings scheduled
- 2 tasks completed
Have a great evening!'''
        },
        {
            'filename': 'weather_update.mp3',
            'title': 'Weather Update',
            'artist': 'Weather Bot',
            'lyrics': '''Today's weather:
Sunny, 72°F
Light breeze from the west
Perfect for a walk!'''
        },
        {
            'filename': 'reminder_alarm.mp3',
            'title': 'Reminder: Take Medication',
            'artist': 'Reminder Service',
            'lyrics': '''It's time to take your medication.
Don't forget to drink water afterwards.
Stay healthy!'''
        },
        {
            'filename': 'task_complete.mp3',
            'title': 'Task Completed Successfully',
            'artist': 'Productivity App',
            'lyrics': '''Great job! You've completed:
"Finish quarterly report"
Time spent: 2 hours 15 minutes
Next: Review and submit'''
        },
        {
            'filename': 'news_brief.mp3',
            'title': 'Daily News Brief',
            'artist': 'News Reader',
            'lyrics': '''Top headlines today:
1. Tech company announces new AI product
2. Local community hosts charity event
3. Scientists discover new species
More details available online.'''
        },
        {
            'filename': 'no_lyrics.mp3',
            'title': 'Silent Track',
            'artist': 'Unknown Artist',
            'lyrics': ''
        },
        {
            'filename': 'long_metadata.mp3',
            'title': 'This is a very long song title that might cause display issues on mobile devices',
            'artist': 'Artist with a Very Long Name That Could Be Problematic',
            'lyrics': '''This is a very long set of lyrics that should be truncated in the preview but fully visible in the modal dialog.

Line after line of content to test how the application handles extensive text.

More lines...
Even more lines...
Testing scrolling behavior...

The quick brown fox jumps over the lazy dog.
Pack my box with five dozen liquor jugs.
How vexingly quick daft zebras jump!

End of lyrics.'''
        }
    ]

    created = 0
    failed = 0

    print("\n" + "=" * 60)
    print("Creating Test MP3 Files")
    print("=" * 60 + "\n")

    for file_info in test_files:
        filepath = os.path.join(music_dir, file_info['filename'])

        if os.path.exists(filepath):
            print(f"Skipping: {file_info['filename']} (already exists)")
            created += 1
            continue

        if create_test_mp3(filepath, file_info['title'], file_info['artist'], file_info['lyrics']):
            created += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"Summary: {created} created, {failed} failed")
    print("=" * 60)
    print(f"\nTest files created in: {music_dir}")
    print("\nNext steps:")
    print("1. Start the server: python app.py")
    print("2. Open browser to: http://localhost:5000")
    print("3. Add more MP3 files to the music/ folder")
    print("=" * 60 + "\n")

    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
