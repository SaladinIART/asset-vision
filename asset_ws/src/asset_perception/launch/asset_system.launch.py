"""
asset_system.launch.py — starts the full Asset-Vision ROS2 pipeline:

  camera_node        → publishes /image_raw
  perception_node    → subscribes /image_raw → publishes /detections + /image_annotated
  asset_manager_node → subscribes /detections → writes SQLite + serves QueryInventory

project_root is auto-detected by walking upward from this file until pyproject.toml
is found. This works whether the file is run from the source tree or from the colcon
install directory (colcon copies the launch file, which breaks fixed .parent counts).

Usage:
  source /opt/ros/humble/setup.bash
  cd <repo_root>/asset_ws && colcon build && source install/setup.bash
  ros2 launch asset_perception asset_system.launch.py

Optional overrides (append key:=value):
  source:=ipcam              camera source (ipcam | usb | integrated | sample)
  camera_url:=http://192.168.1.100:8080/video
  target_fps:=10.0
  db_path:=data/assets.db
  presence_window_sec:=300.0
  log_level:=info            (info | debug | warn)
"""

import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _find_project_root() -> str:
    """
    Walk upward from this file until we find pyproject.toml (the repo root marker).
    Falls back to ASSET_VISION_ROOT env var, then the directory 4 levels up.

    colcon copies the launch file into install/…/share/…/launch/, so a fixed
    .parent.parent.parent.parent count gives the wrong directory.  Walking upward
    for pyproject.toml is install-location-agnostic.
    """
    # 1. Explicit env override (set in install.sh / CI / developer's shell)
    env_root = os.environ.get("ASSET_VISION_ROOT", "")
    if env_root and Path(env_root, "pyproject.toml").exists():
        return env_root

    # 2. Walk upward from this file looking for pyproject.toml
    candidate = Path(__file__).resolve()
    for _ in range(10):           # safety limit — don't walk forever
        candidate = candidate.parent
        if (candidate / "pyproject.toml").exists():
            return str(candidate)

    # 3. Last resort: 4 × parent (original behaviour — correct in source tree)
    return str(Path(__file__).resolve().parent.parent.parent.parent)


_PROJECT_ROOT = _find_project_root()


def generate_launch_description():
    # ── Inject project root into PYTHONPATH so nodes find asset_vision
    #    even if `pip install -e .` was NOT run in the system Python3.
    #    SetEnvironmentVariable prepends; existing PYTHONPATH is preserved.
    _existing_pypath = os.environ.get("PYTHONPATH", "")
    _new_pypath = f"{_PROJECT_ROOT}:{_existing_pypath}" if _existing_pypath else _PROJECT_ROOT
    pythonpath_action = SetEnvironmentVariable("PYTHONPATH", _new_pypath)

    # ── Declare overridable arguments ──────────────────────────────────────
    args = [
        DeclareLaunchArgument(
            "source",
            default_value="ipcam",
            description="Camera source: ipcam | usb | integrated | sample",
        ),
        DeclareLaunchArgument(
            "camera_url",
            default_value="http://192.168.1.100:8080/video",
            description="IP Webcam MJPEG stream URL (used when source=ipcam)",
        ),
        DeclareLaunchArgument(
            "target_fps",
            default_value="10.0",
            description="Target capture FPS",
        ),
        DeclareLaunchArgument(
            "db_path",
            default_value="data/assets.db",
            description="Path to SQLite database",
        ),
        DeclareLaunchArgument(
            "presence_window_sec",
            default_value="300.0",
            description="Seconds before an asset flips from present → missing",
        ),
        DeclareLaunchArgument(
            "log_level",
            default_value="info",
            description="ROS2 log level (debug/info/warn/error)",
        ),
    ]

    cfg = {k: LaunchConfiguration(k) for k in [
        "source", "camera_url", "target_fps", "db_path",
        "presence_window_sec", "log_level",
    ]}

    # ── Nodes ──────────────────────────────────────────────────────────────
    camera_node = Node(
        package="asset_perception",
        executable="camera_node",
        name="camera_node",
        output="screen",
        arguments=["--ros-args", "--log-level", cfg["log_level"]],
        parameters=[{
            "project_root": _PROJECT_ROOT,   # enables import fallback
            "source":       cfg["source"],
            "camera_url":   cfg["camera_url"],
            "target_fps":   cfg["target_fps"],
        }],
    )

    perception_node = Node(
        package="asset_perception",
        executable="perception_node",
        name="perception_node",
        output="screen",
        arguments=["--ros-args", "--log-level", cfg["log_level"]],
        parameters=[{
            "project_root": _PROJECT_ROOT,
            "model":        "yolov8n.pt",
            "confidence":   0.45,
            "device":       "cpu",
        }],
    )

    manager_node = Node(
        package="asset_perception",
        executable="manager_node",
        name="asset_manager_node",
        output="screen",
        arguments=["--ros-args", "--log-level", cfg["log_level"]],
        parameters=[{
            "project_root":        _PROJECT_ROOT,
            "db_path":             cfg["db_path"],
            "presence_window_sec": cfg["presence_window_sec"],
            "presence_sweep_sec":  30.0,
        }],
    )

    banner = LogInfo(msg=(
        "\n"
        "════════════════════════════════════════════════\n"
        "  Asset-Vision ROS2 pipeline starting…\n"
        f"  Project root : {_PROJECT_ROOT}\n"
        "  camera_node  →  /image_raw\n"
        "  perception_node  →  /detections + /image_annotated\n"
        "  asset_manager_node  →  SQLite + QueryInventory srv\n"
        "────────────────────────────────────────────────\n"
        "  Dashboard:  http://localhost:8100\n"
        "  rqt_graph to visualise the node graph\n"
        "════════════════════════════════════════════════\n"
    ))

    return LaunchDescription(
        [pythonpath_action] + args + [banner, camera_node, perception_node, manager_node]
    )
