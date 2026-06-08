# Installation Guide

> **Goal:** Get Asset-Vision running on your machine in under 10 minutes,
> with no camera hardware required.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **OS** | Ubuntu 22.04 (native or WSL2 on Windows 11) |
| **Python** | 3.10 or newer (`python3 --version`) |
| **RAM** | 4 GB minimum; 8 GB recommended |
| **Disk** | ~3 GB free (Python env + YOLOv8 weights downloaded on first run) |
| **Camera** | Optional — the default `sample` mode needs no hardware at all |

### Windows users — two paths

| Path | When to choose |
|------|----------------|
| **Windows-native (Phase A only)** | You want the web dashboard + local camera without WSL2. See **[WINDOWS.md](WINDOWS.md)**. |
| **WSL2 Ubuntu (Phase A + B)** | You want the full ROS2 pipeline. Follow the steps below. |

To install WSL2:

```powershell
# In Windows PowerShell (run as Administrator)
wsl --install -d Ubuntu-22.04
# Restart when prompted, then open "Ubuntu 22.04" from the Start menu
```

All commands below run **inside the WSL2 Ubuntu terminal**.

---

## 1. Clone the repo

```bash
git clone https://github.com/SaladinIART/asset-vision.git
cd asset-vision
```

---

## 2. Run the install script (one command)

```bash
bash scripts/install.sh
```

This automatically:
- Installs system packages (`libzbar0`, `ffmpeg`, `python3-venv`, …)
- Creates a Python virtual environment at `~/asset-venv`
- Installs all Python dependencies from `requirements.txt`
- Copies `config.example.yaml` → `config.yaml` (if not already present)
- Generates the bundled sample images in `samples/`
- Creates the `data/` directory

Re-running is safe — it skips steps already done.

Alternatively, use `make`:

```bash
make install
```

---

## 3. Start the dashboard

```bash
bash scripts/run.sh
# or: make run
```

Open **http://localhost:8100** in your browser (Chrome, Firefox, Edge — any modern browser).

You should see:
- A live feed cycling through the sample desk images
- YOLO detection boxes drawn around objects
- The inventory roster showing AV-0001 … AV-0005 as **Present**

> **Note:** The YOLOv8n model weights (`yolov8n.pt`, ~6 MB) are downloaded
> automatically on first run. You need an internet connection for this one step.
> Subsequent runs are fully offline.

---

## 4. (Optional) Switch to a real camera

Edit `config.yaml` and change the `source` line:

| Source | Setting | Extra steps |
|--------|---------|-------------|
| Offline sample loop | `source: sample` | None |
| USB camera | `source: usb` | Native Linux: none. WSL2: see below |
| Built-in webcam | `source: integrated` | Same as USB |
| Phone via WiFi | `source: ipcam` | Set `url:` to your phone's IP |

**USB / integrated on WSL2** — requires usbipd-win:

```powershell
# In Windows PowerShell (Admin)
winget install usbipd
usbipd list                        # find your camera BUSID, e.g. 2-3
usbipd bind --busid 2-3
usbipd attach --wsl --busid 2-3
```

**IP camera (phone):**

1. Install **[IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam)** on Android → tap **Start server**.
2. Note the IP shown (e.g. `192.168.1.105:8080`).
3. Edit `config.yaml`:
   ```yaml
   camera:
     source: ipcam
     url: "http://192.168.1.105:8080/video"
   ```

See **[docs/CAMERA_SOURCES.md](docs/CAMERA_SOURCES.md)** for a full
comparison of all sources including latency, risks, and WSL2 notes.

---

## 5. (Optional) Install ROS2 Humble (Phase B)

Phase B wraps the same pipeline in ROS2 nodes. Only needed if you want
to explore the robotics architecture.

```bash
# Add ROS2 apt repository
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt-get update
sudo apt-get install -y ros-humble-desktop python3-colcon-common-extensions \
  ros-humble-cv-bridge

# Build the workspace (run from repo root)
source /opt/ros/humble/setup.bash
cd asset_ws
colcon build
source install/setup.bash

# Launch all 3 nodes
ros2 launch asset_perception asset_system.launch.py
```

See **[LAUNCH_GUIDE.md](LAUNCH_GUIDE.md)** for the full ROS2 walkthrough.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `libzbar.so.0: cannot open shared object` | `sudo apt-get install libzbar0` |
| `ModuleNotFoundError: No module named 'cv2'` | `source ~/asset-venv/bin/activate` first |
| Dashboard shows "Waiting for camera…" | Check `config.yaml` → `source:` is valid |
| `FileNotFoundError: No images found in 'samples/'` | Run `python generate_samples.py` |
| Port 8100 already in use | `fuser -k 8100/tcp` then retry |
| WSL2 USB camera not found | Run `usbipd attach --wsl --busid <ID>` in PowerShell |
| YOLOv8 download fails | Check internet connection; weights go to `~/.config/Ultralytics/` |
