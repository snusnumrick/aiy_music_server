# Android Access Guide 🎵

## How Android Finds the Server

Android automatically appends `.local` to hostnames, so you can use either:

### ✅ **Easiest Method** (Recommended)
Just type in your Android browser:
```
http://cubie:5000
```
Android automatically converts this to `http://cubie.local:5000`

### Alternative Methods
```
http://cubie.local:5000
http://192.168.50.28:5000
```

## Why This Works

- **Android mDNS behavior**: Auto-appends `.local` to bare hostnames
- **Avahi daemon**: Provides mDNS service on the Pi
- **Workstation service**: Advertised for Android compatibility

## Testing mDNS

On your Pi, verify services are registered:
```bash
avahi-browse -a -t | grep -i cubie
```

You should see:
- `cubie._http._tcp.local`
- `cubie._workstation._tcp.local`

## Troubleshooting

If Android can't find `cubie`:

1. **Check WiFi**: Ensure phone and Pi are on same network
2. **Wait 30 seconds**: mDNS needs time to propagate
3. **Restart avahi**:
   ```bash
   sudo systemctl restart avahi-daemon
   ```
4. **Use IP address**: Check router admin page for Pi's IP

## Non-Technical User Instructions

### For Your Phone:
1. Connect to same WiFi as Pi
2. Open browser (Chrome/Samsung Internet)
3. Type: **cubie:5000**
4. Press Go
5. Enjoy your music! 🎶

### No need to:
- Remember IP addresses
- Install apps
- Type ".local"
- Configure anything
