"""
Tests for asset_vision.store — AssetStore CRUD, presence logic, roster ordering.

Run with:
    pytest tests/test_store.py -v
"""
import time

from asset_vision.store import AssetStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add(store: AssetStore, asset_id: str, name: str = "", category: str = ""):
    return store.add_asset(asset_id, name=name, category=category,
                           qr_payload=asset_id)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestAddAndGet:
    def test_add_returns_asset(self, store):
        a = _add(store, "AV-0001", name="Laptop", category="electronics")
        assert a.asset_id == "AV-0001"
        assert a.name == "Laptop"
        assert a.category == "electronics"
        assert a.status == "unknown"
        assert a.last_seen is None

    def test_get_asset_by_id(self, store):
        _add(store, "AV-0001", name="Laptop")
        a = store.get_asset("AV-0001")
        assert a is not None
        assert a.name == "Laptop"

    def test_get_asset_not_found_returns_none(self, store):
        assert store.get_asset("DOES-NOT-EXIST") is None

    def test_get_asset_by_qr(self, store):
        _add(store, "AV-0002", name="Charger")
        a = store.get_asset_by_qr("AV-0002")
        assert a is not None
        assert a.asset_id == "AV-0002"

    def test_get_asset_by_qr_not_found_returns_none(self, store):
        assert store.get_asset_by_qr("UNKNOWN-QR") is None

    def test_add_asset_idempotent(self, store):
        """INSERT OR IGNORE — second add with same id is a no-op."""
        _add(store, "AV-0001", name="Laptop")
        _add(store, "AV-0001", name="CHANGED")   # should be ignored
        a = store.get_asset("AV-0001")
        assert a.name == "Laptop"                # original name preserved

    def test_update_asset_name_and_notes(self, store):
        _add(store, "AV-0001", name="Old Name")
        store.update_asset("AV-0001", name="New Name", notes="updated")
        a = store.get_asset("AV-0001")
        assert a.name == "New Name"
        assert a.notes == "updated"

    def test_update_asset_ignores_unknown_fields(self, store):
        """update_asset must not raise on unknown kwargs."""
        _add(store, "AV-0001")
        store.update_asset("AV-0001", nonexistent_field="x")   # should be silent

    def test_delete_asset(self, store):
        _add(store, "AV-0001")
        store.delete_asset("AV-0001")
        assert store.get_asset("AV-0001") is None


# ---------------------------------------------------------------------------
# Presence logic
# ---------------------------------------------------------------------------

class TestPresence:
    def test_mark_seen_sets_present(self, store):
        _add(store, "AV-0001")
        store.mark_seen("AV-0001")
        assert store.get_asset("AV-0001").status == "present"

    def test_mark_seen_updates_last_seen(self, store):
        _add(store, "AV-0001")
        t_before = time.time()
        store.mark_seen("AV-0001")
        t_after = time.time()
        ls = store.get_asset("AV-0001").last_seen
        assert t_before <= ls <= t_after

    def test_mark_seen_with_explicit_ts(self, store):
        _add(store, "AV-0001")
        explicit_ts = 1_000_000.0
        store.mark_seen("AV-0001", ts=explicit_ts)
        assert store.get_asset("AV-0001").last_seen == explicit_ts

    def test_present_to_missing_transition(self, store):
        """Asset marked seen 400 s ago must flip to missing with 300 s window."""
        _add(store, "AV-0001")
        old_ts = time.time() - 400
        store.mark_seen("AV-0001", ts=old_ts)
        store.update_presence(window_sec=300.0)
        assert store.get_asset("AV-0001").status == "missing"

    def test_recent_seen_stays_present(self, store):
        """Asset marked seen 60 s ago stays present with 300 s window."""
        _add(store, "AV-0001")
        store.mark_seen("AV-0001", ts=time.time() - 60)
        store.update_presence(window_sec=300.0)
        assert store.get_asset("AV-0001").status == "present"

    def test_unknown_stays_unknown_after_sweep(self, store):
        """Asset that was never seen must remain 'unknown' after a sweep."""
        _add(store, "AV-NEVER")
        store.update_presence(window_sec=300.0)
        assert store.get_asset("AV-NEVER").status == "unknown"

    def test_update_presence_returns_counts(self, store):
        """update_presence must return a dict keyed by status with int counts."""
        _add(store, "AV-0001")
        store.mark_seen("AV-0001", ts=time.time() - 400)
        _add(store, "AV-0002")
        counts = store.update_presence(window_sec=300.0)
        assert isinstance(counts, dict)
        assert counts.get("missing", 0) >= 1

    def test_multiple_assets_mixed_presence(self, store):
        _add(store, "AV-0001")
        _add(store, "AV-0002")
        _add(store, "AV-0003")
        store.mark_seen("AV-0001", ts=time.time() - 10)    # recent → stays present
        store.mark_seen("AV-0002", ts=time.time() - 400)   # old → missing
        # AV-0003 never seen → unknown
        store.update_presence(window_sec=300.0)
        assert store.get_asset("AV-0001").status == "present"
        assert store.get_asset("AV-0002").status == "missing"
        assert store.get_asset("AV-0003").status == "unknown"


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------

class TestRoster:
    def test_roster_empty(self, store):
        assert store.roster() == []

    def test_roster_contains_all_assets(self, store):
        for i in range(3):
            _add(store, f"AV-{i:04d}")
        assert len(store.roster()) == 3

    def test_roster_ordering_present_first(self, store):
        """Roster order: present → unknown → missing."""
        _add(store, "AV-0001")                              # unknown
        _add(store, "AV-0002")
        store.mark_seen("AV-0002", ts=time.time() - 400)   # will become missing
        _add(store, "AV-0003")
        store.mark_seen("AV-0003")                          # present
        store.update_presence(window_sec=300.0)

        statuses = [a.status for a in store.roster()]
        # present must come before unknown and missing
        first = statuses[0]
        assert first == "present", f"Expected present first, got {statuses}"

    def test_roster_filter_by_status(self, store):
        """roster() returns all; caller can filter by status."""
        for i in range(3):
            _add(store, f"AV-{i:04d}")
        store.mark_seen("AV-0000")
        store.update_presence(window_sec=300.0)

        present = [a for a in store.roster() if a.status == "present"]
        unknown = [a for a in store.roster() if a.status == "unknown"]
        assert len(present) == 1
        assert len(unknown) == 2


# ---------------------------------------------------------------------------
# Detection log
# ---------------------------------------------------------------------------

class TestDetectionLog:
    def test_log_detection_returns_row_id(self, store):
        row_id = store.log_detection("laptop", 0.91, (10, 20, 200, 300))
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_recent_detections_returns_records(self, store):
        store.log_detection("laptop", 0.91, (10, 20, 200, 300))
        store.log_detection("cell phone", 0.78, (50, 60, 150, 200))
        recs = store.recent_detections(10)
        assert len(recs) == 2

    def test_recent_detections_ordered_newest_first(self, store):
        t1 = time.time() - 10
        t2 = time.time()
        store.log_detection("a", 0.9, (0, 0, 10, 10), ts=t1)
        store.log_detection("b", 0.8, (0, 0, 10, 10), ts=t2)
        recs = store.recent_detections(10)
        assert recs[0].label == "b"   # newer first

    def test_log_detection_with_asset_id(self, store):
        _add(store, "AV-0001")
        store.log_detection("laptop", 0.9, (0, 0, 100, 100), asset_id="AV-0001")
        recs = store.recent_detections(1)
        assert recs[0].asset_id == "AV-0001"

    def test_recent_detections_limit(self, store):
        for i in range(10):
            store.log_detection("item", 0.9, (0, 0, 10, 10))
        recs = store.recent_detections(3)
        assert len(recs) == 3


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_empty_db(self, store):
        s = store.stats()
        assert s["total_assets"] == 0
        assert s["total_detections"] == 0
        assert s["by_status"] == {}

    def test_stats_counts_assets(self, store):
        for i in range(4):
            _add(store, f"AV-{i:04d}")
        s = store.stats()
        assert s["total_assets"] == 4

    def test_stats_counts_detections(self, store):
        store.log_detection("x", 0.9, (0, 0, 10, 10))
        store.log_detection("y", 0.8, (0, 0, 10, 10))
        s = store.stats()
        assert s["total_detections"] == 2

    def test_stats_by_status(self, store):
        _add(store, "AV-0001")
        _add(store, "AV-0002")
        store.mark_seen("AV-0001")
        s = store.stats()
        assert s["by_status"].get("present", 0) == 1
        assert s["by_status"].get("unknown", 0) == 1
