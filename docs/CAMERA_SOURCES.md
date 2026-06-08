# Camera Source Guide

> Which input should I use? This page compares all four options so you can
> make the right choice for your setup.

Set your choice in `config.yaml`:

```yaml
camera:
  source: sample   # sample | usb | integrated | ipcam
```

---

## Quick-pick table

| | `sample` | `usb` | `integrated` | `ipcam` |
|---|---|---|---|---|
| **Hardware needed** | None | USB camera | Built-in webcam | Android/iOS phone |
| **Works in WSL2** | ✅ Yes | ⚠️ Needs usbipd-win | ⚠️ Needs usbipd-win | ✅ Yes |
| **Works in native Linux** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Works in Windows** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Latency** | None (static) | ~30–80 ms | ~30–80 ms | ~100–300 ms (WiFi) |
| **Setup effort** | Zero | Low | Low | Medium |
| **Image quality** | Fixed (synthetic) | High | Medium | Medium–High |
| **Real-time content** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Best for** | First run, CI, teaching | Local dev, robotics | Quick test | WSL2, remote rigs |

---

## `sample` — offline image loop (default)

```yaml
camera:
  source: sample
  samples_dir: "samples"   # folder of JPG/PNG files to loop
```

**How it works:** `SampleSource` reads every image in `samples/` and loops
them indefinitely at `target_fps`. No camera, no network — it just works.

**When to use:**
- First time running the repo (no hardware needed)
- Classroom / workshop environments where cameras aren't available
- CI/CD pipelines and automated testing
- Demos where you want deterministic, repeatable output

**Risks / limitations:**
- Images are static — the scene never changes unless you add more files
- YOLO will detect the same objects every loop; QR reads are deterministic
- Not suitable for real asset-tracking in production

**Add your own samples:**

```bash
# Drop any JPG/PNG files into samples/ — they'll be picked up automatically
cp my_desk_photo.jpg samples/

# Or regenerate the built-in set (edit ASSETS[] in generate_samples.py first)
python generate_samples.py
```

---

## `usb` — USB camera

```yaml
camera:
  source: usb
  index: 0         # 0 = first USB camera; try 1, 2 … if you have multiple
  target_fps: 15
  width: 640
```

**How it works:** `UsbCameraCapture` opens the device with
`cv2.VideoCapture(index)`. OpenCV handles driver communication transparently.

**When to use:**
- Native Linux or Windows environments
- Lowest latency for a dedicated camera (no WiFi hop)
- Robotics rigs with a proper machine-vision camera

**WSL2 caveat — USB passthrough required:**

WSL2 does not expose USB devices by default. You must forward the camera
using **usbipd-win**. Without this, you will see the error:

```
[error] Cannot open camera index 0. On WSL2 you need usbipd-win passthrough.
```

### usbipd-win full walkthrough

**One-time setup (do this once per machine):**

```powershell
# 1. Open Windows PowerShell as Administrator (right-click → "Run as administrator")

# 2. Install usbipd-win
winget install --interactive --exact dorssel.usbipd-win

# 3. Plug in your USB camera, then list all USB devices
usbipd list
# Example output:
# BUSID  VID:PID    DEVICE                          STATE
# 1-5    046d:0825  Logitech HD Webcam C270          Not shared
# 2-3    0bda:5539  Integrated Webcam                Not shared

# 4. Bind your camera (one-time per camera, persists across reboots)
usbipd bind --busid 1-5          # replace 1-5 with your camera's BUSID

# 5. Attach to WSL (do this after every WSL restart)
usbipd attach --wsl --busid 1-5
```

**Verify inside WSL2:**

```bash
# In your WSL2 Ubuntu terminal
ls /dev/video*
# Expected: /dev/video0  /dev/video1  (or just /dev/video0)

# Quick test — open a 1-second preview
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
print('Camera OK, frame shape:', frame.shape if ok else 'FAILED')
cap.release()
"
```

**After each WSL restart, re-run:**

```powershell
# In Admin PowerShell — only `attach` is needed; `bind` persists
usbipd attach --wsl --busid 1-5
```

### usbipd-win troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Cannot open camera index 0` in WSL2 | Camera not attached | Run `usbipd attach --wsl --busid <ID>` in Admin PowerShell |
| `usbipd: command not found` | Not installed | `winget install dorssel.usbipd-win` |
| Device shows "Shared" but not in WSL | Another WSL distro has it | `usbipd detach --busid <ID>`, then re-attach |
| `/dev/video0` missing after attach | WSL2 kernel missing `uvcvideo` | Update WSL2: `wsl --update` |
| `Could not open video device` from OpenCV | Permissions | `sudo chmod 666 /dev/video0` |
| Integrated webcam fails even with usbipd | Composite USB device | Try `index: 1` or `index: 2` in config.yaml; some webcams expose multiple endpoints |

**Risks / limitations:**
- Requires elevated privileges on Windows for initial bind
- Must re-run `usbipd attach` after every WSL restart
- Device index (`/dev/videoN`) can change — verify with `ls /dev/video*`
- Some cameras need extra drivers not present in the WSL2 kernel (run `wsl --update`)

---

## `integrated` — built-in laptop webcam

```yaml
camera:
  source: integrated
  # index: 0   (default; omit unless you have multiple cameras)
  target_fps: 15
  width: 640
```

**How it works:** Identical to `usb` — `integrated` is an alias that maps to
`UsbCameraCapture(index=0)`. The distinction is semantic (helps readers
understand which hardware is meant).

**When to use:**
- Quick local test on any laptop
- No extra hardware budget

**WSL2 caveat:** Same as `usb` above — usbipd-win passthrough required.
Integrated webcams are often harder to forward than dedicated USB cameras
because they appear in Windows as a USB composite device with multiple endpoints
(`/dev/video0`, `/dev/video1`, …). Try each index if the first one fails:

```yaml
camera:
  source: integrated
  index: 1   # try 0, 1, 2 if the default doesn't open
```

**Tip — Windows-native path is easier:**
On Windows, just run Phase A natively (see [WINDOWS.md](../WINDOWS.md)) —
integrated webcams open directly without any usbipd setup.

**Tip — check native Linux first:**
If you have dual-boot or bare-metal Ubuntu, integrated webcams almost always
work out of the box at `/dev/video0`. Use native Linux to avoid WSL2 complexity.

---

## `ipcam` — phone / network IP camera

```yaml
camera:
  source: ipcam
  url: "http://192.168.1.100:8080/video"    # your phone's IP
  shot_url: "http://192.168.1.100:8080/shot.jpg"
  reconnect_delay: 3
  target_fps: 5       # keep low — WiFi adds latency
  width: 640
```

**How it works:** `IPCameraCapture` opens the MJPEG stream URL with
`cv2.VideoCapture(url, cv2.CAP_FFMPEG)` and auto-reconnects on drop.

**Recommended app (Android, free):**
[IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam)
by Pavel Khlebovich.

**Setup steps:**

1. Install IP Webcam on your Android phone.
2. Open the app → tap **Start server**.
3. Note the IP shown on screen (e.g. `192.168.1.105:8080`).
4. Edit `config.yaml`:
   ```yaml
   camera:
     source: ipcam
     url: "http://192.168.1.105:8080/video"
   ```
5. Phone and computer must be on the **same WiFi network**.

**When to use:**
- WSL2 environments (no driver pain — works via TCP)
- Dedicated scanner phone that can be repositioned freely
- You want a wide-angle view from across the room

**Risks / limitations:**
- WiFi latency: ~100–300 ms round trip (fine for asset tracking, not for
  real-time robotic control)
- Stream can drop on weak WiFi — the auto-reconnect loop handles this
- Phone battery drains faster when streaming
- Both devices must be on the same subnet (same WiFi router)
- Some corporate/university WiFi networks block device-to-device traffic —
  use a personal hotspot or phone tethering in that case

---

---

## WSL2 ↔ Windows networking — opening the dashboard from a Windows browser

When Asset-Vision runs **inside WSL2**, the Uvicorn server listens on a WSL2
address. Whether `http://localhost:8100` works in your Windows browser depends
on your WSL2 networking mode.

### Option A — Mirrored networking (recommended, Windows 11 22H2+)

Mirrored networking makes WSL2 services reachable at `localhost` from Windows
automatically — no extra config needed.

Enable it by creating or editing `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
```

Then restart WSL2:

```powershell
wsl --shutdown
# Re-open your Ubuntu terminal
```

Verify: open `http://localhost:8100` in your Windows browser while Asset-Vision
is running in WSL2. It should connect immediately.

### Option B — NAT mode (older Windows / WSL2 default)

If mirrored networking is not available, WSL2 uses NAT — `localhost` in Windows
does NOT route to WSL2 services. Use the WSL2 IP instead:

```bash
# In your WSL2 terminal
hostname -I
# Example output: 172.26.240.1  (your WSL2 IP will differ)
```

Start Asset-Vision bound to that IP (or to all interfaces):

```bash
bash scripts/run.sh --host 0.0.0.0
# or
uvicorn web.app:app --host 0.0.0.0 --port 8100 --reload
```

Then open `http://172.26.240.1:8100` in your Windows browser (use your actual IP).

> **Security note:** `--host 0.0.0.0` exposes the dashboard on your LAN.
> There is no authentication — only use this on a trusted private network.
> Revert to `127.0.0.1` (or enable mirrored networking) when done.

### Quick diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `localhost:8100` refuses connection from Windows | NAT mode, bound to 127.0.0.1 | Switch to mirrored networking or use WSL2 IP |
| `localhost:8100` times out | Firewall blocking port | Add Windows Firewall inbound rule for port 8100 |
| Works on localhost but not from other devices | Server bound to 127.0.0.1 | Rebind to `0.0.0.0` (trusted LAN only) |

---

## Latency comparison (approximate, i5-1145G7, WSL2)

```
source: sample      →   0 ms  (file read, no network)
source: usb         →  30–80 ms  (USB 2.0 + OpenCV buffer)
source: integrated  →  30–80 ms  (same)
source: ipcam       → 100–300 ms (WiFi RTT + MJPEG decode)
```

For asset-tracking (detecting items on a desk), all sources are fast enough.
For real-time robotic control (< 50 ms required), prefer `usb`/`integrated`
on bare-metal Linux and avoid ipcam over WiFi.

---

## Recommended path for learners

```
Step 1: source: sample   → get the whole pipeline running, no hardware
Step 2: source: ipcam    → add a real camera via WiFi (works in WSL2)
Step 3: source: usb      → lower latency, usbipd-win if on WSL2
```

---

*See [INSTALL.md](../INSTALL.md) for setup instructions and
[USAGE.md](../USAGE.md) for switching sources at runtime.*
