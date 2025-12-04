# WiFi Setup Guide

This guide explains the WiFi configuration feature added to the music server.

## Overview

The music server now includes a built-in WiFi setup page that allows you to configure WiFi connection when the server has no internet access. This is especially useful for initial setup on Raspberry Pi Zero W.

## How It Works

1. **Startup Check**: When the server starts, it checks for internet connectivity
2. **Auto-Redirect**: If no internet is detected, accessing the root URL (`/`) automatically redirects to the WiFi setup page
3. **Captive Portal (Optional)**: If enabled, devices connecting to the hotspot will be automatically redirected to the WiFi setup page when they try to access any website.
4. **Manual Access**: You can also manually visit `/setup-wifi` to configure WiFi
5. **Network Scan**: The setup page scans for available WiFi networks and displays them
6. **Configuration**: Select a network, enter the password, and click "Connect"
7. **Restart**: After successful configuration, restart the server to connect to the new network

## Captive Portal Feature (Auto-Redirect Hotspot)

When your Pi Zero is acting as a WiFi hotspot (e.g., during initial setup), you can configure it to automatically redirect connected devices to the WiFi setup page. This is known as a "Captive Portal" and will typically trigger a "Sign in to WiFi" notification on phones and laptops.

### How it works:
- Any HTTP traffic (port 80) from devices connected to the Pi's hotspot will be transparently redirected to the Flask server's port 5001.
- The Flask server's `app.py` has a catch-all route that redirects any unexpected requests (like `google.com` or `connectivitycheck.gstatic.com`) to the `/setup-wifi` page if the server is offline.

### How to Enable Captive Portal:
The easiest way is to use the main setup script:
1. Run `sudo ./setup.sh`
2. Answer **"y"** when asked "Enable Captive Portal?".

Alternatively, you can manually configure it:
1. Enable IP forwarding: `echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward`
2. Redirect port 80 to 5001: `sudo iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 5001`
3. Install `iptables-persistent` to save rules.

### Required System Packages (for Captive Portal)

```bash
sudo apt-get update
sudo apt-get install -y iptables-persistent
```

## Required System Packages

Before running the server with WiFi functionality, install these packages on your Raspberry Pi:

```bash
sudo apt-get update
sudo apt-get install -y wireless-tools wpasupplicant

## Usage

### Initial Setup (No WiFi)

1. Start the server:
   ```bash
   python3 app.py
   ```

2. Access the WiFi setup page from a browser:
   - If offline: You'll be automatically redirected to `/setup-wifi`
   - Manual: Visit `http://YOUR-PI-IP:5001/setup-wifi`

3. Select your WiFi network from the dropdown

4. Enter the WiFi password (if required)

5. Click "Connect"

6. After successful configuration, click "Restart Server"

7. The server will restart itself and reconnect to WiFi

8. Access the music server at `http://cubie.local:5001` or `http://YOUR-PI-IP:5001`

### WiFi Setup Page Features

- **Network List**: Shows all available WiFi networks with signal strength indicators
- **Security Info**: Displays network security type (Open, WPA/WPA2, WPA2)
- **Hidden Networks**: Detects and lists hidden networks (shown as "[Hidden Network]")
- **Manual SSID Entry**: For hidden networks, you'll be prompted to enter the SSID manually
- **Password Toggle**: Click the eye icon to show/hide password
- **Auto-Scan**: Automatically scans for networks on page load
- **Mobile-Friendly**: Responsive design optimized for phone access

### Connecting to Phone Hotspots

Phone hotspots often have hidden SSIDs by default. When you see "[Hidden Network]" in the list:

1. Select "[Hidden Network]" from the dropdown
2. Enter your phone hotspot name when prompted (e.g., "iPhone", "Android Hotspot")
3. Enter the hotspot password
4. Click "Connect"

**Alternative**: You can also disable "Hide network name" or "Broadcast SSID" in your phone's hotspot settings to make it appear normally in the list.

## Offline-First Design

The WiFi setup page uses **local assets** instead of CDN links:

- **Tailwind CSS**: `/static/tailwind.min.css` (403KB)
- **Lucide Icons**: `/static/lucide.min.js` (560KB)

This ensures the page works even when there's no internet connection.

## API Endpoints

The WiFi setup uses these API endpoints:

- `GET /setup-wifi` - Serves the WiFi setup HTML page
- `GET /api/wifi/networks` - Scans and returns available WiFi networks
- `POST /api/wifi/configure` - Configures WiFi with provided credentials
- `GET /api/wifi/status` - Returns current WiFi connection status
- `POST /api/wifi/restart` - Restarts the Flask server to reconnect to WiFi
- `POST /api/wifi/reboot` - Reboots the Raspberry Pi to enable WiFi adapter

## WiFi Configuration Details

The server uses **wpa_supplicant** for WiFi configuration:

- Config file location: `/etc/wpa_supplicant/wpa_supplicant.conf`
- Country code: `US` (configurable in `app.py`)
- Security: WPA-PSK (WPA/WPA2)
- Configuration reload: `wpa_cli -i wlan0 reconfigure`

## How WiFi Connection Works

When you configure WiFi, the server:

1. **Writes config file** to `/etc/wpa_supplicant/wpa_supplicant.conf` with your SSID and password
2. **Attempts to reload** using `wpa_cli -i wlan0 reconfigure` (if wpa_supplicant is running)
3. **If reconfigure succeeds**: WiFi attempts to reconnect immediately
4. **If reconfigure fails** (offline, hotspot mode, or wpa_cli not available): Config is saved for next restart
5. **Restart the server** to connect to the new WiFi network

### Important Notes:

**wpa_cli reconfigure only works when:**
- Pi is already connected to a WiFi network managed by wpa_supplicant
- wpa_cli command is available
- The WiFi interface is active

**wpa_cli reconfigure will FAIL when:**
- Pi is offline (no WiFi connection)
- Pi is connected to phone hotspot (may not use wpa_supplicant)
- wpa_supplicant is not running

**When wpa_cli fails**, this is **normal and expected**. The config file is still saved correctly, and restarting the server will connect to the new WiFi network.

### Always Restart After Configuration:

Regardless of whether wpa_cli succeeds or fails, you should **always click "Restart Server"** after configuring WiFi. This ensures:
- Fresh connection to the new network
- New IP address from the new network
- Clean state for the music server

### Hotspot Mode and wlan0 Interface:

When the Pi is in **hotspot mode** (acting as an access point), the wlan0 interface is **not available** for WiFi scanning. This is **completely normal** because:

1. Hotspot mode uses the WiFi adapter in **AP mode** (Access Point)
2. WiFi scanning requires **STA mode** (Station/Client)
3. These modes are **mutually exclusive** - can't do both at once
4. **Reboot is required** to exit hotspot mode and switch to STA mode

**Expected Flow:**

```
Pi boots → No WiFi config → Creates hotspot → User connects → Visits /setup-wifi
     ↓
Configure WiFi → Check wlan0 → Missing (expected!) → Save config → Show "Reboot Now"
     ↓
User clicks reboot → Pi reboots → Exits hotspot mode → Connects to WiFi
```

**What you'll see:**

- Success message: "WiFi configuration saved. The system will reboot to connect to the new network."
- "Reboot Now" button appears automatically

**Manual alternative:**
```bash
# Instead of clicking the button, you can reboot manually:
sudo reboot
```

## Troubleshooting

### "iwlist command not found"
```bash
sudo apt-get install wireless-tools
```

### "Failed to write config"
- Ensure the server is running with appropriate permissions
- Check that the `pi` user has sudo privileges
- Verify `/etc/wpa_supplicant/` is writable

### WiFi not connecting after configuration
1. Check the config file: `sudo cat /etc/wpa_supplicant/wpa_supplicant.conf`
2. Verify SSID and password are correct
3. Restart the network service: `sudo systemctl restart dhcpcd`
4. Check WiFi adapter status: `iwconfig`

### No networks found
1. Ensure WiFi adapter is enabled: `sudo ifconfig wlan0 up`
2. Check WiFi adapter exists: `iwconfig`
3. Ensure you're within range of WiFi networks

### Phone hotspot not appearing
Phone hotspots often have hidden SSIDs by default. You'll see "[Hidden Network]" in the list:

1. **Option A - Use Hidden Network**:
   - Select "[Hidden Network]" from dropdown
   - Enter your hotspot name when prompted
   - Enter the hotspot password
   - Click "Connect"

2. **Option B - Make hotspot visible**:
   - Go to your phone's hotspot settings
   - Disable "Hide network name" or "Broadcast SSID"
   - The hotspot will appear with its actual name

3. **Check 2.4GHz support**:
   - Raspberry Pi Zero W only supports 2.4GHz
   - Ensure your phone hotspot is set to 2.4GHz or dual-band
   - Some phones default to 5GHz only

### Permission Denied Errors
Some WiFi operations require sudo access. The server handles this automatically for:
- Scanning networks (`sudo iwlist wlan0 scan`)
- Writing config (`sudo bash -c 'echo...'`)
- Restarting services (`sudo systemctl restart dhcpcd`)

## Example WiFi Config File

After successful configuration, `/etc/wpa_supplicant/wpa_supplicant.conf` will look like:

```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourNetworkName"
    psk="YourPassword"
    key_mgmt=WPA-PSK
}
```

## File Changes

The following files were added/modified:

### New Files
- `static/wifi-setup.html` - WiFi setup page
- `static/wifi-setup.js` - WiFi setup functionality
- `static/tailwind.js` - Local Tailwind CSS
- `static/lucide.min.js` - Local Lucide icons

### Modified Files
- `app.py` - Added WiFi helper functions and API endpoints
- `static/index.html` - Updated to use local assets and new Tailwind config
- `static/support.html` - Updated to use local assets

## Compatibility

- **Target Platform**: Raspberry Pi Zero W
- **OS**: Raspberry Pi OS (Lite or Full)
- **Python**: 3.x
- **WiFi Adapter**: `wlan0` (standard)

## Security Notes

- WiFi passwords are temporarily stored in the config file
- Passwords are sent via HTTPS (if configured) or HTTP (local network only)
- After server restart, the setup page is no longer accessible unless offline again
- The config file requires sudo to modify (security feature)

## Future Enhancements

Potential improvements for future versions:

- Multiple network support (backup networks)
- WPS (WiFi Protected Setup) support
- Guest network configuration
- Advanced security options (WPA3, enterprise)
- Connection quality monitoring
- Automatic reconnection on disconnect
