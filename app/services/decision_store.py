from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

from app.schemas import AuditEntry, CommissionDecision


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DecisionInput:
    application_id: str
    decision: str
    reason_code: str
    decided_by: str
    comment: Optional[str] = None


class DecisionStore:
    def __init__(self, storage_path: str = ".runtime/decisions_store.json") -> None:
        self._lock = Lock()
        self._decisions: Dict[str, CommissionDecision] = {}
        self._audit: Dict[str, List[AuditEntry]] = {}
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return
        decisions = raw.get("decisions", {})
        audit = raw.get("audit", {})
        for key, value in decisions.items():
            try:
                self._decisions[key] = CommissionDecision(**value)
            except Exception:
                continue
        for key, entries in audit.items():
            parsed: List[AuditEntry] = []
            for entry in entries:
                try:
                    parsed.append(AuditEntry(**entry))
                except Exception:
                    continue
            self._audit[key] = parsed

    def _flush(self) -> None:
        payload = {
            "decisions": {k: v.model_dump() for k, v in self._decisions.items()},
            "audit": {k: [e.model_dump() for e in v] for k, v in self._audit.items()},
        }
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_decision(self, payload: DecisionInput) -> CommissionDecision:
        record = CommissionDecision(
            application_id=payload.application_id,
            decision=payload.decision,
            reason_code=payload.reason_code,
            comment=payload.comment,
            decided_by=payload.decided_by,
            decided_at=_now_iso(),
        )
        with self._lock:
            self._decisions[payload.application_id] = record
            self._audit.setdefault(payload.application_id, []).append(
                AuditEntry(
                    application_id=payload.application_id,
                    action="commission_decision_saved",
                    actor=payload.decided_by,
                    at=_now_iso(),
                    payload=record.model_dump(),
                )
            )
            self._flush()
        return record

    def get_decision(self, application_id: str) -> Optional[CommissionDecision]:
        with self._lock:
            return self._decisions.get(application_id)

    def get_audit(self, application_id: str) -> List[AuditEntry]:
        with self._lock:
            return list(self._audit.get(application_id, []))
