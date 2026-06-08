"""
asset_system.launch.py — starts the full Asset-Vision ROS2 pipeline:

  camera_node        → publishes /image_raw
  perception_node    → subscribes /image_raw → publishes /detections + /image_annotated
  asset_manager_node → subscribes /detections → writes SQLite + serves QueryInventory

project_root is auto-detected from this file's location (4 levels up from launch/).
No hardcoded paths — works on any machine after cloning the repo.

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

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Auto-detect the repo root: this file is at
#   <repo_root>/asset_ws/src/asset_perception/launch/asset_system.launch.py
# so 4 .parent steps reach <repo_root>.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)


def generate_launch_description():
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

    return LaunchDescription(args + [banner, camera_node, perception_node, manager_node])
