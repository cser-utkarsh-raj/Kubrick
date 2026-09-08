from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from kubrick import __version__

ROOT = Path(__file__).resolve().parent


class handler(BaseHTTPRequestHandler):
    """Serve Kubrick's public homepage and lightweight status API."""

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]

        if path == "/api" or path.startswith("/api/"):
            payload = {
                "name": "Kubrick",
                "version": __version__,
                "status": "ok",
                "message": "Kubrick API is online.",
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/kubrick/ui/kubrick-mark.svg":
            body = (ROOT / "kubrick" / "ui" / "kubrick-mark.svg").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=86400, immutable")
            self.end_headers()
            self.wfile.write(body)
            return

        body = (ROOT / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=300, must-revalidate")
        self.end_headers()
        self.wfile.write(body)
