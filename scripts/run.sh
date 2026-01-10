#!/bin/bash

# get path to project root (one level up from scripts)
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# Navigate to the project directory
cd "${PROJECT_ROOT}" || exit

# Create logs directory if it doesn't exist
mkdir -p "${PROJECT_ROOT}/logs"

# Enhanced WiFi detection with better reliability
# Fix: Improved network detection to verify WiFi is actually connected
max_attempts=60
attempt=1
echo "Waiting for network connection..."

# Function to check if we have a valid IP on WiFi
check_wifi_connection() {
    # Check if wlan0 interface exists and is up
    if ! ip link show wlan0 up >/dev/null 2>&1; then
        return 1
    fi

    # Get IP address
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

    # Check if we have a non-loopback IP
    if [ -z "$LOCAL_IP" ] || [ "$LOCAL_IP" = "127.0.0.1" ]; then
        return 1
    fi

    # Verify the IP is actually on wlan0 (not just any interface)
    if ip addr show wlan0 2>/dev/null | grep -q "$LOCAL_IP"; then
        return 0
    fi

    return 1
}

# Function to check for any network connection (fallback for ethernet)
check_any_network() {
    LOCAL_IP=$(hostname -I 2>/dev/null | grep -v '^127\.' | awk '{print $1}')

    if [ -n "$LOCAL_IP" ]; then
        return 0
    fi

    return 1
}

# Main network wait loop
while true; do
    # First, try to detect WiFi specifically
    if check_wifi_connection; then
        echo "✓ WiFi connected (IP: $LOCAL_IP)"
        break
    fi

    # If WiFi check fails but wlan0 exists, we're waiting for WiFi
    if ip link show wlan0 >/dev/null 2>&1; then
        if [ $((attempt % 6)) -eq 0 ]; then
            echo "Waiting for WiFi connection... attempt $attempt"
        fi
    else
        # No WiFi interface, check for ethernet
        if check_any_network; then
            echo "✓ Ethernet connected (IP: $LOCAL_IP)"
            break
        fi

        if [ $((attempt % 6)) -eq 0 ]; then
            echo "Waiting for network... attempt $attempt"
        fi
    fi

    if [ $attempt -ge $max_attempts ]; then
        echo "⚠ Warning: No network detected after $max_attempts attempts"
        echo "  This may be normal in some configurations. Starting server anyway..."
        break
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
