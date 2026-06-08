# Usage Guide

> How to use Asset-Vision day-to-day: run the dashboard, register assets,
> print QR labels, switch camera sources, and read the ROS2 pipeline.

---

## Starting the dashboard

```bash
# From the repo root (WSL2 Ubuntu terminal)
bash scripts/run.sh
# or: make run
```

Open **http://localhost:8100** in your Windows/Linux browser.

To expose the dashboard to other devices on your local network (e.g. a phone):

```bash
bash scripts/run.sh --host 0.0.0.0
```

> ⚠️ No authentication is implemented. Only do this on a trusted network.

---

## Step 1 — Run with sample images (no camera)

Out of the box, `config.yaml` has `source: sample`. The dashboard loops
through the images in `samples/` and shows YOLO detections + QR reads.

This is the safest starting point. You will see:
- Bounding boxes drawn around synthetic objects
- QR codes decoded → AV-0001 to AV-0005 appearing as **Present**
- Live stats (FPS, detection count, QR hits)

---

## Step 2 — Register your own assets

1. Open **http://localhost:8100/register**
2. Fill in:
   - **Asset ID** — a unique number (prefix `AV-` is added automatically)
   - **Name** — e.g. `Laptop`, `Charger`, `Keys`
   - **Category** — e.g. `electronics`, `accessories`
3. Click **Register**.
4. Click **Download QR label** → print the PNG and stick it on the item.

To print all labels at once:
```
GET http://localhost:8100/api/sheet.png
```
Downloads a full A4 label sheet.

---

## Step 3 — Switch to a USB camera

Edit `config.yaml`:

```yaml
camera:
  source: usb
  index: 0        # 0 = first camera; try 1, 2 … for additional cameras
  target_fps: 15
  width: 640
```

Restart the dashboard (`Ctrl+C` → `bash scripts/run.sh`).

Point the camera at a QR-tagged item → the roster should flip to **Present**.
Move the item out of frame → after `presence_window_sec` (default 300 s) it
flips to **Missing**.

**WSL2 users:** USB cameras need `usbipd attach` first.
See [docs/CAMERA_SOURCES.md](docs/CAMERA_SOURCES.md) and [INSTALL.md](INSTALL.md).

---

## Step 4 — Switch to an IP camera (phone)

1. Install **[IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam)** on Android → **Start server**.
2. Note the IP shown (e.g. `192.168.1.105:8080`).
3. Edit `config.yaml`:

```yaml
camera:
  source: ipcam
  url: "http://192.168.1.105:8080/video"
  target_fps: 5        # keep low — WiFi adds latency
```

4. Restart the dashboard.

---

## Step 5 — Query the inventory via API

All endpoints return JSON:

```bash
# Full roster
curl http://localhost:8100/api/roster

# Stats (total assets, present/missing counts, pipeline FPS)
curl http://localhost:8100/api/stats

# Register an asset
curl -X POST http://localhost:8100/api/assets \
  -d "asset_id=0010&name=Multimeter&category=tools"

# Delete an asset
curl -X DELETE http://localhost:8100/api/assets/AV-0010

# Download a single QR label
curl -o AV-0010.png http://localhost:8100/api/assets/AV-0010/qr.png
```

---

## Step 6 — Run the ROS2 pipeline (Phase B)

The ROS2 version runs the same perception logic as proper robotics nodes,
connected via typed topics and a service.

```bash
# Terminal 1 — ROS2 pipeline (3 nodes)
source /opt/ros/humble/setup.bash
cd asset_ws && source install/setup.bash
ros2 launch asset_perception asset_system.launch.py

# Terminal 2 — web dashboard (reads same SQLite DB)
bash scripts/run.sh

# Terminal 3 — visualise the node graph
rqt_graph

# Terminal 3 — RViz2 annotated feed
rviz2 -d install/asset_perception/share/asset_perception/rviz/asset.rviz
```

Override launch parameters:

```bash
ros2 launch asset_perception asset_system.launch.py \
  camera_url:=http://192.168.1.100:8080/video \
  target_fps:=10.0 \
  presence_window_sec:=120.0 \
  log_level:=debug
```

Query the inventory via ROS2 service:

```bash
# All assets
ros2 service call /asset_manager_node/query_inventory \
  asset_interfaces/srv/QueryInventory "{status_filter: ''}"

# Only present assets
ros2 service call /asset_manager_node/query_inventory \
  asset_interfaces/srv/QueryInventory "{status_filter: 'present'}"
```

See **[LAUNCH_GUIDE.md](LAUNCH_GUIDE.md)** for the full walkthrough.

---

## Presence tracking

An asset flips from **Present** → **Missing** when it has not been seen by
the camera for `presence_window_sec` seconds (default: 300 s = 5 min).

Adjust in `config.yaml`:

```yaml
storage:
  presence_window_sec: 120   # 2 minutes — useful for testing
```

---

## Regenerating sample images

```bash
# Recreate the built-in samples
python generate_samples.py
# or: make sample

# Add your own images — just drop JPG/PNG files into samples/
cp my_photo.jpg samples/
```

---

## Resetting the database

```bash
make clean          # removes data/assets.db and data/frames/
# then: make run    # starts fresh
```

Or delete just the DB:
```bash
rm data/assets.db
```

---

## Keyboard shortcuts in the dashboard

| Action | How |
|--------|-----|
| Refresh roster | Auto — every 5 s |
| Force refresh | `F5` or browser refresh |
| Register asset | Click **Register new asset** |
| Download QR sheet | Click **Download label sheet** on the dashboard |

---

*See [INSTALL.md](INSTALL.md) to set up from scratch,
[docs/CAMERA_SOURCES.md](docs/CAMERA_SOURCES.md) to choose a camera,
and [LAUNCH_GUIDE.md](LAUNCH_GUIDE.md) for the ROS2 walkthrough.*
