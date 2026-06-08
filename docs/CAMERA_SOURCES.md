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
using **usbipd-win**:

```powershell
# In Windows PowerShell (run as Administrator)
winget install usbipd
usbipd list                       # find your camera's BUSID, e.g. 2-3
usbipd bind --busid 2-3
usbipd attach --wsl --busid 2-3  # re-run after every WSL restart
```

Then in WSL:
```bash
ls /dev/video*          # should show /dev/video0
python capture.py --source usb
```

**Risks / limitations:**
- Requires elevated privileges on Windows for initial bind
- Device path (`/dev/videoN`) can change after reboot — re-run `usbipd attach`
- Some cameras need extra drivers not present in the WSL2 kernel

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
because they show up as a USB composite device.

**Tip — check native Linux first:**
If you have a dual-boot or a bare-metal Ubuntu machine, integrated webcams
almost always work out of the box (`/dev/video0`). Use native Linux to avoid
the WSL2 passthrough complexity.

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
