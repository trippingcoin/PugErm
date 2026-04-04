from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class RuleFlag:
    code: str
    severity: str
    message: str
    passed: bool


@dataclass
class RuleSpec:
    policy_id: str
    category: str
    severity: str
    source: str
    message: str


@dataclass
class RuleEvaluation:
    flags: List[RuleFlag]
    policy_checks: List[Dict[str, object]]
    eligibility_passed: bool
    eligibility_score: float
    compliance_score: float
    fraud_risk_score: float


RULE_SPECS: Dict[str, RuleSpec] = {
    "AMOUNT_POSITIVE": RuleSpec(
        policy_id="P-001",
        category="financial",
        severity="high",
        source="Rules Ch.3/Ch.4",
        message="Причитающая сумма должна быть положительной.",
    ),
    "NORMATIVE_POSITIVE": RuleSpec(
        policy_id="P-002",
        category="financial",
        severity="high",
        source="Rules Appendix 1",
        message="Норматив должен быть положительным.",
    ),
    "DISTRICT_PRESENT": RuleSpec(
        policy_id="P-003",
        category="application",
        severity="medium",
        source="Rules Appendix 3 Form fields",
        message="В заявке должен быть указан район хозяйства.",
    ),
    "DIRECTION_PROGRAM_CONSISTENCY": RuleSpec(
        policy_id="P-004",
        category="semantic",
        severity="medium",
        source="Rules Appendix 2 criteria alignment",
        message="Направление субсидирования должно соответствовать типу программы.",
    ),
    "APPLICATION_WINDOW_20JAN_20DEC": RuleSpec(
        policy_id="P-005",
        category="timeline",
        severity="medium",
        source="Rules Appendix 2 submission windows",
        message="Дата подачи должна попадать в окно приема заявок.",
    ),
    "STATUS_RISK": RuleSpec(
        policy_id="P-006",
        category="status",
        severity="high",
        source="Rules Appendix 4 p.9 refusal grounds",
        message="Отклоненные/отозванные заявки не рекомендуются автоматически.",
    ),
    "AMOUNT_NORMATIVE_RATIO": RuleSpec(
        policy_id="P-007",
        category="fraud",
        severity="medium",
        source="Risk control policy",
        message="Соотношение суммы к нормативу вне допустимого диапазона.",
    ),
    "NO_REPEAT_SUBSIDY_SIGNAL": RuleSpec(
        policy_id="P-008",
        category="anti_repeat",
        severity="medium",
        source="Rules non-subsidized cases",
        message="Потенциальный сигнал повторного субсидирования.",
    ),
}


def _to_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _lower(value) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _parse_dt(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def evaluate_record_rules(attributes: Dict[str, object]) -> RuleEvaluation:
    flags: List[RuleFlag] = []

    status = _lower(attributes.get("Статус заявки"))
    direction = _lower(attributes.get("Направление водства"))
    program = _lower(attributes.get("Наименование субсидирования"))
    district = _lower(attributes.get("Район хозяйства"))
    submitted_at = _parse_dt(attributes.get("Дата поступления"))

    amount = _to_float(attributes.get("Причитающая сумма"))
    normative = _to_float(attributes.get("Норматив"))

    amount_ok = amount is not None and amount > 0
    flags.append(
        RuleFlag(
            code="AMOUNT_POSITIVE",
            severity="high" if not amount_ok else "info",
            message="Причитающая сумма должна быть положительной.",
            passed=amount_ok,
        )
    )

    norm_ok = normative is not None and normative > 0
    flags.append(
        RuleFlag(
            code="NORMATIVE_POSITIVE",
            severity="high" if not norm_ok else "info",
            message="Норматив должен быть положительным.",
            passed=norm_ok,
        )
    )

    district_ok = bool(district)
    flags.append(
        RuleFlag(
            code="DISTRICT_PRESENT",
            severity="medium" if not district_ok else "info",
            message="Нужно указать район хозяйства.",
            passed=district_ok,
        )
    )

    relation = {
        "скотовод": ["крупного рогатого", "молока", "быков", "коров", "скота"],
        "птицевод": ["птиц", "кур", "яиц", "инкубац"],
        "овцевод": ["овец", "овцев", "баран"],
        "коневод": ["лошад", "кон"],
        "верблюдовод": ["верблюд"],
        "пчеловод": ["мед", "пчел"],
        "свиновод": ["свин"],
        "козовод": ["коз"],
    }
    consistency = True
    if direction and program:
        matched = False
        for key, keywords in relation.items():
            if key in direction:
                matched = True
                if not any(k in program for k in keywords):
                    consistency = False
                break
        if not matched:
            consistency = True
    flags.append(
        RuleFlag(
            code="DIRECTION_PROGRAM_CONSISTENCY",
            severity="medium" if not consistency else "info",
            message="Направление субсидирования должно соответствовать типу программы.",
            passed=consistency,
        )
    )

    in_window = True
    if submitted_at is not None:
        start = datetime(submitted_at.year, 1, 20)
        end = datetime(submitted_at.year, 12, 20, 23, 59, 59)
        in_window = start <= submitted_at <= end
    flags.append(
        RuleFlag(
            code="APPLICATION_WINDOW_20JAN_20DEC",
            severity="medium" if not in_window else "info",
            message="Дата подачи должна попадать в окно приема заявок по критериям Правил.",
            passed=in_window,
        )
    )

    bad_status = any(s in status for s in ["отклон", "отозван", "refused", "rejected"])
    flags.append(
        RuleFlag(
            code="STATUS_RISK",
            severity="high" if bad_status else "info",
            message="Статус заявки указывает на повышенный риск отказа/отзыва.",
            passed=not bad_status,
        )
    )

    ratio_ok = True
    if amount is not None and normative is not None and normative > 0:
        ratio = amount / normative
        ratio_ok = 0.1 <= ratio <= 20000
    flags.append(
        RuleFlag(
            code="AMOUNT_NORMATIVE_RATIO",
            severity="medium" if not ratio_ok else "info",
            message="Соотношение суммы к нормативу вне ожидаемого диапазона.",
            passed=ratio_ok,
        )
    )

    duplicate_hint = "повтор" in program or "ранее просубсид" in program
    flags.append(
        RuleFlag(
            code="NO_REPEAT_SUBSIDY_SIGNAL",
            severity="medium" if duplicate_hint else "info",
            message="Выявлен потенциальный сигнал повторного субсидирования (требуется ручная проверка реестра).",
            passed=not duplicate_hint,
        )
    )

    hard_fail_codes = {
        "AMOUNT_POSITIVE",
        "NORMATIVE_POSITIVE",
        "DISTRICT_PRESENT",
        "STATUS_RISK",
    }
    medium_fail_codes = {
        "DIRECTION_PROGRAM_CONSISTENCY",
        "APPLICATION_WINDOW_20JAN_20DEC",
        "AMOUNT_NORMATIVE_RATIO",
        "NO_REPEAT_SUBSIDY_SIGNAL",
    }

    hard_failed = [f for f in flags if f.code in hard_fail_codes and not f.passed]
    medium_failed = [f for f in flags if f.code in medium_fail_codes and not f.passed]

    eligibility_passed = len(hard_failed) == 0
    eligibility_score = 100.0 if eligibility_passed else max(0.0, 100.0 - 30.0 * len(hard_failed))
    compliance_score = max(0.0, 100.0 - 20.0 * len(medium_failed))
    fraud_risk_score = min(100.0, 10.0 * len(medium_failed) + 35.0 * len(hard_failed))

    policy_checks: List[Dict[str, object]] = []
    for flag in flags:
        spec = RULE_SPECS.get(flag.code)
        if spec is None:
            continue
        policy_checks.append(
            {
                "policy_id": spec.policy_id,
                "category": spec.category,
                "severity": flag.severity,
                "passed": flag.passed,
                "message": flag.message,
                "source": spec.source,
            }
        )

    return RuleEvaluation(
        flags=flags,
        policy_checks=policy_checks,
        eligibility_passed=eligibility_passed,
        eligibility_score=eligibility_score,
        compliance_score=compliance_score,
        fraud_risk_score=fraud_risk_score,
    )
