from __future__ import annotations

import os
import shutil
import tempfile
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.schemas import ScoreResponse
from app.services.scoring_service import FilterOptions, ScoringService
from app.utils.logger import get_logger


logger = get_logger("api")
router = APIRouter()
service = ScoringService()
DEFAULT_INPUT = "Data.xlsx"


def _save_temp_upload(file: UploadFile) -> str:
    temp_dir = tempfile.mkdtemp(prefix="pugerm-upload-")
    safe_name = (file.filename or "upload").replace("/", "_").replace("..", "_")
    path = os.path.join(temp_dir, safe_name)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return path


def _cleanup_temp(path: str) -> None:
    try:
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)
    except Exception:
        logger.exception("Failed to cleanup temp path: %s", path)


def _do_score(
    input_path: str,
    shortlist: int,
    target: Optional[str],
    id_column: Optional[str],
    region: Optional[str],
    farm_size: Optional[str],
    subsidy_type: Optional[str],
) -> ScoreResponse:
    filters = FilterOptions(region=region, farm_size=farm_size, subsidy_type=subsidy_type)
    try:
        return service.run_scoring(
            input_path=input_path,
            shortlist_n=shortlist,
            target_column=target,
            id_column=id_column,
            filters=filters,
        )
    except Exception as exc:
        logger.exception("Scoring failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "subsidy-scoring-api"}


@router.post("/score", response_model=ScoreResponse)
@router.post("/api/score", response_model=ScoreResponse)
async def score(
    shortlist: int = Query(20, ge=1, le=1000),
    target: Optional[str] = Query(None),
    id: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    farm_size: Optional[str] = Query(None),
    subsidy_type: Optional[str] = Query(None),
    file: Optional[UploadFile] = File(None),
) -> ScoreResponse:
    input_path = DEFAULT_INPUT
    temp_path: Optional[str] = None

    if file is not None:
        temp_path = _save_temp_upload(file)
        input_path = temp_path

    if not os.path.exists(input_path):
        if temp_path:
            _cleanup_temp(temp_path)
        raise HTTPException(status_code=400, detail=f"Input file not found: {input_path}")

    try:
        return _do_score(
            input_path=input_path,
            shortlist=shortlist,
            target=target,
            id_column=id,
            region=region,
            farm_size=farm_size,
            subsidy_type=subsidy_type,
        )
    finally:
        if temp_path:
            _cleanup_temp(temp_path)


@router.get("/top")
@router.get("/api/top")
def top(
    n: int = Query(20, ge=1, le=1000),
    region: Optional[str] = Query(None),
    farm_size: Optional[str] = Query(None),
    subsidy_type: Optional[str] = Query(None),
) -> dict:
    response = service.get_last_response()
    if response is None:
        raise HTTPException(status_code=400, detail="No scoring run found. Call POST /score first.")

    shortlist = response.records
    if region:
        shortlist = [r for r in shortlist if str(r.attributes.get("Область", "")).lower() == region.lower()]
    if subsidy_type:
        shortlist = [
            r
            for r in shortlist
            if str(r.attributes.get("Наименование субсидирования", "")).lower() == subsidy_type.lower()
        ]
    if farm_size:
        shortlist = [r for r in shortlist if str(r.attributes.get("fe_farm_size_bucket", "")).lower() == farm_size.lower()]

    return {"count": min(n, len(shortlist)), "records": shortlist[:n]}


@router.get("/feature-importance")
@router.get("/api/feature-importance")
def feature_importance() -> dict:
    response = service.get_last_response()
    if response is None:
        raise HTTPException(status_code=400, detail="No scoring run found. Call POST /score first.")
    return {"model": response.meta.selected_model, "features": response.feature_importance}

