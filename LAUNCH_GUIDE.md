# Asset-Vision — Live Launch Guide (Phase B)

> **Goal:** Bring up the full 3-node ROS2 pipeline + web dashboard in two terminals.

---

## Pre-flight

1. **Phone** — Open IP Webcam app → Start Server. Note the IP (default: `192.168.1.100:8080`).
2. **WSL** — Make sure Ubuntu 22.04 is running: `wsl -d Ubuntu-22.04`

---

## Terminal 1 — ROS2 Pipeline

```bash
# In WSL
source /opt/ros/humble/setup.bash
cd ~/asset_ws
source install/setup.bash

ros2 launch asset_perception asset_system.launch.py
```

You should see:
```
[INFO] Asset-Vision ROS2 pipeline starting…
[INFO] camera_node: Connected to http://192.168.1.100:8080/video
[INFO] perception_node: Loading YOLO model…
[INFO] asset_manager_node: Store opened: data/assets.db
```

**Optional overrides:**
```bash
ros2 launch asset_perception asset_system.launch.py \
  camera_url:=http://192.168.1.100:8080/video \
  target_fps:=10.0 \
  presence_window_sec:=120.0 \
  log_level:=debug
```

---

## Terminal 2 — Web Dashboard

```bash
# In WSL (new tab)
cd /path/to/asset-vision      # wherever you cloned the repo
source ~/asset-venv/bin/activate
./start.sh
```

Open: **http://localhost:8100** in Windows browser.

---

## Terminal 3 (optional) — RViz2 + rqt_graph

```bash
# In WSL (new tab)
source /opt/ros/humble/setup.bash
cd ~/asset_ws && source install/setup.bash

# Annotated live feed in RViz:
rviz2 -d install/asset_perception/share/asset_perception/rviz/asset.rviz

# OR — node graph topology:
rqt_graph
```

---

## Query the inventory via service call

```bash
# All assets:
ros2 service call /asset_manager_node/query_inventory \
  asset_interfaces/srv/QueryInventory "{status_filter: ''}"

# Only present assets:
ros2 service call /asset_manager_node/query_inventory \
  asset_interfaces/srv/QueryInventory "{status_filter: 'present'}"
```

---

## Expected node graph (rqt_graph)

```
[camera_node]
     │ /image_raw (sensor_msgs/Image)
     ▼
[perception_node]
     │ /detections (asset_interfaces/AssetDetections)
     │ /image_annotated (sensor_msgs/Image)
     ▼
[asset_manager_node]
     │ → SQLite (data/assets.db)  ← read by web dashboard
     └ QueryInventory service
```

---

## Demo screenshot checklist

- [ ] `rqt_graph` showing all 3 nodes connected
- [ ] `rviz2` showing annotated live feed with YOLO boxes + QR overlay
- [ ] Web dashboard at `localhost:8100` with PRESENT/MISSING roster
- [ ] Terminal showing `ros2 service call` response
