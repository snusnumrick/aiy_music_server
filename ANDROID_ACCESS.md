# Android Access Guide 🎵

## How Android Finds the Server

Android hostname resolution varies a lot by device/browser. In particular, `.local` (mDNS) often works on macOS/iOS but may not resolve in Android browsers, especially on hotspot/local-only networks.

### ✅ **Easiest Method** (Recommended)
Just type in your Android browser:
```
http://cubie:5000
```

This works well in hotspot mode because the hotspot DNS (`dnsmasq`) can resolve `cubie` to the Pi’s hotspot IP.

### Alternative Methods
```
http://192.168.50.28:5000
http://cubie.local:5000
```

## Why This Works

- **Hotspot DNS (dnsmasq)**: Provides `cubie` → Pi IP mapping
- **Avahi / Zeroconf**: Provides mDNS service discovery (more reliable on macOS)

## Testing mDNS

On your Pi, verify services are registered:
```bash
avahi-browse -a -t | grep -i cubie
```

You should see:
- `cubie._http._tcp.local`
- `cubie._workstation._tcp.local`

## Troubleshooting

If Android can’t open `http://cubie:5000`:

1. **Check WiFi**: Ensure phone and Pi are on same network
2. **Wait 30 seconds**: mDNS needs time to propagate
3. **Restart avahi**:
   ```bash
   sudo systemctl restart avahi-daemon
   ```
4. **Disable Private DNS** (Android Settings → Network & Internet → Private DNS → Off/Automatic)
5. **Use IP address**: `http://<pi-ip>:5000`

## Non-Technical User Instructions

### For Your Phone:
1. Connect to same WiFi as Pi
2. Open browser (Chrome/Samsung Internet)
3. Type: **http://cubie:5000**
4. Press Go
5. Enjoy your music! 🎶

### No need to:
- Remember IP addresses
- Install apps
- Configure anything
