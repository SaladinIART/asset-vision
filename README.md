# Asset-Vision

**Inventory asset scanner powered by computer vision, QR tags, and (eventually) ROS2.**

> *"I set out to build an asset-monitoring system — phone camera, object detection, QR tags, a local dashboard. Once it worked, I realized the architecture was a robotics perception pipeline, so I re-architected it on ROS2."*

---

## What it does

- Streams live video from an Android phone (IP Webcam app over WiFi)
- Detects and classifies objects in the frame using **YOLOv8** (PyTorch, CPU)
- Reads stick-on **QR tags** to give each item a unique asset ID
- Logs detections and tracks **presence / missing** status in local SQLite
- Serves a **web dashboard** (FastAPI): live annotated feed + inventory roster + QR label generator
- (Phase B) Re-implemented as a **ROS2 Humble** graph: `camera_node` → `perception_node` → `asset_manager_node`

## Stack

| Layer | Tech |
|-------|------|
| Vision | Ultralytics YOLOv8n · PyTorch (CPU) · OpenCV · pyzbar |
| Backend | Python 3.10 · SQLite · FastAPI · Uvicorn |
| Robotics | ROS2 Humble · cv_bridge · rqt · RViz2 |
| Platform | WSL2 Ubuntu 22.04 on Windows 11 · Intel i5-1145G7 · 32 GB RAM |
| Sensor | Oppo Reno7 running IP Webcam app |

## Architecture

```
[Oppo Reno7 : IP Webcam] ──WiFi MJPEG──► OpenCV capture
                                               │
                                    ┌──────────┼──────────┐
                                 YOLO detect        QR decode
                                    └──────────┼──────────┘
                                               │ associate
                                           SQLite DB
                                               │
                                    FastAPI web dashboard
                                  (live feed · roster · QR gen)
```

*Phase B wraps each stage as a ROS2 node, connected via typed topics and services.*

## Setup

> Full setup guide — coming in CP-A7.

## Progress

See [CHECKLIST.md](CHECKLIST.md) for checkpoint-by-checkpoint status.

---

*Portfolio project — Salbotics · 2026*
