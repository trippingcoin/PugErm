#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import Tuple

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.routes import router as api_router
from app.utils.logger import setup_logging


app = FastAPI(title="Subsidy Scoring API", version="2.0.0")
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("web/index.html")


@app.get("/app.js")
async def app_js() -> FileResponse:
    return FileResponse("web/app.js", media_type="application/javascript")


@app.get("/styles.css")
async def styles_css() -> FileResponse:
    return FileResponse("web/styles.css", media_type="text/css")


def env_or(key: str, fallback: str) -> str:
    value = os.getenv(key)
    return value if value else fallback


def parse_addr(addr: str) -> Tuple[str, int]:
    if not addr:
        return ("127.0.0.1", 8080)
    if addr.startswith(":"):
        return ("127.0.0.1", int(addr[1:]))
    if ":" in addr:
        host, port = addr.rsplit(":", 1)
        return (host, int(port))
    return ("127.0.0.1", int(addr))


def main() -> None:
    setup_logging()
    addr = env_or("ADDR", "127.0.0.1:8080")
    host, port = parse_addr(addr)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
