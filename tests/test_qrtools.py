"""
Tests for asset_vision.qrtools — QR generation, decode round-trip, IoU association.

These tests are pure-Python; no camera or YOLO model required.

Run with:
    pytest tests/test_qrtools.py -v
"""
from dataclasses import dataclass

import cv2
import numpy as np
import pytest
from PIL import Image

from asset_vision.qrtools import (
    DecodedQR,
    annotate_qr,
    associate_qr_to_detections,
    decode_qr,
    make_asset_label,
    make_qr_image,
    make_label_sheet,
)


# ---------------------------------------------------------------------------
# Minimal Detection stand-in (avoids loading YOLO / ultralytics)
# ---------------------------------------------------------------------------

@dataclass
class _Det:
    """Minimal detection mock — only .bbox is needed by associate_qr_to_detections."""
    bbox: tuple[int, int, int, int]
    label: str = "object"
    confidence: float = 0.9
    asset_id: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pil_to_bgr(img: Image.Image) -> np.ndarray:
    """Convert PIL RGB image to BGR numpy array (as OpenCV uses)."""
    arr = np.array(img.convert("RGB"))
    return arr[:, :, ::-1].copy()


def _make_qr_frame(payload: str, size: int = 400) -> np.ndarray:
    """Generate a BGR frame containing a single scannable QR code."""
    return _pil_to_bgr(make_qr_image(payload, size_px=size))


# ---------------------------------------------------------------------------
# make_qr_image
# ---------------------------------------------------------------------------

class TestMakeQrImage:
    def test_returns_pil_image(self):
        img = make_qr_image("AV-TEST")
        assert isinstance(img, Image.Image)

    def test_size_matches_parameter(self):
        img = make_qr_image("AV-TEST", size_px=200)
        assert img.size == (200, 200)

    def test_default_size(self):
        img = make_qr_image("AV-TEST")
        assert img.size == (300, 300)

    def test_different_payloads_differ(self):
        a = np.array(make_qr_image("AV-AAA"))
        b = np.array(make_qr_image("AV-BBB"))
        # Different payloads must produce different pixel matrices
        assert not np.array_equal(a, b)


# ---------------------------------------------------------------------------
# make_asset_label
# ---------------------------------------------------------------------------

class TestMakeAssetLabel:
    def test_returns_pil_image(self):
        img = make_asset_label("0001", name="Laptop")
        assert isinstance(img, Image.Image)

    def test_height_larger_than_width(self):
        """Label strip is added below the QR, so height > QR square."""
        img = make_asset_label("0001", size_px=300)
        w, h = img.size
        assert h > w or h > 300

    def test_prefix_prepended_when_missing(self):
        """make_asset_label("0001") should produce payload "AV-0001"."""
        img = make_asset_label("0001", size_px=200)
        frame = _pil_to_bgr(img)
        qrs = decode_qr(frame)
        assert len(qrs) >= 1
        assert qrs[0].payload == "AV-0001"

    def test_prefix_not_doubled(self):
        """make_asset_label("AV-0001") must not produce "AV-AV-0001"."""
        img = make_asset_label("AV-0001", size_px=200)
        frame = _pil_to_bgr(img)
        qrs = decode_qr(frame)
        assert len(qrs) >= 1
        assert qrs[0].payload == "AV-0001"


# ---------------------------------------------------------------------------
# decode_qr (round-trip)
# ---------------------------------------------------------------------------

class TestDecodeQr:
    def test_round_trip_basic(self):
        """Generate → encode to BGR → decode → payload matches."""
        payload = "AV-0099"   # short payload → clean modules at 400 px
        frame = _make_qr_frame(payload)
        qrs = decode_qr(frame)
        assert len(qrs) == 1
        assert qrs[0].payload == payload

    def test_round_trip_preserves_dashes(self):
        frame = _make_qr_frame("AV-0042")
        qrs = decode_qr(frame)
        assert qrs[0].payload == "AV-0042"

    def test_decoded_qr_has_polygon(self):
        frame = _make_qr_frame("AV-POLY")
        qrs = decode_qr(frame)
        assert len(qrs[0].polygon) >= 4

    def test_decoded_qr_bbox_is_tuple_of_4(self):
        frame = _make_qr_frame("AV-BBOX")
        qrs = decode_qr(frame)
        assert len(qrs[0].bbox) == 4

    def test_decoded_qr_bbox_is_within_frame(self):
        frame = _make_qr_frame("AV-INFRAME", size=400)
        qrs = decode_qr(frame)
        x1, y1, x2, y2 = qrs[0].bbox
        h, w = frame.shape[:2]
        assert 0 <= x1 < x2 <= w
        assert 0 <= y1 < y2 <= h

    def test_blank_frame_returns_empty(self):
        """Solid white frame — no QR code → empty list."""
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 255
        qrs = decode_qr(frame)
        assert qrs == []

    def test_noisy_frame_returns_empty_or_succeeds(self):
        """Random noise should not raise; it may or may not find codes."""
        rng = np.random.default_rng(42)
        frame = (rng.random((480, 640, 3)) * 255).astype(np.uint8)
        qrs = decode_qr(frame)
        assert isinstance(qrs, list)


# ---------------------------------------------------------------------------
# annotate_qr
# ---------------------------------------------------------------------------

class TestAnnotateQr:
    def test_returns_same_shape(self):
        frame = _make_qr_frame("AV-ANN")
        qrs = decode_qr(frame)
        out = annotate_qr(frame, qrs)
        assert out.shape == frame.shape

    def test_does_not_mutate_original(self):
        frame = _make_qr_frame("AV-NOMUT")
        original = frame.copy()
        qrs = decode_qr(frame)
        annotate_qr(frame, qrs)
        assert np.array_equal(frame, original)

    def test_empty_qr_list_leaves_frame_unchanged(self):
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
        out = annotate_qr(frame, [])
        assert np.array_equal(out, frame)


# ---------------------------------------------------------------------------
# associate_qr_to_detections (IoU)
# ---------------------------------------------------------------------------

class TestAssociateQrToDetections:
    """
    Frame coordinate convention: (x1, y1, x2, y2) top-left to bottom-right.
    """

    def test_overlapping_maps_correctly(self):
        """QR fully inside detection bbox — must map to that detection."""
        qrs = [DecodedQR(payload="AV-0001", polygon=[], bbox=(10, 10, 90, 90))]
        dets = [_Det(bbox=(5, 5, 100, 100))]      # large box containing QR
        mapping = associate_qr_to_detections(qrs, dets)
        assert mapping.get("AV-0001") == 0

    def test_non_overlapping_returns_empty(self):
        """QR and detection do not overlap — no mapping."""
        qrs = [DecodedQR(payload="AV-0001", polygon=[], bbox=(0, 0, 50, 50))]
        dets = [_Det(bbox=(200, 200, 300, 300))]
        mapping = associate_qr_to_detections(qrs, dets)
        assert "AV-0001" not in mapping

    def test_empty_detections_returns_empty(self):
        qrs = [DecodedQR(payload="AV-0001", polygon=[], bbox=(10, 10, 90, 90))]
        mapping = associate_qr_to_detections(qrs, [])
        assert mapping == {}

    def test_empty_qrs_returns_empty(self):
        dets = [_Det(bbox=(0, 0, 100, 100))]
        mapping = associate_qr_to_detections([], dets)
        assert mapping == {}

    def test_multiple_qrs_each_maps_to_nearest(self):
        """Two QRs, each sitting inside one of two non-overlapping detections."""
        qrs = [
            DecodedQR(payload="AV-A", polygon=[], bbox=(5, 5, 45, 45)),
            DecodedQR(payload="AV-B", polygon=[], bbox=(105, 105, 145, 145)),
        ]
        dets = [
            _Det(bbox=(0, 0, 50, 50)),     # det 0 → should match AV-A
            _Det(bbox=(100, 100, 150, 150)),  # det 1 → should match AV-B
        ]
        mapping = associate_qr_to_detections(qrs, dets)
        assert mapping.get("AV-A") == 0
        assert mapping.get("AV-B") == 1

    def test_best_iou_wins(self):
        """When two detections overlap the QR, the higher-IoU one wins."""
        qrs = [DecodedQR(payload="AV-BEST", polygon=[], bbox=(10, 10, 60, 60))]
        dets = [
            _Det(bbox=(0, 0, 200, 200)),    # big box, low IoU
            _Det(bbox=(8, 8, 62, 62)),      # tight box, high IoU → winner
        ]
        mapping = associate_qr_to_detections(qrs, dets)
        assert mapping.get("AV-BEST") == 1

    def test_iou_threshold_respected(self):
        """Very tiny overlap below threshold must not produce a mapping."""
        # QR at (0,0,100,100), detection touching only at 1 pixel column
        qrs = [DecodedQR(payload="AV-TINY", polygon=[], bbox=(0, 0, 100, 100))]
        dets = [_Det(bbox=(99, 0, 200, 100))]   # 1px wide overlap, tiny IoU
        mapping = associate_qr_to_detections(qrs, dets, iou_threshold=0.05)
        # IoU = 100/(100*100 + 101*100 - 100) ≈ 0.005 < 0.05 → no mapping
        assert "AV-TINY" not in mapping


# ---------------------------------------------------------------------------
# make_label_sheet (smoke test)
# ---------------------------------------------------------------------------

class TestMakeLabelSheet:
    def test_sheet_creates_file(self, tmp_path):
        out = str(tmp_path / "sheet.png")
        make_label_sheet([("0001", "Laptop"), ("0002", "Mouse")], out)
        assert (tmp_path / "sheet.png").exists()

    def test_sheet_is_valid_png(self, tmp_path):
        out = str(tmp_path / "sheet.png")
        make_label_sheet([("0001", "Test")], out)
        img = Image.open(out)
        assert img.format == "PNG"

    def test_sheet_dimensions_scale_with_count(self, tmp_path):
        one_col = str(tmp_path / "one.png")
        two_col = str(tmp_path / "two.png")
        make_label_sheet([("0001", "A")], one_col, cols=1)
        make_label_sheet([("0001", "A"), ("0002", "B"), ("0003", "C"),
                          ("0004", "D")], two_col, cols=2)
        h1 = Image.open(one_col).size[1]
        h2 = Image.open(two_col).size[1]
        assert h2 > h1   # more rows → taller sheet
