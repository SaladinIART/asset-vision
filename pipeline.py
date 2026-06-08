"""
Pipeline — wires capture -> detect -> QR -> associate -> store -> annotate.
Runs as a thread; exposes a frame queue for the web dashboard.
"""
import logging
import queue
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml

from capture import make_source
from detector import YOLODetector
from qrtools import decode_qr, annotate_qr, associate_qr_to_detections
from store import AssetStore

log = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class Pipeline:
    """
    Runs the perception loop in a background thread.
    Call start() / stop(); read latest annotated frame via get_frame().
    """

    def __init__(self, config_path: str = "config.yaml"):
        cfg = load_config(config_path)
        self.cfg = cfg
        self.store = AssetStore(cfg["storage"]["db_path"])
        self.presence_window = cfg["storage"]["presence_window_sec"]
        self.frames_dir = Path(cfg["storage"]["frames_dir"])
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        self._capture = make_source(cfg["camera"])
        self._detector = YOLODetector(cfg["detection"])

        self._frame_q: queue.Queue = queue.Queue(maxsize=2)
        self._stop_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._stats = {"frames": 0, "detections": 0, "qr_hits": 0, "fps": 0.0}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="pipeline")
        self._thread.start()
        log.info("Pipeline started.")

    def stop(self):
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._capture.release()
        log.info("Pipeline stopped.")

    def get_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Return the latest annotated frame, or None if nothing available."""
        try:
            return self._frame_q.get(timeout=timeout)
        except queue.Empty:
            return None

    def stats(self) -> dict:
        return dict(self._stats)

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    def _loop(self):
        fps_counter, fps_ts = 0, time.monotonic()
        last_presence_update = 0.0

        for ts, frame in self._capture.frames():
            if self._stop_evt.is_set():
                break

            # --- YOLO detection ---
            detections = self._detector.detect(frame)

            # --- QR decode ---
            qrs = decode_qr(frame)

            # --- Associate QR payloads -> detection boxes ---
            qr_map = associate_qr_to_detections(qrs, detections)
            # qr_map: {qr_payload: detection_index}

            # --- Resolve asset IDs + update store ---
            seen_asset_ids = set()
            save_frame = bool(qrs)   # save frame snapshot when QR found

            frame_path: Optional[str] = None
            if save_frame:
                fname = self.frames_dir / f"{int(ts * 1000)}.jpg"
                cv2.imwrite(str(fname), frame)
                frame_path = str(fname)

            for qr in qrs:
                asset = self.store.get_asset_by_qr(qr.payload)
                if asset:
                    det_idx = qr_map.get(qr.payload)
                    if det_idx is not None:
                        detections[det_idx].asset_id = asset.asset_id
                    self.store.mark_seen(asset.asset_id, ts=ts)
                    seen_asset_ids.add(asset.asset_id)
                    self._stats["qr_hits"] += 1

            # Log all detections (linked to asset if matched)
            for det in detections:
                self.store.log_detection(
                    label=det.label,
                    confidence=det.confidence,
                    bbox=det.bbox,
                    asset_id=det.asset_id,
                    frame_path=frame_path,
                    ts=ts,
                )

            # --- Presence sweep (every 30 s) ---
            if ts - last_presence_update > 30:
                self.store.update_presence(self.presence_window)
                last_presence_update = ts

            # --- Annotate frame ---
            annotated = self._detector.annotate(frame, detections)
            annotated = annotate_qr(annotated, qrs)

            # Overlay stats
            fps_counter += 1
            now = time.monotonic()
            if now - fps_ts >= 2.0:
                self._stats["fps"] = fps_counter / (now - fps_ts)
                fps_counter, fps_ts = 0, now

            s = self.stats()
            cv2.putText(annotated,
                        f"FPS:{s['fps']:.1f}  det:{s['detections']}  qr:{s['qr_hits']}",
                        (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

            self._stats["frames"] += 1
            self._stats["detections"] += len(detections)

            # Push to frame queue (drop oldest if full)
            if self._frame_q.full():
                try:
                    self._frame_q.get_nowait()
                except queue.Empty:
                    pass
            self._frame_q.put(annotated)


# ---------------------------------------------------------------------------
# CLI test: python pipeline.py
# Displays annotated feed in an OpenCV window (requires WSLg / display).
# Press Q to quit.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    p = Pipeline()

    def _shutdown(sig, frame):
        log.info("Shutting down…")
        p.stop()
        cv2.destroyAllWindows()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    p.start()
    log.info("Pipeline running — press Q in the window to quit.")

    while True:
        frame = p.get_frame(timeout=0.5)
        if frame is None:
            continue
        cv2.imshow("Asset-Vision", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    p.stop()
    cv2.destroyAllWindows()

    s = p.stats()
    print(f"\nSession: {s['frames']} frames  {s['detections']} detections  {s['qr_hits']} QR hits")
