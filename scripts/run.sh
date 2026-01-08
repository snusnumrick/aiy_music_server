#!/bin/bash

# get path to project root (one level up from scripts)
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# Navigate to the project directory
cd "${PROJECT_ROOT}" || exit

# Create logs directory if it doesn't exist
mkdir -p "${PROJECT_ROOT}/logs"

# Wait for local network connection (IP address on any interface)
# This allows the server to work in both WiFi and hotspot modes
max_attempts=60
attempt=1
echo "Waiting for network connection..."
while true; do
    # Check if we have a non-loopback IP address
    LOCAL_IP=$(hostname -I 2>/dev/null | grep -v '^127\.' | awk '{print $1}')
    if [ -n "$LOCAL_IP" ]; then
        echo "✓ Local network connected (IP: $LOCAL_IP)"
        break
    fi

    if [ $attempt -ge $max_attempts ]; then
        echo "⚠ Warning: No local network detected after $max_attempts attempts"
        echo "  This may be normal in some configurations. Starting server anyway..."
        break
    fi

    if [ $((attempt % 6)) -eq 0 ]; then
        echo "Waiting for network... attempt $attempt"
    fi
    sleep 5
    attempt=$((attempt + 1))
done

# Try to pull latest changes (optional - don't fail if no internet)
echo "Checking for updates..."
if ping -c 1 github.com >/dev/null 2>&1; then
    echo "Internet available, pulling latest changes..."
    if git pull; then
        echo "✓ Repository updated"
    else
        echo "⚠ Could not update repository (continuing anyway)"
    fi
else
    echo "⚠ No internet connection - skipping repository update"
    echo "  (This is normal in hotspot mode)"
fi

# Run the Python script with new logging flags
echo "Starting music server..."
${PROJECT_ROOT}/music_server/bin/python ${PROJECT_ROOT}/app.py
