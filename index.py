from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from kubrick import __version__

ROOT = Path(__file__).resolve().parent


class handler(BaseHTTPRequestHandler):
    """Serve Kubrick's public homepage and lightweight status API."""

    def _send_file(self, path: Path, content_type: str, cache_control: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.end_headers()
        self.wfile.write(body)

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

        static_files = {
            "/kubrick/ui/kubrick-mark.svg": ("kubrick-mark.svg", "image/svg+xml"),
            "/kubrick/ui/dot.svg": ("dot.svg", "image/svg+xml"),
        }
        if path in static_files:
            filename, content_type = static_files[path]
            self._send_file(
                ROOT / "kubrick" / "ui" / filename,
                content_type,
                "public, max-age=86400, immutable",
            )
            return

        self._send_file(
            ROOT / "index.html",
            "text/html; charset=utf-8",
            "public, max-age=300, must-revalidate",
        )
