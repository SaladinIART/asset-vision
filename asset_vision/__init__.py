"""
asset_vision — core perception and data modules for the Asset-Vision system.

Importable after `pip install -e .` from the repo root:

    from asset_vision.capture  import make_source, IPCameraCapture
    from asset_vision.detector import YOLODetector, Detection
    from asset_vision.qrtools  import decode_qr, make_asset_label
    from asset_vision.store    import AssetStore
    from asset_vision.pipeline import Pipeline
"""

__version__ = "0.2.0"
__author__ = "SaladinIART (Salbotics)"
__license__ = "MIT"
