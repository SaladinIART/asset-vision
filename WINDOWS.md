# Asset-Vision on Windows — Manual Setup Guide

> **Platform:** Windows 10/11 (native) — no WSL2 required for the Phase A dashboard.
> ROS2 Phase B still runs inside WSL2; see [INSTALL.md](INSTALL.md) for that path.

This guide walks you through each step manually so you understand what is happening.
If you prefer one-command automation, [scripts/install.ps1](scripts/install.ps1) does
all of these steps for you — scroll to the bottom for details.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Windows** | Windows 10 21H2 or Windows 11 |
| **Python** | 3.10 or newer — install from [python.org](https://www.python.org/downloads/) |
| **py launcher** | Bundled with the official Python installer; choose "Add to PATH" |
| **Git** | [git-scm.com](https://git-scm.com/) or GitHub Desktop |
| **RAM** | 4 GB minimum; 8 GB recommended |
| **Camera** | Optional — the default `sample` mode needs no hardware at all |

To check Python is installed correctly, open **Command Prompt** or **PowerShell** and run:

```powershell
py --version
# Expected: Python 3.10.x (or newer)
```

---

## Step 1 — Clone the repository

```powershell
git clone https://github.com/SaladinIART/asset-vision.git
cd asset-vision
```

---

## Step 2 — Create a virtual environment

A virtual environment keeps Asset-Vision's dependencies separate from your system Python.

```powershell
py -m venv .venv
```

This creates a `.venv\` folder inside the repo. It is already listed in `.gitignore`.

---

## Step 3 — Activate the virtual environment

```powershell
.venv\Scripts\Activate.ps1
```

> **Execution policy error?** If PowerShell blocks the script, run this first:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> Then re-run the activate command above.

After activation, your prompt shows `(.venv)` — this means the venv is active.

---

## Step 4 — Install Python dependencies

```powershell
pip install -r requirements.txt
```

This installs OpenCV, YOLOv8, pyzbar, FastAPI, Uvicorn, and all other dependencies.

---

## Step 5 — Install the `asset_vision` package

```powershell
pip install -e .
```

The `-e` flag installs in *editable* mode — code changes take effect immediately
without reinstalling.

---

## Step 6 — Copy the example config

```powershell
Copy-Item config.example.yaml config.yaml
```

The default config uses `source: sample` — this means the dashboard runs with no
camera hardware attached.

---

## Step 7 — Create the data directory

```powershell
New-Item -ItemType Directory -Force data\frames
```

---

## Step 8 — Start the dashboard

```powershell
.venv\Scripts\uvicorn.exe web.app:app --host 127.0.0.1 --port 8100 --reload
```

Open **http://localhost:8100** in your browser. You should see:

- A live feed cycling through bundled sample desk images
- YOLO detection boxes drawn around detected objects
- An inventory roster showing AV-0001 … AV-0005 as **Present**

> **First-run note:** YOLOv8n model weights (`yolov8n.pt`, ~6 MB) are downloaded
> automatically the first time. Subsequent runs are fully offline.

---

## Using a real camera on Windows

Windows gives you direct access to USB and built-in cameras — no usbipd passthrough needed.

Edit `config.yaml` and change the `source` line:

```yaml
camera:
  source: usb         # USB webcam (index 0 = first camera)
  # index: 0
```

| Source | `config.yaml` setting | Windows behaviour |
|--------|----------------------|-------------------|
| `sample` | `source: sample` | Offline image loop — no hardware needed |
| `usb` | `source: usb` | USB webcam — plug in and it works |
| `integrated` | `source: integrated` | Built-in laptop camera — same as `usb` |
| `ipcam` | `source: ipcam` + `url: http://...` | Phone IP Webcam app over WiFi |

For the IP camera option, install the **IP Webcam** Android app, tap **Start server**,
note the IP shown (e.g. `192.168.1.105:8080`), then edit `config.yaml`:

```yaml
camera:
  source: ipcam
  url: "http://192.168.1.105:8080/video"
```

See [docs/CAMERA_SOURCES.md](docs/CAMERA_SOURCES.md) for a full comparison with WSL2 notes.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `py` not found | Install Python from python.org — tick "Add to PATH" and "py launcher" |
| `.venv\Scripts\Activate.ps1` blocked | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: No module named 'cv2'` | Ensure `.venv` is active (`(.venv)` in prompt) |
| `zbar` library error on Windows | Install the pyzbar Windows binary: `pip install pyzbar` (included in requirements.txt) |
| Dashboard shows "Waiting for camera…" | Check `config.yaml` → `source:` is set to a valid value |
| `FileNotFoundError: No images found in 'samples/'` | Run `py generate_samples.py` |
| Port 8100 already in use | `netstat -ano \| findstr :8100` → `taskkill /PID <pid> /F` |
| Camera index 0 not found | Change `index: 1` in config.yaml if you have multiple cameras |

---

## Automation shortcut

`scripts/install.ps1` automates every step above (Steps 2–7) in a single command:

```powershell
.\scripts\install.ps1
```

And `scripts/run.ps1` starts the dashboard:

```powershell
.\scripts\run.ps1
```

These scripts are primarily intended for the author's repeated dev workflow.
Going through the manual steps above (at least once) gives you a better understanding
of what each piece does and how to troubleshoot it.

---

## What about ROS2 on Windows?

ROS2 Humble's Windows support is incomplete and painful to set up. The Phase B ROS2
pipeline runs inside **WSL2 Ubuntu 22.04** — this is the recommended path for everyone.

If you want Phase B:
1. Install WSL2: `wsl --install -d Ubuntu-22.04` (PowerShell, Admin)
2. Follow [INSTALL.md](INSTALL.md) inside the WSL2 terminal.

The Phase A web dashboard (this guide) runs natively on Windows — you can run it
in a separate terminal while WSL2 handles the ROS2 pipeline.
