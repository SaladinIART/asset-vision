"""
qrtools.py — compatibility shim.

The actual implementation has moved to the asset_vision package:

    from asset_vision.qrtools import decode_qr, make_asset_label

Install the package first (done by scripts/install.sh):

    pip install -e .
"""
from asset_vision.qrtools import (  # noqa: F401
    DecodedQR,
    make_qr_image,
    make_asset_label,
    make_label_sheet,
    decode_qr,
    annotate_qr,
    associate_qr_to_detections,
    load_config,
)
