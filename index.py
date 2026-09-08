from __future__ import annotations

from pathlib import Path

from kubrick import __version__

ROOT = Path(__file__).resolve().parent


class handler:
    """Serve Kubrick's public homepage without a web framework dependency."""

    def GET(self, request):
        body = (ROOT / "index.html").read_bytes()
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "public, max-age=300, must-revalidate",
            },
            "body": body.decode("utf-8"),
        }
