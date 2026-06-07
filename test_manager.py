"""Verify manager_node's store interaction without a live ROS daemon."""
import time
from pathlib import Path
from store import AssetStore

TEST_DB = "/tmp/test_manager.db"
Path(TEST_DB).unlink(missing_ok=True)

store = AssetStore(TEST_DB)

# Simulate what _on_detections does
store.add_asset("AV-0001", name="Laptop",   category="electronics", qr_payload="AV-0001")
store.add_asset("AV-0002", name="Charger",  category="electronics", qr_payload="AV-0002")
store.add_asset("AV-0003", name="SSD",      category="storage",     qr_payload="AV-0003")

ts = time.time()
store.log_detection("laptop", 0.88, (10, 20, 200, 300), asset_id="AV-0001", ts=ts)
store.mark_seen("AV-0001", ts=ts)
store.log_detection("cell phone", 0.72, (50, 60, 150, 200), ts=ts)  # untagged

# Simulate QueryInventory (all)
roster = store.roster()
assert len(roster) == 3, f"expected 3 assets, got {len(roster)}"

# Simulate filter by status
store.update_presence(window_sec=300)
present = [a for a in store.roster() if a.status == "present"]
assert len(present) == 1 and present[0].asset_id == "AV-0001", "present filter failed"

# Simulate missing after window
store.mark_seen("AV-0001", ts=time.time() - 400)
store.update_presence(window_sec=300)
missing = [a for a in store.roster() if a.status == "missing"]
assert len(missing) == 1 and missing[0].asset_id == "AV-0001", "missing transition failed"

stats = store.stats()
assert stats["total_assets"] == 3
assert stats["by_status"]["missing"] == 1

print(f"roster: {[a.asset_id for a in roster]}")
print(f"present after mark_seen: {[a.asset_id for a in present]}")
print(f"missing after window: {[a.asset_id for a in missing]}")
print(f"stats: {stats}")
print("ALL MANAGER LOGIC TESTS PASSED")

Path(TEST_DB).unlink(missing_ok=True)
