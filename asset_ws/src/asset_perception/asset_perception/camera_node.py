"""
camera_node — reads a camera source and publishes sensor_msgs/Image on /image_raw.

Supports all sources from asset_vision.capture (ipcam | usb | integrated | sample).
The source type is selected by the `source` parameter (default: ipcam for ROS2 use).

Topics published:
  /image_raw  (sensor_msgs/Image, BGR8)

Parameters:
  source          camera source: ipcam | usb | integrated | sample (default: ipcam)
  camera_url      MJPEG URL — used when source=ipcam
  target_fps      frames per second to publish (default: 5.0)
  frame_width     resize width in pixels (default: 640)
  reconnect_delay seconds between reconnect attempts — ipcam only (default: 3.0)
  camera_index    device index — used when source=usb|integrated (default: 0)
  samples_dir     image folder — used when source=sample (default: "samples")
  project_root    path to the asset-vision repo root (auto-set by launch file;
                  only needed if `pip install -e .` was NOT run in the ROS2 env)
"""
import sys
import threading

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from cv_bridge import CvBridge


def _ensure_asset_vision(project_root: str):
    """Import asset_vision, falling back to sys.path injection if not installed."""
    try:
        import asset_vision  # noqa: F401 — already installed via pip install -e .
    except ImportError:
        if not project_root:
            raise RuntimeError(
                "asset_vision package not found. Either run "
                "'pip install -e .' from the repo root, or pass "
                "project_root:=<path> to the launch file."
            )
        if project_root not in sys.path:
            sys.path.insert(0, project_root)


class CameraNode(Node):
    def __init__(self):
        super().__init__("camera_node")

        # ── Parameters ──────────────────────────────────────────────────
        self.declare_parameter("project_root",    "")
        self.declare_parameter("source",          "ipcam")
        self.declare_parameter("camera_url",      "http://192.168.1.100:8080/video")
        self.declare_parameter("target_fps",      5.0)
        self.declare_parameter("frame_width",     640)
        self.declare_parameter("reconnect_delay", 3.0)
        self.declare_parameter("camera_index",    0)
        self.declare_parameter("samples_dir",     "samples")

        project_root = self.get_parameter("project_root").value
        _ensure_asset_vision(project_root)

        from asset_vision.capture import make_source  # noqa: E402

        source = self.get_parameter("source").value
        cfg = {
            "source":          source,
            "url":             self.get_parameter("camera_url").value,
            "target_fps":      self.get_parameter("target_fps").value,
            "width":           self.get_parameter("frame_width").value,
            "reconnect_delay": self.get_parameter("reconnect_delay").value,
            "index":           self.get_parameter("camera_index").value,
            "samples_dir":     self.get_parameter("samples_dir").value,
        }

        self.get_logger().info(f"Camera source : {source}")
        self.get_logger().info(f"Target FPS    : {cfg['target_fps']}")

        self._bridge = CvBridge()
        self._pub    = self.create_publisher(Image, "image_raw", 10)
        self._cap    = make_source(cfg)

        self._thread = threading.Thread(target=self._stream, daemon=True)
        self._thread.start()
        self.get_logger().info("camera_node ready — streaming.")

    # ------------------------------------------------------------------
    def _stream(self):
        for ts, frame in self._cap.frames():
            if not rclpy.ok():
                break
            msg = self._bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header = Header()
            msg.header.stamp    = self.get_clock().now().to_msg()
            msg.header.frame_id = "camera"
            self._pub.publish(msg)

    def destroy_node(self):
        self._cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
