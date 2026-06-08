"""
YOLO detection module — wraps Ultralytics YOLOv8n for CPU inference.
Returns structured detection results; draws annotated frames.
"""
import time
import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

log = logging.getLogger(__name__)

_COLORS = [
    (56, 189, 248), (251, 146, 60), (52, 211, 153), (167, 139, 250),
    (251, 191, 36), (244, 114, 182), (34, 211, 238), (163, 230, 53),
]


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]   # x1, y1, x2, y2
    class_id: int = 0
    asset_id: str | None = None       # filled in by pipeline after QR association


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)["detection"]


class YOLODetector:
    def __init__(self, cfg: dict):
        model_path = cfg.get("model", "yolov8n.pt")
        self.conf = cfg.get("confidence", 0.45)
        self.device = cfg.get("device", "cpu")
        log.info("Loading model %s on %s …", model_path, self.device)
        self.model = YOLO(model_path)
        self.model.to(self.device)
        log.info("Model ready — %d classes", len(self.model.names))

    # ------------------------------------------------------------------
    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run inference on a BGR frame; return list of Detection."""
        t0 = time.perf_counter()
        results = self.model(frame, conf=self.conf, verbose=False)[0]
        elapsed = time.perf_counter() - t0
        log.debug("Inference %.0f ms, %d detections", elapsed * 1000, len(results.boxes))

        detections: list[Detection] = []
        for box in results.boxes:
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
            cls = int(box.cls[0])
            detections.append(Detection(
                label=self.model.names[cls],
                confidence=float(box.conf[0]),
                bbox=(x1, y1, x2, y2),
                class_id=cls,
            ))
        return detections

    # ------------------------------------------------------------------
    def annotate(
        self,
        frame: np.ndarray,
        detections: list[Detection],
        *,
        show_conf: bool = True,
    ) -> np.ndarray:
        """Draw boxes + labels on a copy of frame; return annotated copy."""
        out = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = _COLORS[det.class_id % len(_COLORS)]
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

            label = det.asset_id if det.asset_id else det.label
            if show_conf:
                label = f"{label} {det.confidence:.0%}"

            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
            cv2.putText(out, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
        return out

    # ------------------------------------------------------------------
    def benchmark(self, frame: np.ndarray, runs: int = 10) -> float:
        """Return average FPS over `runs` inferences."""
        t0 = time.perf_counter()
        for _ in range(runs):
            self.detect(frame)
        fps = runs / (time.perf_counter() - t0)
        log.info("Benchmark: %.1f FPS (avg over %d runs)", fps, runs)
        return fps


# ---------------------------------------------------------------------------
# Quick test: python detector.py [image_path]
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    cfg = load_config()
    detector = YOLODetector(cfg)

    if len(sys.argv) > 1:
        img_path = sys.argv[1]
        frame = cv2.imread(img_path)
        if frame is None:
            print(f"Cannot read {img_path}")
            sys.exit(1)
    else:
        # generate a blank test frame if no image provided
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "No image — pass path as arg", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

    dets = detector.detect(frame)
    print(f"\nDetected {len(dets)} object(s):")
    for d in dets:
        print(f"  {d.label:20s}  conf={d.confidence:.2f}  bbox={d.bbox}")

    annotated = detector.annotate(frame, dets)
    out_path = "data/detect_test.jpg"
    Path("data").mkdir(exist_ok=True)
    cv2.imwrite(out_path, annotated)
    print(f"\nAnnotated frame saved → {out_path}")

    fps = detector.benchmark(frame)
    print(f"Benchmark: {fps:.1f} FPS on CPU")
