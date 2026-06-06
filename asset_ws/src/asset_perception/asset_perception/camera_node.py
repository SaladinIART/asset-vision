"""
camera_node — reads the Oppo Reno7 IP Webcam MJPEG stream and publishes
sensor_msgs/Image on /image_raw at a configurable FPS.

Reuses capture.py from Phase A via sys.path injection.
Topics published:
  /image_raw  (sensor_msgs/Image, BGR8)
Parameters:
  camera_url      (str)   IP Webcam MJPEG URL
  target_fps      (float) frames per second to publish
  frame_width     (int)   resize width (height auto-scaled)
  reconnect_delay (float) seconds between reconnect attempts
"""
import sys
import os

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from cv_bridge import CvBridge

# Inject project root so we can reuse capture.py from Phase A
_PROJECT_ROOT = "/mnt/c/Users/salbot01/Salbotics/asset-vision"
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from capture import IPCameraCapture  # noqa: E402


class CameraNode(Node):
    def __init__(self):
        super().__init__("camera_node")

        # Declare parameters (overridable from launch / CLI)
        self.declare_parameter("camera_url",      "http://192.168.0.5:8080/video")
        self.declare_parameter("target_fps",      5.0)
        self.declare_parameter("frame_width",     640)
        self.declare_parameter("reconnect_delay", 3.0)

        url      = self.get_parameter("camera_url").value
        fps      = self.get_parameter("target_fps").value
        width    = self.get_parameter("frame_width").value
        delay    = self.get_parameter("reconnect_delay").value

        self.get_logger().info(f"Camera URL : {url}")
        self.get_logger().info(f"Target FPS : {fps}")

        self._bridge = CvBridge()
        self._pub    = self.create_publisher(Image, "image_raw", 10)

        cfg = {
            "url": url,
            "target_fps": fps,
            "width": width,
            "reconnect_delay": delay,
        }
        self._cap = IPCameraCapture(cfg)

        # Spin in a thread so the ROS executor stays responsive
        import threading
        self._thread = threading.Thread(target=self._stream, daemon=True)
        self._thread.start()
        self.get_logger().info("camera_node ready — streaming.")

    def _stream(self):
        for ts, frame in self._cap.frames():
            if not rclpy.ok():
                break
            msg = self._bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header = Header()
            msg.header.stamp = self.get_clock().now().to_msg()
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
