"""Kubrick desktop UI package."""


def main() -> int:
    """Launch the desktop editor without eagerly importing the app module."""
    from .app import main as app_main

    return app_main()


__all__ = ["main"]
