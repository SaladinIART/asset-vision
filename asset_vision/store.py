"""
SQLite store — assets, detections, presence/last-seen logic.
Source of truth for the whole system (dashboard + ROS2 node both read this).
"""
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)["storage"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Asset:
    asset_id: str
    qr_payload: str
    name: str
    category: str
    created_at: float
    last_seen: Optional[float]
    status: str          # "present" | "missing" | "unknown"
    thumbnail_path: Optional[str]
    notes: str


@dataclass
class DetectionRecord:
    id: int
    ts: float
    asset_id: Optional[str]
    label: str
    confidence: float
    bbox: str            # JSON string "x1,y1,x2,y2"
    frame_path: Optional[str]


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class AssetStore:
    def __init__(self, db_path: str = "data/assets.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_schema()
        log.info("Store ready: %s", db_path)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS assets (
                    asset_id        TEXT PRIMARY KEY,
                    qr_payload      TEXT NOT NULL UNIQUE,
                    name            TEXT NOT NULL DEFAULT '',
                    category        TEXT NOT NULL DEFAULT '',
                    created_at      REAL NOT NULL,
                    last_seen       REAL,
                    status          TEXT NOT NULL DEFAULT 'unknown',
                    thumbnail_path  TEXT,
                    notes           TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS detections (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts          REAL NOT NULL,
                    asset_id    TEXT REFERENCES assets(asset_id),
                    label       TEXT NOT NULL,
                    confidence  REAL NOT NULL,
                    bbox        TEXT NOT NULL,
                    frame_path  TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_detections_ts
                    ON detections(ts DESC);
                CREATE INDEX IF NOT EXISTS idx_detections_asset
                    ON detections(asset_id);
            """)

    # ------------------------------------------------------------------
    # Asset CRUD
    # ------------------------------------------------------------------

    def add_asset(
        self,
        asset_id: str,
        name: str = "",
        category: str = "",
        notes: str = "",
        qr_payload: str = "",
    ) -> Asset:
        qr_payload = qr_payload or asset_id
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO assets
                   (asset_id, qr_payload, name, category, created_at, status, notes)
                   VALUES (?, ?, ?, ?, ?, 'unknown', ?)""",
                (asset_id, qr_payload, name, category, now, notes),
            )
        log.info("Asset registered: %s (%s)", asset_id, name)
        return self.get_asset(asset_id)

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM assets WHERE asset_id = ?", (asset_id,)
            ).fetchone()
        return _row_to_asset(row) if row else None

    def get_asset_by_qr(self, qr_payload: str) -> Optional[Asset]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM assets WHERE qr_payload = ?", (qr_payload,)
            ).fetchone()
        return _row_to_asset(row) if row else None

    def update_asset(self, asset_id: str, **kwargs) -> None:
        allowed = {"name", "category", "notes", "thumbnail_path"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self._conn() as conn:
            conn.execute(
                f"UPDATE assets SET {cols} WHERE asset_id = ?",
                (*fields.values(), asset_id),
            )

    def delete_asset(self, asset_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM assets WHERE asset_id = ?", (asset_id,))

    def roster(self) -> list[Asset]:
        """All assets ordered by status (present first) then name."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM assets
                   ORDER BY CASE status
                       WHEN 'present' THEN 0
                       WHEN 'unknown' THEN 1
                       ELSE 2 END, name"""
            ).fetchall()
        return [_row_to_asset(r) for r in rows]

    # ------------------------------------------------------------------
    # Detection log
    # ------------------------------------------------------------------

    def log_detection(
        self,
        label: str,
        confidence: float,
        bbox: tuple,
        asset_id: Optional[str] = None,
        frame_path: Optional[str] = None,
        ts: Optional[float] = None,
    ) -> int:
        ts = ts or time.time()
        bbox_str = ",".join(str(v) for v in bbox)
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO detections
                   (ts, asset_id, label, confidence, bbox, frame_path)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (ts, asset_id, label, confidence, bbox_str, frame_path),
            )
        return cur.lastrowid

    def recent_detections(self, limit: int = 50) -> list[DetectionRecord]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM detections ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_detection(r) for r in rows]

    # ------------------------------------------------------------------
    # Presence logic
    # ------------------------------------------------------------------

    def mark_seen(self, asset_id: str, ts: Optional[float] = None) -> None:
        """Update last_seen and set status=present for a known asset."""
        ts = ts or time.time()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assets SET last_seen = ?, status = 'present' WHERE asset_id = ?",
                (ts, asset_id),
            )

    def update_presence(self, window_sec: float = 300.0) -> dict[str, int]:
        """
        Flip assets to 'missing' if last_seen > window_sec ago.
        Returns counts: {present, missing, unknown}.
        """
        cutoff = time.time() - window_sec
        with self._conn() as conn:
            conn.execute(
                """UPDATE assets SET status = 'missing'
                   WHERE status = 'present' AND (last_seen IS NULL OR last_seen < ?)""",
                (cutoff,),
            )
            rows = conn.execute(
                "SELECT status, COUNT(*) as n FROM assets GROUP BY status"
            ).fetchall()
        counts = {r["status"]: r["n"] for r in rows}
        log.debug("Presence update: %s", counts)
        return counts

    def stats(self) -> dict:
        with self._conn() as conn:
            n_assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
            n_detections = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
            by_status = conn.execute(
                "SELECT status, COUNT(*) as n FROM assets GROUP BY status"
            ).fetchall()
        return {
            "total_assets": n_assets,
            "total_detections": n_detections,
            "by_status": {r["status"]: r["n"] for r in by_status},
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_asset(row: sqlite3.Row) -> Asset:
    return Asset(
        asset_id=row["asset_id"],
        qr_payload=row["qr_payload"],
        name=row["name"],
        category=row["category"],
        created_at=row["created_at"],
        last_seen=row["last_seen"],
        status=row["status"],
        thumbnail_path=row["thumbnail_path"],
        notes=row["notes"],
    )


def _row_to_detection(row: sqlite3.Row) -> DetectionRecord:
    return DetectionRecord(
        id=row["id"],
        ts=row["ts"],
        asset_id=row["asset_id"],
        label=row["label"],
        confidence=row["confidence"],
        bbox=row["bbox"],
        frame_path=row["frame_path"],
    )


# ---------------------------------------------------------------------------
# CLI / unit test: python store.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    TEST_DB = "/tmp/test_assets.db"
    Path(TEST_DB).unlink(missing_ok=True)

    store = AssetStore(TEST_DB)

    # --- add assets ---
    store.add_asset("AV-0001", name="Laptop", category="electronics", qr_payload="AV-0001")
    store.add_asset("AV-0002", name="Charger", category="electronics", qr_payload="AV-0002")
    store.add_asset("AV-0003", name="Notebook", category="stationery", qr_payload="AV-0003")

    assert store.get_asset("AV-0001").name == "Laptop", "get_asset failed"
    assert store.get_asset_by_qr("AV-0002").asset_id == "AV-0002", "get_by_qr failed"

    # --- mark seen ---
    store.mark_seen("AV-0001")
    store.mark_seen("AV-0002")
    # AV-0003 never seen → stays unknown

    # --- log detections ---
    store.log_detection("laptop", 0.91, (10, 20, 200, 300), asset_id="AV-0001")
    store.log_detection("cell phone", 0.78, (50, 60, 150, 200))

    # --- presence: all recent → present ---
    counts = store.update_presence(window_sec=300)
    assert store.get_asset("AV-0001").status == "present", "should be present"
    assert store.get_asset("AV-0003").status == "unknown", "should be unknown"
    print("  present/missing check 1 OK")

    # --- simulate old last_seen → should flip to missing ---
    old_ts = time.time() - 400
    store.mark_seen("AV-0001", ts=old_ts)
    counts = store.update_presence(window_sec=300)
    assert store.get_asset("AV-0001").status == "missing", "should be missing after window"
    print("  present->missing transition OK")

    # --- roster ---
    roster = store.roster()
    assert len(roster) == 3
    print(f"  roster OK: {[a.asset_id for a in roster]}")

    # --- stats ---
    s = store.stats()
    assert s["total_assets"] == 3
    assert s["total_detections"] == 2
    print(f"  stats OK: {s}")

    # --- recent detections ---
    recs = store.recent_detections(10)
    assert len(recs) == 2
    print(f"  recent_detections OK: {len(recs)} records")

    Path(TEST_DB).unlink(missing_ok=True)
    print("\nALL TESTS PASSED")
