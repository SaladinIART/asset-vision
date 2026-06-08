"""
generate_samples.py — create the bundled offline sample images.

Generates 5 synthetic desk-scene frames, each containing a coloured
object rectangle and a scannable QR label. These are used by the
SampleSource when camera.source = "sample" in config.yaml.

Run this once after cloning if the samples/ folder is missing:
    python generate_samples.py

Or customise ASSETS below and re-run to generate different labels.
"""
from pathlib import Path

import cv2
import numpy as np

from asset_vision.qrtools import make_qr_image

# ---------------------------------------------------------------------------
# Customise these to generate your own sample assets
# ---------------------------------------------------------------------------
ASSETS = [
    # (asset_id,  display_name,  BGR colour of the "object" rectangle)
    ("AV-0001", "Laptop",      (60,  80,  180)),
    ("AV-0002", "Phone",       (50,  140, 80)),
    ("AV-0003", "Notebook",    (180, 100, 40)),
    ("AV-0004", "USB Drive",   (200, 60,  60)),
    ("AV-0005", "Headphones",  (100, 60,  180)),
]

OUTPUT_DIR = Path("samples")
JPEG_QUALITY = 90


def make_frame(asset_id: str, name: str, color_bgr: tuple, index: int) -> np.ndarray:
    """Render a 640×480 synthetic desk scene with the object and its QR tag."""
    W, H = 640, 480

    # Warm desk-tone gradient background
    bg = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        bg[y, :] = [int(40 + 30 * t), int(30 + 25 * t), int(20 + 20 * t)]

    # Object rectangle
    ox, oy, ow, oh = 80, 100, 280, 200
    cv2.rectangle(bg, (ox, oy), (ox + ow, oy + oh), color_bgr, -1)
    cv2.rectangle(bg, (ox, oy), (ox + ow, oy + oh), (255, 255, 255), 2)
    cv2.putText(bg, name, (ox + 10, oy + oh // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

    # QR label overlay (bottom-right corner of the object)
    qr_pil = make_qr_image(asset_id, size_px=120)
    qr_np = cv2.cvtColor(np.array(qr_pil.convert("RGB")), cv2.COLOR_RGB2BGR)
    qx, qy = ox + ow - 130, oy + oh - 130
    bg[qy:qy + 120, qx:qx + 120] = qr_np
    cv2.putText(bg, asset_id, (qx, qy - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

    # Caption
    cv2.putText(bg,
                f"Asset-Vision Sample {index + 1}/{len(ASSETS)} — github.com/SaladinIART/asset-vision",
                (8, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 160, 160), 1)

    return bg


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    for i, (aid, name, color) in enumerate(ASSETS):
        frame = make_frame(aid, name, color, i)
        path = OUTPUT_DIR / f"sample_{i + 1:02d}_{aid}.jpg"
        cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        print(f"  {path}")

    print(f"\n{len(ASSETS)} sample images written to {OUTPUT_DIR}/")
    print("Start the dashboard:  bash start.sh")
    print("Open browser:         http://localhost:8100")


if __name__ == "__main__":
    main()
