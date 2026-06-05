"""
FastAPI web dashboard — live annotated feed + inventory roster + asset registration.
Reads the same SQLite DB as the pipeline; pipeline runs in a background thread.
"""
import asyncio
import io
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import Pipeline
from qrtools import make_asset_label, make_label_sheet
from store import AssetStore

log = logging.getLogger(__name__)


def _ts_filter(unix: float) -> str:
    """Jinja2 filter: unix timestamp -> human time string."""
    import datetime
    return datetime.datetime.fromtimestamp(unix).strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
with open(CONFIG_PATH) as f:
    _cfg = yaml.safe_load(f)

WEB_CFG = _cfg["web"]
STORE_CFG = _cfg["storage"]

pipeline = Pipeline(str(CONFIG_PATH))
store = pipeline.store

app = FastAPI(title="Asset-Vision")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.filters["ts"] = _ts_filter


@app.on_event("startup")
async def _startup():
    pipeline.start()
    log.info("Pipeline started.")


@app.on_event("shutdown")
async def _shutdown():
    pipeline.stop()


# ---------------------------------------------------------------------------
# MJPEG stream
# ---------------------------------------------------------------------------

async def _frame_generator():
    """Yield annotated frames as multipart MJPEG."""
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(blank, "Waiting for camera...", (120, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180, 180, 180), 2)

    while True:
        frame = pipeline.get_frame(timeout=0.2)
        if frame is None:
            frame = blank
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
        )
        await asyncio.sleep(1 / WEB_CFG.get("stream_fps", 10))


@app.get("/stream")
async def stream():
    return StreamingResponse(
        _frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    roster = store.roster()
    stats = store.stats()
    recent = store.recent_detections(12)
    pipe_stats = pipeline.stats()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"roster": roster, "stats": stats, "recent": recent, "pipe_stats": pipe_stats},
    )


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={})


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/roster")
async def api_roster():
    return [
        {
            "asset_id": a.asset_id,
            "name": a.name,
            "category": a.category,
            "status": a.status,
            "last_seen": a.last_seen,
        }
        for a in store.roster()
    ]


@app.get("/api/stats")
async def api_stats():
    s = store.stats()
    s.update(pipeline.stats())
    return s


@app.post("/api/assets")
async def create_asset(
    asset_id: str = Form(...),
    name: str = Form(""),
    category: str = Form(""),
    notes: str = Form(""),
):
    prefix = _cfg["qr"].get("prefix", "AV-")
    qr_payload = f"{prefix}{asset_id}" if not asset_id.startswith(prefix) else asset_id
    store.add_asset(
        asset_id=qr_payload,
        name=name,
        category=category,
        notes=notes,
        qr_payload=qr_payload,
    )
    return JSONResponse({"ok": True, "asset_id": qr_payload})


@app.delete("/api/assets/{asset_id}")
async def delete_asset(asset_id: str):
    store.delete_asset(asset_id)
    return {"ok": True}


@app.get("/api/assets/{asset_id}/qr.png")
async def download_qr(asset_id: str):
    asset = store.get_asset(asset_id)
    if not asset:
        return Response(status_code=404)
    img = make_asset_label(asset.asset_id, asset.name)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{asset_id}.png"'},
    )


@app.get("/api/sheet.png")
async def download_sheet():
    assets = [(a.asset_id, a.name) for a in store.roster()]
    if not assets:
        return Response(status_code=404)
    out = "/tmp/asset_sheet.png"
    make_label_sheet(assets, out)
    return Response(
        content=Path(out).read_bytes(),
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="asset_sheet.png"'},
    )
