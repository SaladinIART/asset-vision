"""
capture.py — compatibility shim.

The actual implementation has moved to the asset_vision package:

    from asset_vision.capture import make_source, IPCameraCapture

Install the package first (done by scripts/install.sh):

    pip install -e .

Then this shim re-exports everything so existing scripts still work:

    python capture.py --source sample
"""
from asset_vision.capture import (  # noqa: F401
    CameraSource,
    IPCameraCapture,
    UsbCameraCapture,
    SampleSource,
    make_source,
    load_config,
    Frame,
    FrameYield,
)

if __name__ == "__main__":
    from asset_vision.capture import __doc__ as _doc
    import runpy
    runpy.run_module("asset_vision.capture", run_name="__main__", alter_sys=True)
