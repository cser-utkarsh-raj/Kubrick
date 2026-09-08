from __future__ import annotations

from kubrick import __version__


def handler(request):
    return {
        "name": "Kubrick",
        "version": __version__,
        "status": "ok",
        "message": "Kubrick API is online.",
    }
