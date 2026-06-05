# Asset-Vision

> **"I set out to build an asset-monitoring system. Once it worked, I realized the architecture was a robotics perception pipeline — so I re-built it on ROS2."**

A computer-vision inventory scanner that detects, identifies, and tracks personal belongings using a phone camera, YOLOv8, QR tags, and a local web dashboard. Phase B refactors the same logic into a ROS2 node graph.

---

## Demo

![dashboard screenshot](docs/dashboard.png)

**Live annotated feed · Inventory roster (present / missing) · One-click QR label printing**

---

## The story

Most robotics tutorials start with ROS2 — install everything first, fight the config, then write hello-world. I did the opposite.

1. **I had a real problem:** I wanted to track my gear (laptop, charger, headphones, etc.) with a camera.
2. **I built it in plain Python first:** phone stream → YOLO detection → QR tag lookup → SQLite → web dashboard. When it worked, every piece had a clear role.
3. **I noticed the pattern:** the pipeline was: *sensor → perception → state management → interface*. That's a robotics perception stack.
4. **I refactored it onto ROS2** (Phase B): `camera_node` → `perception_node` → `asset_manager_node`, connected via typed topics and services, visualised in RViz2 and rqt.

The result covers four things at once: **ML / machine vision · robotics (ROS2) · software integration · full-stack web**.

---

## Architecture

### Phase A — Plain Python (this branch)

```
[Oppo Reno7]
  IP Webcam app (free, Play Store)
  streams MJPEG over WiFi
       │
       ▼
 capture.py ──► detector.py ──► qrtools.py
  OpenCV          YOLOv8n        pyzbar QR
  auto-reconnect  80 COCO cls    decode + IoU
       │               │              │
       └───────────────┴──────────────┘
                       │
                  pipeline.py
              (orchestration loop)
                       │
                  store.py
              SQLite · assets + detections
              presence / last-seen logic
                       │
                  web/app.py
              FastAPI · Uvicorn
              MJPEG stream · roster · QR gen
```

### Phase B — ROS2 Humble (coming)

```
camera_node  ──/image_raw──►  perception_node  ──/detections──►  asset_manager_node
(capture.py)                  (detector + qr)                    (store + presence)
                                    │                                    │
                             /image_annotated                    QueryInventory srv
                                    │                                    │
                              rqt_image_view                     web dashboard
                                 RViz2                           (same SQLite)
```

---

## Hardware

| Component | Spec |
|-----------|------|
| CPU | Intel i5-1145G7 · 4C/8T · 2.6 GHz |
| RAM | 32 GB |
| GPU | Intel Iris Xe (no CUDA — pure CPU inference) |
| Platform | WSL2 Ubuntu 22.04 on Windows 11 |
| Camera | Oppo Reno7 running **IP Webcam** app |

CPU-only YOLOv8n achieves **~9 FPS** at 640 px on this hardware — sufficient for a room-scale asset scanner.

---

## Stack

| Layer | Tech |
|-------|------|
| Vision / ML | Ultralytics YOLOv8n · PyTorch (CPU) · OpenCV |
| QR | pyzbar (decode) · qrcode + Pillow (generate) |
| Storage | SQLite (local source of truth) |
| Backend | FastAPI · Uvicorn |
| Frontend | Jinja2 templates · vanilla JS (auto-refresh) |
| Robotics (Phase B) | ROS2 Humble · cv_bridge · rqt · RViz2 |

---

## Setup

### Prerequisites

- Windows 11 with WSL2 (Ubuntu 22.04)
- Android phone with **[IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam)** app (free)
- ~8 GB free disk in WSL

### Install

```bash
# In WSL Ubuntu 22.04
sudo apt-get install -y git python3-venv python3-pip build-essential libzbar0 ffmpeg
git clone https://github.com/SaladinIART/asset-vision.git
cd asset-vision
python3 -m venv ~/asset-venv
source ~/asset-venv/bin/activate
pip install -r requirements.txt
```

### Configure

1. Open **IP Webcam** on your phone → tap **Start server**
2. Note the IP shown (e.g. `192.168.1.105:8080`)
3. Edit `config.yaml`:
   ```yaml
   camera:
     url: "http://192.168.1.105:8080/video"
   ```

### Run

```bash
# In WSL, from project root
bash start.sh
```

Open **http://localhost:8100** in your Windows browser.

---

## Features

### Dashboard (`/`)
- Live annotated MJPEG stream from phone camera
- Inventory roster: all assets with **Present** / **Missing** / **Unknown** status
- Auto-refreshes every 5 s without reloading the stream
- Recent detections strip with confidence scores

### Asset registration (`/register`)
- Register a new item with name + category
- Download a printable QR label PNG (stick it on the item)
- Download a full label sheet (`/api/sheet.png`) for bulk printing

### Detection + tracking
- YOLOv8n detects object categories in every frame
- pyzbar reads QR tags in the same frame
- IoU-based spatial association links a QR tag to the nearest detection box
- `last_seen` timestamp updated on every confirmed sighting
- Asset flips to **missing** if not seen within the configured window (default 5 min)

---

## Project checklist

See [CHECKLIST.md](CHECKLIST.md) for checkpoint-by-checkpoint progress.

---

## What I learned

- How to stream video from a phone into a Linux computer-vision pipeline over WiFi (avoids USB/driver pain entirely)
- Spatial association between two independent detectors (YOLO boxes + QR polygons) using IoU
- SQLite WAL mode for concurrent read/write from a real-time loop and a web server
- FastAPI MJPEG streaming with `StreamingResponse` and multipart boundaries
- Why plain-Python-first is the right way to learn ROS2: you understand *what* each node does before you learn *how* ROS2 connects them

---

## Roadmap

- **Phase B** — ROS2 Humble refactor (nodes, custom msg/srv, launch file, RViz2)
- Firebase sync (optional cloud dashboard)
- OpenVINO export for Intel Iris Xe acceleration
- Custom YOLO fine-tune on personal items
- Multi-camera / location zones

---

*Portfolio project · Salbotics · 2026 · [salbotics.uk](https://salbotics.uk)*
