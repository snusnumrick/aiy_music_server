# Captive Portal Guide 🌐

## What is a Captive Portal?

A captive portal automatically redirects users to your music server when they connect to your Pi's WiFi. They don't need to know:
- The IP address
- The port number
- How to type URLs

**User Experience:**
1. User connects to Pi's WiFi network
2. Opens any browser (e.g., google.com)
3. **Automatically redirected to music server!** 🎵

## Setup

### During Installation
When running `sudo ./setup.sh`, you'll be asked:
```
Enable Captive Portal (redirects port 80 to music server)? (y/n)
```

Answer **y** to enable it.

### How It Works

1. **Setup Phase:**
   - Installs iptables-persistent
   - Enables IP forwarding
   - Creates initial redirect rule: port 80 → 5000
   - Saves rules for persistence

2. **Server Start:**
   - Server auto-detects available port (5000, 5001, 5002...)
   - Writes port to `/tmp/music_server_port.txt`
   - Automatically updates iptables redirect: port 80 → [actual port]
   - Users are redirected correctly!

3. **User Access:**
   - Connect to Pi's WiFi
   - Open any browser
   - Get redirected to music server ✨

## Requirements

### For Captive Portal to Work:
1. **Pi as WiFi Access Point** - Pi must create its own WiFi network
   ```bash
   # Install hostapd and dnsmasq
   sudo apt install hostapd dnsmasq
   ```

2. **Configure hostapd** - Create `/etc/hostapd/hostapd.conf`:
   ```ini
   interface=wlan0
   driver=nl80211
   ssid=MusicServer
   hw_mode=g
   channel=6
   wpa=2
   wpa_passphrase=music123
   wpa_key_mgmt=WPA-PSK
   ```

3. **Configure dnsmasq** - Edit `/etc/dnsmasq.conf`:
   ```ini
   interface=wlan0
   dhcp-range=192.168.4.10,192.168.4.100,12h
   dhcp-option=3,192.168.4.1
   dhcp-option=6,192.168.4.1
   ```

4. **Enable services:**
   ```bash
   sudo systemctl enable hostapd dnsmasq
   sudo systemctl start hostapd dnsmasq
   ```

## Manual Configuration

If you need to manually configure the captive portal:

```bash
# Run the configuration script
sudo bash ./configure_captive_portal.sh
```

This will:
- Detect the current server port
- Update iptables redirect rule
- Save the configuration

## How to Test

1. Connect to Pi's WiFi network
2. Try to visit any website (e.g., google.com)
3. You should be redirected to the music server!

## Troubleshooting

### Port 80 redirect not working?

```bash
# Check iptables rules
sudo iptables -t nat -L PREROUTING -n

# Check if rule exists for port 80
sudo iptables -t nat -L PREROUTING -n | grep 80

# Manually add rule
sudo iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 5000

# Save rules
sudo iptables-save
```

### Can't access port 80?

```bash
# Check what's using port 80
sudo netstat -tlnp | grep :80

# If Apache or nginx is using it, stop them
sudo systemctl stop apache2
sudo systemctl stop nginx
```

### Server not updating redirect?

```bash
# Check if port file exists
cat /tmp/music_server_port.txt

# Run manual configuration
sudo bash ./configure_captive_portal.sh
```

## Benefits

✅ **Zero configuration for users** - Just connect to WiFi
✅ **Auto-adaptive** - Works with any server port
✅ **Persistent** - Rules survive reboots
✅ **Simple** - No apps or manual URL entry needed

## When NOT to Use Captive Portal

- Pi connects to existing WiFi (not creating its own)
- Users need to access other websites while connected
- You prefer direct URL access (cubie:5000)

## Alternative: Direct Access

If you don't use captive portal, users can still access the server:

**Android:**
```
http://cubie:5000
```

**Desktop:**
```
http://cubie.local:5000
```

Or use the IP address shown on Pi startup.
