from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler

from kubrick import __version__


class handler(BaseHTTPRequestHandler):
    """Minimal Vercel-compatible health endpoint for Kubrick."""

    def do_GET(self) -> None:  # noqa: N802
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

    def do_HEAD(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
