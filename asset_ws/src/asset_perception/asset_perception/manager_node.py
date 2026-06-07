"""
manager_node — subscribes /detections, writes to SQLite, runs presence logic,
exposes QueryInventory service.

Reuses store.py from Phase A via sys.path injection.
The web dashboard (web/app.py) reads the SAME SQLite file — no sync needed.

Topics subscribed:
  /detections  (asset_interfaces/AssetDetections)
Services:
  ~/query_inventory  (asset_interfaces/QueryInventory)
Parameters:
  db_path              path to SQLite file (default data/assets.db)
  presence_window_sec  seconds until asset flips to missing (default 300)
  presence_sweep_sec   how often to sweep for missing assets (default 30)
"""
import sys
import time

import rclpy
from rclpy.node import Node

_PROJECT_ROOT = "/mnt/c/Users/salbot01/Salbotics/asset-vision"
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from store import AssetStore  # noqa: E402

from asset_interfaces.msg import AssetDetections       # noqa: E402
from asset_interfaces.srv import QueryInventory        # noqa: E402


class ManagerNode(Node):
    def __init__(self):
        super().__init__("asset_manager_node")

        self.declare_parameter("db_path",             "data/assets.db")
        self.declare_parameter("presence_window_sec", 300.0)
        self.declare_parameter("presence_sweep_sec",   30.0)

        db_path      = self.get_parameter("db_path").value
        self._window = self.get_parameter("presence_window_sec").value
        sweep_sec    = self.get_parameter("presence_sweep_sec").value

        self._store = AssetStore(db_path)
        self.get_logger().info(f"Store opened: {db_path}")

        # Subscribe to detections from perception_node
        self._sub = self.create_subscription(
            AssetDetections, "detections", self._on_detections, 10
        )

        # QueryInventory service
        self._srv = self.create_service(
            QueryInventory, "query_inventory", self._handle_query
        )

        # Periodic presence sweep
        self._sweep_timer = self.create_timer(sweep_sec, self._sweep_presence)

        self._det_count = 0
        self.get_logger().info(
            f"asset_manager_node ready  "
            f"(presence window={self._window}s, sweep every {sweep_sec}s)"
        )

    # ------------------------------------------------------------------
    def _on_detections(self, msg: AssetDetections):
        ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

        for da in msg.detections:
            # Log every detection
            self._store.log_detection(
                label=da.label,
                confidence=da.confidence,
                bbox=(da.x1, da.y1, da.x2, da.y2),
                asset_id=da.asset_id if da.asset_id else None,
                ts=ts,
            )
            # Mark asset as seen if QR was decoded
            if da.asset_id:
                self._store.mark_seen(da.asset_id, ts=ts)

        self._det_count += len(msg.detections)

        if self._det_count % 100 == 0:
            stats = self._store.stats()
            self.get_logger().info(
                f"Detections logged: {self._det_count}  "
                f"Assets: {stats['total_assets']}  "
                f"Present: {stats['by_status'].get('present', 0)}  "
                f"Missing: {stats['by_status'].get('missing', 0)}"
            )

    # ------------------------------------------------------------------
    def _sweep_presence(self):
        counts = self._store.update_presence(self._window)
        self.get_logger().debug(f"Presence sweep: {counts}")

    # ------------------------------------------------------------------
    def _handle_query(
        self,
        request: QueryInventory.Request,
        response: QueryInventory.Response,
    ) -> QueryInventory.Response:
        roster = self._store.roster()

        # Filter if requested
        if request.status_filter:
            roster = [a for a in roster if a.status == request.status_filter]

        response.asset_ids  = [a.asset_id   for a in roster]
        response.names      = [a.name       for a in roster]
        response.categories = [a.category   for a in roster]
        response.statuses   = [a.status     for a in roster]
        response.last_seen  = [float(a.last_seen) if a.last_seen else 0.0
                               for a in roster]

        stats = self._store.stats()
        response.total_assets  = stats["total_assets"]
        response.present_count = stats["by_status"].get("present", 0)
        response.missing_count = stats["by_status"].get("missing", 0)

        self.get_logger().info(
            f"QueryInventory: returned {len(roster)} assets "
            f"(filter={request.status_filter!r})"
        )
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
