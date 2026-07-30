"""Process entry point."""
from __future__ import annotations

from eka.api.app import create_app
from eka.config import get_settings

app = create_app(get_settings())


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "eka.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not settings.is_production,
        log_config=None,
    )


if __name__ == "__main__":
    run()
