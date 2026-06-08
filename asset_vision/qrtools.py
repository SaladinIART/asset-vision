"""
QR tools — generate printable asset labels and decode QR codes from frames.
"""
import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import qrcode
import yaml
from PIL import Image, ImageDraw, ImageFont
from pyzbar import pyzbar

log = logging.getLogger(__name__)

_LABEL_BG = (255, 255, 255)
_LABEL_FG = (30, 30, 30)


@dataclass
class DecodedQR:
    payload: str                          # raw string inside the QR
    polygon: list[tuple[int, int]]        # corner points in the frame
    bbox: tuple[int, int, int, int]       # x1, y1, x2, y2 bounding rect


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return cfg["qr"]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def make_qr_image(payload: str, size_px: int = 300) -> Image.Image:
    """Return a PIL Image of a QR code for `payload`."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size_px, size_px), Image.LANCZOS)


def make_asset_label(
    asset_id: str,
    name: str = "",
    size_px: int = 300,
    *,
    prefix: str = "AV-",
) -> Image.Image:
    """Return a labelled QR PNG: QR code + asset_id text below it."""
    payload = f"{prefix}{asset_id}" if not asset_id.startswith(prefix) else asset_id
    qr_img = make_qr_image(payload, size_px)

    label_h = 48
    canvas = Image.new("RGB", (size_px, size_px + label_h), _LABEL_BG)
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
        small = font

    line1 = payload
    line2 = name[:28] if name else ""
    _, _, tw, _ = draw.textbbox((0, 0), line1, font=font)
    draw.text(((size_px - tw) // 2, size_px + 4), line1, fill=_LABEL_FG, font=font)
    if line2:
        _, _, tw2, _ = draw.textbbox((0, 0), line2, font=small)
        draw.text(((size_px - tw2) // 2, size_px + 28), line2, fill=(80, 80, 80), font=small)

    return canvas


def make_label_sheet(
    assets: list[tuple[str, str]],   # [(asset_id, name), …]
    out_path: str,
    cols: int = 3,
    label_size_px: int = 300,
    *,
    prefix: str = "AV-",
    margin: int = 20,
) -> str:
    """Generate a printable PNG sheet of QR labels. Returns saved path."""
    rows = (len(assets) + cols - 1) // cols
    label_h = label_size_px + 48
    w = cols * label_size_px + (cols + 1) * margin
    h = rows * label_h + (rows + 1) * margin

    sheet = Image.new("RGB", (w, h), (240, 240, 240))
    for i, (aid, name) in enumerate(assets):
        col, row = i % cols, i // cols
        x = margin + col * (label_size_px + margin)
        y = margin + row * (label_h + margin)
        label = make_asset_label(aid, name, label_size_px, prefix=prefix)
        sheet.paste(label, (x, y))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, dpi=(300, 300))
    log.info("Label sheet saved → %s  (%d labels)", out_path, len(assets))
    return out_path


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------

def decode_qr(frame: np.ndarray) -> list[DecodedQR]:
    """Decode all QR codes in a BGR frame. Returns list of DecodedQR."""
    results: list[DecodedQR] = []
    for obj in pyzbar.decode(frame):
        if obj.type not in ("QRCODE", "CODE128", "EAN13"):
            continue
        payload = obj.data.decode("utf-8", errors="replace")
        pts = [(p.x, p.y) for p in obj.polygon]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        results.append(DecodedQR(payload=payload, polygon=pts, bbox=bbox))
    return results


def annotate_qr(frame: np.ndarray, qrs: list[DecodedQR]) -> np.ndarray:
    """Draw QR outlines + payload text on a copy of frame."""
    out = frame.copy()
    for qr in qrs:
        pts = np.array(qr.polygon, dtype=np.int32)
        cv2.polylines(out, [pts], True, (0, 255, 128), 2)
        x1, y1, _, _ = qr.bbox
        cv2.putText(out, qr.payload, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 128), 2, cv2.LINE_AA)
    return out


# ---------------------------------------------------------------------------
# Spatial association helper (used by pipeline)
# ---------------------------------------------------------------------------

def associate_qr_to_detections(
    qrs: list[DecodedQR],
    detections,               # list[Detection] from detector.py
    iou_threshold: float = 0.05,
) -> dict[str, str]:
    """
    Return {payload: detection_index_str} mapping QR payloads to the
    nearest detection by IoU overlap. Detection must overlap the QR bbox.
    """
    mapping: dict[str, str] = {}
    for qr in qrs:
        qx1, qy1, qx2, qy2 = qr.bbox
        best_iou, best_idx = 0.0, -1
        for i, det in enumerate(detections):
            dx1, dy1, dx2, dy2 = det.bbox
            ix1, iy1 = max(qx1, dx1), max(qy1, dy1)
            ix2, iy2 = min(qx2, dx2), min(qy2, dy2)
            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            if inter == 0:
                continue
            union = (qx2-qx1)*(qy2-qy1) + (dx2-dx1)*(dy2-dy1) - inter
            iou = inter / union if union else 0
            if iou > best_iou:
                best_iou, best_idx = iou, i
        if best_iou >= iou_threshold and best_idx >= 0:
            mapping[qr.payload] = best_idx
    return mapping


# ---------------------------------------------------------------------------
# CLI: python qrtools.py --gen AV-0001 "My Laptop"
#      python qrtools.py --sheet  (generates a sample 6-label sheet)
#      python qrtools.py --decode data/sample.jpg
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    cfg = load_config()
    prefix = cfg.get("prefix", "AV-")

    if "--gen" in sys.argv:
        idx = sys.argv.index("--gen")
        aid = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "0001"
        name = sys.argv[idx + 2] if idx + 2 < len(sys.argv) else ""
        out = f"data/label_{aid}.png"
        make_asset_label(aid, name, prefix=prefix).save(out)
        print(f"Label saved → {out}")

    elif "--sheet" in sys.argv:
        samples = [(f"000{i}", n) for i, n in enumerate(
            ["Laptop", "Charger", "Mouse", "Headphones", "Notebook", "Pen"], 1)]
        make_label_sheet(samples, "data/label_sheet.png", prefix=prefix)
        print("Sheet saved → data/label_sheet.png")

    elif "--decode" in sys.argv:
        idx = sys.argv.index("--decode")
        img_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        frame = cv2.imread(img_path)
        if frame is None:
            print(f"Cannot read {img_path}")
            sys.exit(1)
        qrs = decode_qr(frame)
        print(f"Found {len(qrs)} QR code(s):")
        for q in qrs:
            print(f"  payload={q.payload!r}  bbox={q.bbox}")
        out = annotate_qr(frame, qrs)
        out_path = "data/qr_annotated.jpg"
        cv2.imwrite(out_path, out)
        print(f"Annotated → {out_path}")

    else:
        print("Usage:")
        print("  python qrtools.py --gen <asset_id> [name]")
        print("  python qrtools.py --sheet")
        print("  python qrtools.py --decode <image_path>")
