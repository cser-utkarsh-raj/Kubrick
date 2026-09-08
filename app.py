from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from kubrick import __version__

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Kubrick", docs_url=None, redoc_url=None)


@app.get("/", include_in_schema=False)
def homepage() -> FileResponse:
    return FileResponse(ROOT / "index.html", media_type="text/html")


@app.get("/api", include_in_schema=False)
def api_status() -> JSONResponse:
    return JSONResponse(
        {
            "name": "Kubrick",
            "version": __version__,
            "status": "ok",
            "message": "Kubrick API is online.",
        },
        headers={"Cache-Control": "no-store"},
    )


@app.get("/kubrick/ui/kubrick-mark.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(ROOT / "kubrick" / "ui" / "kubrick-mark.svg", media_type="image/svg+xml")
