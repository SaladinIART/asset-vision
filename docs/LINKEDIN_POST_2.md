# LinkedIn Post #2 — Teaching-Grade Repo Launch

> **Status:** Ready to publish once `docs/rqt_graph.png` + `docs/live_dashboard.png` are captured.
> Attach those two images to the LinkedIn post before posting.

---

## Draft copy (copy-paste into LinkedIn)

---

I rebuilt my robotics portfolio project — not to impress recruiters, but to be actually useful to robotics students.

Here's what changed, and why.

---

**The original:** a full computer-vision asset tracker built in two phases:
- Phase A → plain Python: IP Webcam → YOLOv8 → QR decode → SQLite → FastAPI dashboard
- Phase B → ROS2 Humble: camera_node → perception_node → asset_manager_node, typed topics, custom messages, QueryInventory service

It worked. But a fresh clone on anyone else's machine? Wouldn't run without my phone IP address hardcoded in three places.

---

**The problem I fixed:**

🔒 Scrubbed all personal data from the working tree (private IPs, local usernames, personal email in ROS2 package metadata)

📦 Moved the core logic into an installable `asset_vision` Python package — `pip install -e .` from the repo root

🎥 Pluggable camera source: `sample → usb → integrated → ipcam` — swap with one config line. Default is `sample`, so any student can run it offline with zero hardware

✅ 58 automated tests (pytest) — store CRUD, presence state machine, QR round-trip encode/decode, IoU spatial association

🟢 GitHub Actions CI — lint (ruff) + full test suite on every push

📖 `docs/CAMERA_SOURCES.md` — when to use IP cam vs USB vs integrated vs sample, WSL2 usbipd walkthrough, latency comparison table

---

**The learning structure I care about:**

Most ROS2 tutorials start with "install ROS2 first" — then you fight setup for two days and never understand *why* the nodes are split that way.

I built Phase A in plain Python first. Every component had a clear job. When I noticed the pattern — *sensor → perception → state → interface* — the ROS2 refactor was obvious, not magic.

That's the point I want students to take away: **understand the problem first, then reach for the framework.**

---

🔗 **Repo:** https://github.com/SaladinIART/asset-vision
Clone it, run it offline, swap in your camera when ready.

If you're learning ROS2 and want to see a real perception pipeline built bottom-up, this is for you.

---

#ROS2 #Robotics #MachineLearning #ComputerVision #YOLOv8 #OpenSource #Python #SoftwareEngineering #Salbotics

---

## Image checklist for this post

Attach **2 images** in this order:

1. **`docs/rqt_graph.png`** — rqt_graph showing the 3-node topology
   - Run: `rqt_graph` while the system is live
   - Set view to "All" / uncheck dead sinks
   - Should show: `camera_node → /image_raw → perception_node → /detections → asset_manager_node`

2. **`docs/live_dashboard.png`** — browser dashboard with USB cam feed + YOLO boxes + roster
   - Run system with `source: usb` in config.yaml
   - Capture the browser window at http://localhost:8100
   - Aim for at least one detected object with a bounding box visible

---

## Capture session checklist

```bash
# In WSL2 — start the ROS2 pipeline (USB camera)
source /opt/ros/humble/setup.bash
cd ~/asset_ws
source install/setup.bash
ros2 launch asset_perception asset_system.launch.py source:=usb

# In a second terminal
rqt_graph
# Screenshot → save to docs/rqt_graph.png

# Browser → http://localhost:8100
# Screenshot → save to docs/live_dashboard.png
```

Then from the repo root:
```bash
git add docs/rqt_graph.png docs/live_dashboard.png
git commit -m "docs: add live USB camera shots (rqt_graph + dashboard)"
git push
```
