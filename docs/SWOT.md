# Asset-Vision — SWOT Analysis

*Last updated: 2026-06-08 (post Wave 1–3 completion)*

---

## Strengths

| # | Strength |
|---|----------|
| S1 | **Pluggable camera source** — same Python code runs `sample → ipcam → usb → integrated` with one config line; same pipeline logic across all four |
| S2 | **Offline-first** — `source: sample` works with zero hardware; CI runs the full pipeline headless |
| S3 | **Bottom-up teaching story** — Phase A plain Python → Phase B ROS2 Humble refactor shows *why* the node split makes sense, not just *how* to do it |
| S4 | **Full-stack breadth** — ML (YOLOv8), CV (OpenCV, pyzbar IoU), storage (SQLite WAL), web (FastAPI/Uvicorn/MJPEG), robotics (ROS2 custom msg/srv, colcon, rqt) |
| S5 | **58 automated tests** — pytest suite covers store CRUD, presence state machine, QR round-trip encode/decode, IoU spatial association — no YOLO/camera needed |
| S6 | **Green CI badge** — GitHub Actions: ruff lint + pytest on every push |
| S7 | **Cross-environment** — Windows-native (Phase A), WSL2 (Phase A + B), bare-metal Ubuntu (Phase A + B); documented, tested |
| S8 | **Clean security posture** — personal leaks scrubbed (IPs, username paths, email in ROS2 metadata); web default to `127.0.0.1`; leak-grep clean |

---

## Weaknesses

| # | Status | Item |
|---|--------|------|
| W1 | ✅ Eliminated | Personal/security leaks — Windows username in paths ×4, private phone IP ×8, personal email in ROS2 package metadata, web bound to `0.0.0.0` |
| W2 | ✅ Mostly eliminated | Not clone-and-runnable — live phone IP required, hardcoded `/mnt/c/...` paths. *Residual: Ubuntu 22.04 system pip PEP 660 issue (worked around via PYTHONPATH + `setup.py` stub)* |
| W3 | ✅ Eliminated | Missing polish — broken hero image, no LICENSE, no install automation, no camera guidance |
| W4 | ⚠️ Partial | No live screenshots — `docs/rqt_graph.png` and `docs/live_dashboard.png` pending author capture. Capture checklist is written; Windows-native path removes the hardware blocker. |
| W5 | ⚠️ Known | `_PROJECT_ROOT` in launch file computes wrong path when run from colcon install directory (`Path(__file__).parent×4` gives install tree, not repo root). Mitigated by `_find_project_root()` walk-up and PYTHONPATH injection in launch file. |

---

## Opportunities

| # | Status | Item |
|---|--------|------|
| O1 | ✅ Converted → S7 | Pluggable source already runs the same code in 3 environments → capability matrix in README turns the gap into a documented strength |
| O2 | ✅ Converted | Windows-native Phase A = zero-friction local-camera demo → easiest path to `live_dashboard.png` and unblocks LinkedIn post #2 |
| O3 | ✅ Converted | Windows path + usbipd guide together = honest "works on any setup" teaching story |
| O4 | Open | OpenVINO export for Intel Iris Xe — CPU inference is currently ~9 FPS; OpenVINO could push 2–3× faster without CUDA |
| O5 | Open | Jazzy/Kilted rebuild — clean tutorial version of Phase B for the next ROS2 LTS cohort |
| O6 | Open | Firebase sync / cloud dashboard — extends the portfolio story from local to cloud-connected IIoT |

---

## Threats

| # | Status | Item |
|---|--------|------|
| T1 | ✅ Reduced → ~0 | Clone won't build → repo looks broken. Green CI + sample default + offline-first docs mitigate. *Residual: ROS2 USB path still env-gated (WSL2 + usbipd required)* |
| T2 | ✅ Eliminated | Email scraping from public ROS2 metadata — replaced with `asset-vision@users.noreply.github.com` |
| T3 | ✅ Reduced | LAN exposure — web default `0.0.0.0` → `127.0.0.1`. *Residual: no authentication if user opts into `0.0.0.0`* |
| T4 | ✅ Documented | First-run USB failure in WSL2 = wall of red errors → student thinks repo is broken. Now documented in `CAMERA_SOURCES.md` with the exact error string and fix steps |
| T5 | ✅ Documented | Browser-from-Windows → WSL2 service networking — mirrored vs NAT mode. Documented in `CAMERA_SOURCES.md` with diagnosis table |

---

## Verified capability matrix

| Source | Windows (native) | WSL2 Ubuntu | Native Linux |
|--------|:---:|:---:|:---:|
| `sample` — offline image loop | ✅ | ✅ | ✅ |
| `ipcam` — phone IP Webcam | ✅ | ✅ | ✅ |
| `usb` — USB camera | ✅ native | ⚠️ usbipd-win | ✅ |
| `integrated` — built-in webcam | ✅ native | ⚠️ usbipd-win | ✅ |

*"4 cameras" claim is true in code. In WSL2, `usb`/`integrated` require usbipd-win passthrough.
On Windows-native or bare-metal Linux, all four sources work out of the box.*

---

## Wave summary

| Wave | Focus | Status |
|------|-------|--------|
| Wave 1 | Safe + runnable + documented (scrub, sample source, install/run scripts, camera guide, INSTALL/USAGE, SVG diagram) | ✅ Complete |
| Wave 2 | Teaching-grade refactor (`asset_vision` package, ROS2 param de-hardcode, pytest suite, CI, LinkedIn draft) | ✅ Complete |
| Wave 3 | Cross-environment + live proof (`install.ps1`/`run.ps1`, `WINDOWS.md`, usbipd deep guide, capability matrix, capture checklist, this SWOT) | ✅ Complete (screenshots pending author capture) |
