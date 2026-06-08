"""
detector.py — compatibility shim.

The actual implementation has moved to the asset_vision package:

    from asset_vision.detector import YOLODetector, Detection

Install the package first (done by scripts/install.sh):

    pip install -e .
"""
from asset_vision.detector import (  # noqa: F401
    Detection,
    YOLODetector,
    load_config,
)

if __name__ == "__main__":
    import runpy
    runpy.run_module("asset_vision.detector", run_name="__main__", alter_sys=True)
