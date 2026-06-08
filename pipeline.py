"""
pipeline.py — compatibility shim.

The actual implementation has moved to the asset_vision package:

    from asset_vision.pipeline import Pipeline

Install the package first (done by scripts/install.sh):

    pip install -e .
"""
from asset_vision.pipeline import Pipeline, load_config  # noqa: F401

if __name__ == "__main__":
    import runpy
    runpy.run_module("asset_vision.pipeline", run_name="__main__", alter_sys=True)
