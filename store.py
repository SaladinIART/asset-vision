"""
store.py — compatibility shim.

The actual implementation has moved to the asset_vision package:

    from asset_vision.store import AssetStore

Install the package first (done by scripts/install.sh):

    pip install -e .
"""
from asset_vision.store import (  # noqa: F401
    Asset,
    DetectionRecord,
    AssetStore,
    load_config,
)
