# Asset-Vision — Project Checklist

> **Portfolio project:** Inventory asset scanner using machine vision, QR tags, and ROS2.
> **Narrative:** Built a working Python asset-monitor first, then re-architected it as a ROS2 robotics pipeline.

---

## Phase A — Plain-Python MVP

| CP | Task | Status |
|----|------|--------|
| A0 | WSL2 Ubuntu 22.04 + dev tooling | ✅ done |
| A1 | Camera capture module (Oppo Reno7 → IP Webcam → OpenCV) | ✅ done |
| A2 | YOLO detection module (YOLOv8n, CPU) | ✅ done |
| A3 | QR generator + reader | 🔄 in progress |
| A4 | SQLite store + presence logic (present / missing) | ⬜ todo |
| A5 | Pipeline orchestration (capture → detect → QR → store) | ⬜ todo |
| A6 | FastAPI web dashboard (live feed + roster + QR generator) | ⬜ todo |
| A7 | Repo hygiene + README + demo assets → **LinkedIn post #1** | ⬜ todo |

## Phase B — ROS2 Humble Refactor

| CP | Task | Status |
|----|------|--------|
| B0 | Install ROS2 Humble desktop (same WSL2) | ⬜ todo |
| B1 | colcon workspace + custom interfaces (msg / srv) | ⬜ todo |
| B2 | camera_node (publishes `/image_raw`) | ⬜ todo |
| B3 | perception_node (YOLO + QR → `/detections`) | ⬜ todo |
| B4 | asset_manager_node + QueryInventory service | ⬜ todo |
| B5 | launch file + RViz + dashboard integration → **LinkedIn post #2** | ⬜ todo |
| B6 | README v2 — robotics section + node-graph diagram | ⬜ todo |

## Phase C — Later

| Item | Status |
|------|--------|
| Firebase sync (optional cloud dashboard) | ⬜ deferred |
| OpenVINO export (Intel Iris Xe acceleration) | ⬜ deferred |
| Custom YOLO fine-tune on personal items | ⬜ deferred |
| Latest-LTS rebuild (teaching/tutorial version) | ⬜ deferred |
| Mobile app | ⬜ deferred |

---

## Legend
- ✅ done
- 🔄 in progress
- ❌ blocked
- ⬜ todo
