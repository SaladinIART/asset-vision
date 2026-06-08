"""
capture.py — pluggable camera source abstraction.

Supported sources (set `camera.source` in config.yaml):

  sample      Loop images from the samples/ folder — no hardware needed.
              Perfect for first-run, CI, and offline demos.
  usb         USB camera via cv2.VideoCapture(index). Needs a physical USB
              camera. Works natively on Linux; on WSL2 requires usbipd-win.
  integrated  Laptop/built-in webcam — same as `usb` but index defaults to 0.
              Same WSL2 caveat applies.
  ipcam       Network IP camera (e.g. phone running IP Webcam app over WiFi).
              No driver pain; works in WSL2 out of the box; WiFi adds ~100–300 ms
              latency compared to USB.

All backends implement the same interface:
    .frames()         → generator yielding (timestamp: float, frame: np.ndarray)
    .save_sample(path) → grab one frame and write it to disk
    .release()        → free resources

Factory:
    make_source(cfg: dict) → one of the classes above

See docs/CAMERA_SOURCES.md for a full comparison (latency, risk, WSL2 support).
"""
from __future__ import annotations

import glob
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Tuple

import cv2
import numpy as np
import yaml

log = logging.getLogger(__name__)

Frame = np.ndarray
FrameYield = Iterator[Tuple[float, Frame]]


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class CameraSource(ABC):
    """Common interface every source must implement."""

    @abstractmethod
    def frames(self) -> FrameYield:
        """Yield (unix_timestamp, BGR_frame) indefinitely."""

    def save_sample(self, path: str = "data/sample.jpg") -> bool:
        """Grab one frame and save it to disk. Returns True on success."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        for _, frame in self.frames():
            cv2.imwrite(path, frame)
            log.info("Saved sample → %s", path)
            return True
        return False

    def release(self):
        """Override to free hardware resources."""


# ---------------------------------------------------------------------------
# IP Camera (phone / network cam via MJPEG)
# ---------------------------------------------------------------------------

class IPCameraCapture(CameraSource):
    """
    Read MJPEG stream from a network IP camera (e.g. Android IP Webcam app).

    Best for: WSL2 (no driver setup), shared/remote setups.
    Tradeoff: WiFi adds ~100–300 ms latency; stream can drop.
    Config keys: url, target_fps, width, reconnect_delay
    """

    def __init__(self, cfg: dict):
        self.url = cfg["url"]
        self.target_fps = cfg.get("target_fps", 5)
        self.width = cfg.get("width", 640)
        self.reconnect_delay = cfg.get("reconnect_delay", 3)
        self._cap: cv2.VideoCapture | None = None
        self._frame_interval = 1.0 / max(self.target_fps, 1)

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

    def _resize(self, frame: Frame) -> Frame:
        h, w = frame.shape[:2]
        if w == self.width:
            return frame
        scale = self.width / w
        return cv2.resize(frame, (self.width, int(h * scale)))

    def frames(self) -> FrameYield:
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

    def release(self):
        if self._cap:
            self._cap.release()
            self._cap = None


# ---------------------------------------------------------------------------
# USB / integrated webcam
# ---------------------------------------------------------------------------

class UsbCameraCapture(CameraSource):
    """
    Read from a USB or integrated (built-in laptop) webcam.

    Best for: native Linux, Windows; lowest latency for local cameras.
    WSL2 caveat: requires usbipd-win passthrough — see docs/CAMERA_SOURCES.md.
    Config keys: index (default 0), target_fps, width
    """

    def __init__(self, cfg: dict):
        self.index = cfg.get("index", 0)
        self.target_fps = cfg.get("target_fps", 15)
        self.width = cfg.get("width", 640)
        self._cap: cv2.VideoCapture | None = None
        self._frame_interval = 1.0 / max(self.target_fps, 1)

    def _open(self) -> bool:
        log.info("Opening camera index %d", self.index)
        cap = cv2.VideoCapture(self.index)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            self._cap = cap
            log.info("USB/integrated camera ready (index=%d).", self.index)
            return True
        cap.release()
        return False

    def _resize(self, frame: Frame) -> Frame:
        h, w = frame.shape[:2]
        if w == self.width:
            return frame
        scale = self.width / w
        return cv2.resize(frame, (self.width, int(h * scale)))

    def frames(self) -> FrameYield:
        while True:
            if not self._open():
                log.error(
                    "Cannot open camera index %d. "
                    "On WSL2 you need usbipd-win passthrough — see docs/CAMERA_SOURCES.md.",
                    self.index,
                )
                time.sleep(5)
                continue
            last = time.monotonic()
            while True:
                ok, frame = self._cap.read()
                if not ok or frame is None:
                    log.warning("Camera read failed; reopening…")
                    break
                now = time.monotonic()
                elapsed = now - last
                if elapsed < self._frame_interval:
                    time.sleep(self._frame_interval - elapsed)
                last = time.monotonic()
                yield time.time(), self._resize(frame)

    def release(self):
        if self._cap:
            self._cap.release()
            self._cap = None


# ---------------------------------------------------------------------------
# Sample source (offline, no hardware)
# ---------------------------------------------------------------------------

class SampleSource(CameraSource):
    """
    Loop images from a folder (samples/) as a synthetic camera feed.

    Best for: first-run offline demo, CI/CD, classroom use with no camera.
    Tradeoff: static images — no real-time content.
    Config keys: samples_dir (default "samples"), target_fps, width
    """

    EXTENSIONS = ("*.jpg", "*.jpeg", "*.png", "*.bmp")

    def __init__(self, cfg: dict):
        self.samples_dir = Path(cfg.get("samples_dir", "samples"))
        self.target_fps = cfg.get("target_fps", 5)
        self.width = cfg.get("width", 640)
        self._frame_interval = 1.0 / max(self.target_fps, 1)
        self._paths: list[Path] = self._discover()

    def _discover(self) -> list[Path]:
        paths: list[Path] = []
        for ext in self.EXTENSIONS:
            paths.extend(sorted(self.samples_dir.glob(ext)))
        if not paths:
            raise FileNotFoundError(
                f"No images found in '{self.samples_dir}/'. "
                "Add some JPG/PNG files or change camera.source to 'ipcam' / 'usb'."
            )
        log.info("SampleSource: %d images in '%s' (looping).", len(paths), self.samples_dir)
        return paths

    def _resize(self, frame: Frame) -> Frame:
        h, w = frame.shape[:2]
        if w == self.width:
            return frame
        scale = self.width / w
        return cv2.resize(frame, (self.width, int(h * scale)))

    def frames(self) -> FrameYield:
        idx = 0
        while True:
            path = self._paths[idx % len(self._paths)]
            frame = cv2.imread(str(path))
            if frame is None:
                log.warning("Could not read %s; skipping.", path)
            else:
                yield time.time(), self._resize(frame)
            idx += 1
            time.sleep(self._frame_interval)

    def release(self):
        pass   # nothing to free


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_source(cfg: dict) -> CameraSource:
    """
    Create the right camera source based on cfg["source"].

    cfg is the `camera:` block from config.yaml.

    Valid values for cfg["source"]:
      "sample"      — offline image loop (default; works everywhere)
      "usb"         — USB camera
      "integrated"  — built-in laptop camera (alias for usb, index=0)
      "ipcam"       — network IP camera (MJPEG URL)
    """
    source = cfg.get("source", "sample").lower().strip()

    if source == "sample":
        return SampleSource(cfg)
    elif source in ("usb", "integrated"):
        return UsbCameraCapture(cfg)
    elif source == "ipcam":
        return IPCameraCapture(cfg)
    else:
        raise ValueError(
            f"Unknown camera source '{source}'. "
            "Valid values: sample, usb, integrated, ipcam  "
            "(set camera.source in config.yaml)"
        )


# ---------------------------------------------------------------------------
# Config helper
# ---------------------------------------------------------------------------

def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)["camera"]


# ---------------------------------------------------------------------------
# CLI test: python capture.py [--source sample|usb|ipcam]
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(description="Asset-Vision capture test")
    parser.add_argument("--source", default=None,
                        choices=["sample", "usb", "integrated", "ipcam"],
                        help="Override camera.source from config.yaml")
    parser.add_argument("--save", action="store_true",
                        help="Save one frame to data/sample.jpg and exit")
    args = parser.parse_args()

    cfg = load_config()
    if args.source:
        cfg["source"] = args.source

    src = make_source(cfg)

    if args.save:
        src.save_sample()
        sys.exit(0)

    print(f"Source: {cfg.get('source', 'sample')} — press Q to quit")
    for ts, frame in src.frames():
        cv2.imshow("Asset-Vision capture test", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    src.release()
    cv2.destroyAllWindows()
