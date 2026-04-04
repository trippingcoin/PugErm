from __future__ import annotations

import os
import shutil
import tempfile
from importlib.metadata import PackageNotFoundError, version
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.schemas import CommissionDecisionRequest, ScoreResponse
from app.models.trainer import get_ml_backend_status
from app.services.decision_store import DecisionInput, DecisionStore
from app.services.reporting import build_applicant_report_pdf
from app.services.scoring_service import FilterOptions, ScoringService
from app.utils.logger import get_logger


logger = get_logger("api")
router = APIRouter()
service = ScoringService()
decision_store = DecisionStore()
DEFAULT_INPUT = "Data.xlsx"


def _pkg_version(name: str) -> Optional[str]:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


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


@router.get("/api/diagnostics")
def diagnostics() -> dict:
    backends = get_ml_backend_status()
    available = [name for name, info in backends.items() if info.get("available")]
    missing = [name for name, info in backends.items() if not info.get("available")]
    notes = []
    if "lightgbm" in missing:
        notes.append("LightGBM unavailable. On macOS install libomp: `brew install libomp`.")
    return {
        "service": "subsidy-scoring-api",
        "input_data": {
            "default_input": DEFAULT_INPUT,
            "exists": os.path.exists(DEFAULT_INPUT),
        },
        "ml_backends": backends,
        "stacking_ready": len(available) >= 2,
        "available_backends": available,
        "missing_backends": missing,
        "runtime": {
            "fastapi": _pkg_version("fastapi"),
            "numpy": _pkg_version("numpy"),
            "scikit-learn": _pkg_version("scikit-learn"),
            "xgboost": _pkg_version("xgboost"),
            "lightgbm": _pkg_version("lightgbm"),
            "catboost": _pkg_version("catboost"),
            "shap": _pkg_version("shap"),
        },
        "notes": notes,
    }


@router.post("/api/score", response_model=ScoreResponse)
async def score(
    shortlist: int = Query(20, ge=1, le=1000),
    target: Optional[str] = Query(None),
    id: Optional[str] = Query(None),
    compact: bool = Query(False, description="Return lightweight response without full records payload"),
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
        response = _do_score(
            input_path=input_path,
            shortlist=shortlist,
            target=target,
            id_column=id,
            region=region,
            farm_size=farm_size,
            subsidy_type=subsidy_type,
        )
        if compact:
            return response.model_copy(update={"records": []})
        return response
    finally:
        if temp_path:
            _cleanup_temp(temp_path)


@router.get("/api/score/last", response_model=ScoreResponse)
def score_last(
    compact: bool = Query(True, description="Return lightweight response without full records payload"),
) -> ScoreResponse:
    response = service.get_last_response()
    if response is None:
        raise HTTPException(status_code=404, detail="No scoring state found.")
    if compact:
        return response.model_copy(update={"records": []})
    return response


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
    region = region if isinstance(region, str) else None
    farm_size = farm_size if isinstance(farm_size, str) else None
    subsidy_type = subsidy_type if isinstance(subsidy_type, str) else None

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


@router.get("/api/records")
def records(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    region: Optional[str] = Query(None),
    farm_size: Optional[str] = Query(None),
    subsidy_type: Optional[str] = Query(None),
) -> dict:
    response = service.get_last_response()
    if response is None:
        raise HTTPException(status_code=400, detail="No scoring run found. Call POST /score first.")

    items = response.records
    region = region if isinstance(region, str) else None
    farm_size = farm_size if isinstance(farm_size, str) else None
    subsidy_type = subsidy_type if isinstance(subsidy_type, str) else None

    if region:
        items = [r for r in items if str(r.attributes.get("Область", "")).lower() == region.lower()]
    if subsidy_type:
        items = [
            r
            for r in items
            if str(r.attributes.get("Наименование субсидирования", "")).lower() == subsidy_type.lower()
        ]
    if farm_size:
        items = [r for r in items if str(r.attributes.get("fe_farm_size_bucket", "")).lower() == farm_size.lower()]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "records": items[start:end],
    }


@router.get("/api/feature-importance")
def feature_importance() -> dict:
    response = service.get_last_response()
    if response is None:
        raise HTTPException(status_code=400, detail="No scoring run found. Call POST /score first.")
    return {"model": response.meta.selected_model, "features": response.feature_importance}


@router.post("/api/decisions")
def save_decision(payload: CommissionDecisionRequest) -> dict:
    decision = decision_store.save_decision(
        DecisionInput(
            application_id=payload.application_id,
            decision=payload.decision,
            reason_code=payload.reason_code,
            comment=payload.comment,
            decided_by=payload.decided_by,
        )
    )
    return {"decision": decision}


@router.get("/api/decisions/{application_id}")
def get_decision(application_id: str) -> dict:
    decision = decision_store.get_decision(application_id)
    return {"decision": decision}


@router.get("/api/audit/{application_id}")
def get_audit(application_id: str) -> dict:
    return {"application_id": application_id, "entries": decision_store.get_audit(application_id)}


@router.get("/api/reports/{application_id}.pdf")
def report_pdf(
    application_id: str,
    lang: str = Query("ru"),
) -> Response:
    record = service.get_record_by_id(application_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found. Run /score first and verify application ID.")
    pdf = build_applicant_report_pdf(record=record, lang=lang)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="applicant_{application_id}.pdf"'},
    )


@router.get("/api/scenario/simulate")
def simulate_scenario(
    top_n: int = Query(50, ge=1, le=5000),
    avg_subsidy_per_farm: float = Query(5_000_000.0, gt=0),
) -> dict:
    response = service.get_last_response()
    if response is None:
        raise HTTPException(status_code=400, detail="No scoring run found. Call POST /score first.")

    selected = sorted(response.records, key=lambda x: x.score, reverse=True)[:top_n]
    if not selected:
        return {
            "selected_farms": 0,
            "estimated_budget": 0.0,
            "expected_output_gain_pct": 0.0,
            "expected_risk_adjusted_gain_pct": 0.0,
        }

    gains = []
    risk_adjusted = []
    for rec in selected:
        base_gain = 4.0 + rec.score * 0.16
        risk_discount = {"low": 1.0, "medium": 0.82, "high": 0.6}.get(rec.risk_level, 0.8)
        gains.append(base_gain)
        risk_adjusted.append(base_gain * risk_discount)

    return {
        "selected_farms": len(selected),
        "estimated_budget": round(len(selected) * avg_subsidy_per_farm, 2),
        "expected_output_gain_pct": round(float(sum(gains) / len(gains)), 2),
        "expected_risk_adjusted_gain_pct": round(float(sum(risk_adjusted) / len(risk_adjusted)), 2),
    }
