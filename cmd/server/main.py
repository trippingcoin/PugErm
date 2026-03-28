#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

DEFAULT_INPUT = "Data.xlsx"

app = FastAPI()
app.mount("/", StaticFiles(directory="web", html=True), name="static")


def env_or(key: str, fallback: str) -> str:
    value = os.getenv(key)
    return value if value else fallback


def parse_addr(addr: str) -> Tuple[str, int]:
    if not addr:
        return ("", 8080)
    if addr.startswith(":"):
        return ("", int(addr[1:]))
    if ":" in addr:
        host, port = addr.rsplit(":", 1)
        return (host, int(port))
    return ("", int(addr))


def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = name.replace(os.sep, "_")
    name = name.replace("..", "_")
    return name


def error_payload(message: str, detail: Optional[str]) -> dict:
    payload = {"error": message}
    if detail:
        payload["detail"] = detail
    return payload


@app.post("/api/score")
async def score(
    target: Optional[str] = Query(None),
    id: Optional[str] = Query(None),
    shortlist: Optional[str] = Query(None),
    file: Optional[UploadFile] = File(None),
):
    python_bin = env_or("PYTHON_BIN", "python3")
    ml_script = env_or("ML_SCRIPT", "ml/score.py")

    input_path = DEFAULT_INPUT
    temp_dir = None

    if file is not None:
        temp_dir = tempfile.mkdtemp(prefix="pugerm-upload-")
        filename = sanitize_filename(file.filename or "") or "upload.xlsx"
        input_path = os.path.join(temp_dir, filename)
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

    if not os.path.exists(input_path):
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse(
            status_code=400,
            content=error_payload("input file not found", f"{input_path} does not exist"),
        )

    args = [ml_script, "--input", input_path]
    if target:
        args += ["--target", target.strip()]
    if id:
        args += ["--id-column", id.strip()]
    if shortlist:
        args += ["--shortlist", shortlist.strip()]

    try:
        result = subprocess.run(
            [python_bin, *args],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse(status_code=504, content=error_payload("ml scoring timeout", None))
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

    if result.returncode != 0:
        return JSONResponse(
            status_code=500,
            content=error_payload("ml scoring failed", result.stderr.strip() or None),
        )

    try:
        json.loads(result.stdout)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content=error_payload("ml output is not valid json", result.stderr.strip() or None),
        )

    return Response(content=result.stdout, media_type="application/json")


def main() -> None:
    addr = env_or("ADDR", ":8080")
    host, port = parse_addr(addr)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
