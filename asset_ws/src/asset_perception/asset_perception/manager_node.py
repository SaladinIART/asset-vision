"""
manager_node — subscribes /detections, writes to SQLite, runs presence logic,
exposes QueryInventory service.

The web dashboard reads the same SQLite file — no sync needed.

Topics subscribed:
  /detections  (asset_interfaces/AssetDetections)
Services:
  ~/query_inventory  (asset_interfaces/QueryInventory)
Parameters:
  db_path              path to SQLite file (default: data/assets.db)
  presence_window_sec  seconds until asset flips to missing (default: 300)
  presence_sweep_sec   how often to sweep for missing assets (default: 30)
  project_root         path to the asset-vision repo root (auto-set by launch file;
                       only needed if `pip install -e .` was NOT run in the ROS2 env)
"""
import sys
import time

import rclpy
from rclpy.node import Node

from asset_interfaces.msg import AssetDetections
from asset_interfaces.srv import QueryInventory


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


class ManagerNode(Node):
    def __init__(self):
        super().__init__("asset_manager_node")

        # ── Parameters ──────────────────────────────────────────────────
        self.declare_parameter("project_root",         "")
        self.declare_parameter("db_path",              "data/assets.db")
        self.declare_parameter("presence_window_sec",  300.0)
        self.declare_parameter("presence_sweep_sec",    30.0)

        project_root = self.get_parameter("project_root").value
        _ensure_asset_vision(project_root)

        from asset_vision.store import AssetStore  # noqa: E402

        db_path      = self.get_parameter("db_path").value
        self._window = self.get_parameter("presence_window_sec").value
        sweep_sec    = self.get_parameter("presence_sweep_sec").value

        self._store = AssetStore(db_path)
        self.get_logger().info(f"Store opened: {db_path}")

        self._sub = self.create_subscription(
            AssetDetections, "detections", self._on_detections, 10
        )
        self._srv = self.create_service(
            QueryInventory, "query_inventory", self._handle_query
        )
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
            self._store.log_detection(
                label=da.label,
                confidence=da.confidence,
                bbox=(da.x1, da.y1, da.x2, da.y2),
                asset_id=da.asset_id if da.asset_id else None,
                ts=ts,
            )
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

        if request.status_filter:
            roster = [a for a in roster if a.status == request.status_filter]

        response.asset_ids  = [a.asset_id  for a in roster]
        response.names      = [a.name      for a in roster]
        response.categories = [a.category  for a in roster]
        response.statuses   = [a.status    for a in roster]
        response.last_seen  = [
            float(a.last_seen) if a.last_seen else 0.0 for a in roster
        ]

        stats = self._store.stats()
        response.total_assets  = stats["total_assets"]
        response.present_count = stats["by_status"].get("present", 0)
        response.missing_count = stats["by_status"].get("missing", 0)

        self.get_logger().info(
            f"QueryInventory: {len(roster)} assets (filter={request.status_filter!r})"
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
