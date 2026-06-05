"""
Camera capture — reads MJPEG stream from IP Webcam app on Oppo Reno7.
Yields BGR numpy frames; auto-reconnects on drop.
"""
import time
import logging
import yaml
import cv2
import numpy as np

log = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)["camera"]


class IPCameraCapture:
    def __init__(self, cfg: dict):
        self.url = cfg["url"]
        self.target_fps = cfg.get("target_fps", 5)
        self.width = cfg.get("width", 640)
        self.reconnect_delay = cfg.get("reconnect_delay", 3)
        self._cap: cv2.VideoCapture | None = None
        self._frame_interval = 1.0 / self.target_fps

    # ------------------------------------------------------------------
    def _open(self) -> bool:
        if self._cap:
            self._cap.release()
        log.info("Connecting to %s", self.url)
        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # minimise latency
        if cap.isOpened():
            self._cap = cap
            log.info("Connected.")
            return True
        cap.release()
        return False

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        if w == self.width:
            return frame
        scale = self.width / w
        return cv2.resize(frame, (self.width, int(h * scale)))

    # ------------------------------------------------------------------
    def frames(self):
        """Yield (timestamp, frame) tuples indefinitely; reconnects on drop."""
        while True:
            if not self._open():
                log.warning("Could not connect; retrying in %ds", self.reconnect_delay)
                time.sleep(self.reconnect_delay)
                continue

            last = time.monotonic()
            while True:
                ok, frame = self._cap.read()
                if not ok or frame is None:
                    log.warning("Stream lost; reconnecting…")
                    break

                now = time.monotonic()
                elapsed = now - last
                if elapsed < self._frame_interval:
                    time.sleep(self._frame_interval - elapsed)
                last = time.monotonic()

                yield time.time(), self._resize(frame)

    def save_sample(self, path: str = "data/sample.jpg") -> bool:
        """Grab one frame and save it to disk (useful for testing)."""
        import os; os.makedirs(os.path.dirname(path), exist_ok=True)
        for ts, frame in self.frames():
            cv2.imwrite(path, frame)
            log.info("Saved sample → %s", path)
            return True

    def release(self):
        if self._cap:
            self._cap.release()


# ---------------------------------------------------------------------------
# Quick test: python capture.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    cfg = load_config()

    if "--sample" in sys.argv:
        IPCameraCapture(cfg).save_sample()
        sys.exit(0)

    cap = IPCameraCapture(cfg)
    print("Streaming — press Q to quit")
    for ts, frame in cap.frames():
        cv2.imshow("Asset-Vision capture test", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()
