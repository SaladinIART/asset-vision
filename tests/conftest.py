"""
Shared pytest fixtures for asset-vision tests.

Fixtures
--------
tmp_db  — path string to a fresh, per-test SQLite database
store   — AssetStore backed by tmp_db (auto-cleaned after test)
"""
import pytest
from asset_vision.store import AssetStore


@pytest.fixture
def tmp_db(tmp_path):
    """Return path to a per-test SQLite DB (deleted when test ends)."""
    return str(tmp_path / "test_assets.db")


@pytest.fixture
def store(tmp_db):
    """Fresh AssetStore for each test."""
    return AssetStore(tmp_db)
