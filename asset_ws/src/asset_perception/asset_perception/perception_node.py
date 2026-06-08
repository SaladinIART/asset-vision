"""
perception_node — subscribes /image_raw, runs YOLO + QR decode,
publishes AssetDetections on /detections and annotated image on /image_annotated.

Topics subscribed:
  /image_raw          (sensor_msgs/Image)
Topics published:
  /detections         (asset_interfaces/AssetDetections)
  /image_annotated    (sensor_msgs/Image, BGR8)
Parameters:
  model        YOLOv8 weight file (default: yolov8n.pt)
  confidence   detection threshold (default: 0.45)
  device       cpu / cuda (default: cpu)
  project_root path to the asset-vision repo root (auto-set by launch file;
               only needed if `pip install -e .` was NOT run in the ROS2 env)
"""
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from cv_bridge import CvBridge

from asset_interfaces.msg import DetectedAsset, AssetDetections


def _ensure_asset_vision(project_root: str):
    try:
        import asset_vision  # noqa: F401
    except ImportError:
        if not project_root:
            raise RuntimeError(
                "asset_vision package not found. Either run "
                "'pip install -e .' from the repo root, or pass "
                "project_root:=<path> to the launch file."
            )
        if project_root not in sys.path:
            sys.path.insert(0, project_root)


class PerceptionNode(Node):
    def __init__(self):
        super().__init__("perception_node")

        # ── Parameters ──────────────────────────────────────────────────
        self.declare_parameter("project_root", "")
        self.declare_parameter("model",        "yolov8n.pt")
        self.declare_parameter("confidence",   0.45)
        self.declare_parameter("device",       "cpu")

        project_root = self.get_parameter("project_root").value
        _ensure_asset_vision(project_root)

        from asset_vision.detector import YOLODetector          # noqa: E402
        from asset_vision.qrtools  import (                     # noqa: E402
            decode_qr, annotate_qr, associate_qr_to_detections
        )
        self._decode_qr               = decode_qr
        self._annotate_qr             = annotate_qr
        self._associate               = associate_qr_to_detections

        cfg = {
            "model":      self.get_parameter("model").value,
            "confidence": self.get_parameter("confidence").value,
            "device":     self.get_parameter("device").value,
        }

        self.get_logger().info("Loading YOLO model…")
        self._detector = YOLODetector(cfg)
        self._bridge   = CvBridge()

        self._pub_det = self.create_publisher(AssetDetections, "detections", 10)
        self._pub_img = self.create_publisher(Image, "image_annotated", 10)
        self._sub     = self.create_subscription(
            Image, "image_raw", self._on_image, 10
        )

        self._frame_count = 0
        self.get_logger().info("perception_node ready — waiting for /image_raw.")

    # ------------------------------------------------------------------
    def _on_image(self, msg: Image):
        t0 = time.perf_counter()

        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

        detections = self._detector.detect(frame)
        qrs        = self._decode_qr(frame)
        qr_map     = self._associate(qrs, detections)

        for qr in qrs:
            idx = qr_map.get(qr.payload)
            if idx is not None:
                detections[idx].asset_id  = qr.payload
                detections[idx].qr_payload = qr.payload  # type: ignore[attr-defined]

        inference_ms = (time.perf_counter() - t0) * 1000

        stamp   = self.get_clock().now().to_msg()
        det_msg = AssetDetections()
        det_msg.header.stamp    = stamp
        det_msg.header.frame_id = "camera"
        det_msg.frame_width     = frame.shape[1]
        det_msg.frame_height    = frame.shape[0]
        det_msg.inference_ms    = float(inference_ms)

        for d in detections:
            da            = DetectedAsset()
            da.header     = det_msg.header
            da.label      = d.label
            da.confidence = float(d.confidence)
            da.x1, da.y1, da.x2, da.y2 = d.bbox
            da.asset_id   = d.asset_id or ""
            da.qr_payload = getattr(d, "qr_payload", "") or ""
            det_msg.detections.append(da)

        self._pub_det.publish(det_msg)

        annotated = self._detector.annotate(frame, detections)
        annotated = self._annotate_qr(annotated, qrs)
        ann_msg   = self._bridge.cv2_to_imgmsg(annotated, encoding="bgr8")
        ann_msg.header = det_msg.header
        self._pub_img.publish(ann_msg)

        self._frame_count += 1
        if self._frame_count % 30 == 0:
            self.get_logger().info(
                f"Frames: {self._frame_count}  "
                f"Dets: {len(detections)}  "
                f"QRs: {len(qrs)}  "
                f"Inference: {inference_ms:.0f} ms"
            )


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
