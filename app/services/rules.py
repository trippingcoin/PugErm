from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Dict, List

from app.services.regulatory_data import (
    NATURAL_LOSS_MAX_PCT,
    PASTURE_MIN_RESTORED_HA,
    SPECIES_PATTERNS,
    SUBSIDY_PROGRAM_COMPACTS,
)


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
        source="V1900018404 Appendix 1",
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
        source="V1900018404 Appendix 2",
        message="Дата подачи должна попадать в окно приема заявок.",
    ),
    "STATUS_RISK": RuleSpec(
        policy_id="P-006",
        category="status",
        severity="high",
        source="V1900018404 Appendix 4",
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
    "NATURAL_LOSS_WITHIN_NORMS": RuleSpec(
        policy_id="P-009",
        category="animal_welfare",
        severity="medium",
        source="V1500012488",
        message="Естественная убыль (падеж) не должна превышать нормативы по видам животных.",
    ),
    "PASTURE_LOAD_MIN_AREA": RuleSpec(
        policy_id="P-010",
        category="land",
        severity="medium",
        source="V1500011064",
        message="Нагрузка на пастбища должна соответствовать минимальным нормативам площади.",
    ),
    "SUBSIDY_PROGRAM_LISTED": RuleSpec(
        policy_id="P-011",
        category="program",
        severity="medium",
        source="V1900018404 Appendix 1",
        message="Наименование субсидирования должно соответствовать перечню Приложения 1.",
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


def _normalize_program_text(value: object) -> str:
    text = str(value or "").lower()
    text = text.replace("ё", "е")
    text = re.sub(r"[\\W_]+", " ", text)
    return re.sub(r"\\s+", " ", text).strip()


def _compact_text(value: object) -> str:
    text = str(value or "").lower().replace("ё", "е")
    return re.sub(r"[^0-9a-zа-я]+", "", text)


def _detect_species(*values: object) -> str | None:
    haystack = " ".join(_normalize_program_text(v) for v in values if v)
    for species, tokens in SPECIES_PATTERNS.items():
        if any(token in haystack for token in tokens):
            return species
    return None


def _find_numeric_attr(attributes: Dict[str, object], keys: List[str]) -> float | None:
    for key, value in attributes.items():
        norm_key = _normalize_program_text(key)
        if any(k in norm_key for k in keys):
            val = _to_float(value)
            if val is not None:
                return val
    return None


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

    program_listed = True
    if program:
        compact = _compact_text(program)
        if len(compact) >= 8:
            program_listed = any(
                compact in known or known in compact for known in SUBSIDY_PROGRAM_COMPACTS
            )
    flags.append(
        RuleFlag(
            code="SUBSIDY_PROGRAM_LISTED",
            severity="medium" if not program_listed else "info",
            message="Наименование субсидирования должно соответствовать перечню Приложения 1.",
            passed=program_listed,
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

    species = _detect_species(
        direction,
        program,
        attributes.get("Вид животного"),
        attributes.get("Порода"),
        attributes.get("Категория животных"),
    )
    mortality = _find_numeric_attr(
        attributes,
        ["падеж", "естественн", "убыль", "mortality", "loss"],
    )
    if mortality is not None and species in NATURAL_LOSS_MAX_PCT:
        if mortality <= 1:
            mortality *= 100
        max_pct = NATURAL_LOSS_MAX_PCT[species]
        ok = mortality <= max_pct
        flags.append(
            RuleFlag(
                code="NATURAL_LOSS_WITHIN_NORMS",
                severity="medium" if not ok else "info",
                message=f"Естественная убыль {mortality:.2f}% при нормативе до {max_pct:.2f}%.",
                passed=ok,
            )
        )

    pasture_area = _find_numeric_attr(attributes, ["площадь пастби", "пастбищ", "pasture area", "pasture"])
    headcount = _find_numeric_attr(attributes, ["поголов", "голов", "headcount", "livestock", "числен"])
    if (
        pasture_area is not None
        and headcount is not None
        and headcount > 0
        and species in PASTURE_MIN_RESTORED_HA
    ):
        area_per_head = pasture_area / headcount
        min_required = PASTURE_MIN_RESTORED_HA[species]
        ok = area_per_head >= min_required
        flags.append(
            RuleFlag(
                code="PASTURE_LOAD_MIN_AREA",
                severity="medium" if not ok else "info",
                message=(
                    f"Площадь пастбищ на 1 голову: {area_per_head:.2f} га "
                    f"(минимум {min_required:.2f} га на восстановленных угодьях)."
                ),
                passed=ok,
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
        "NATURAL_LOSS_WITHIN_NORMS",
        "PASTURE_LOAD_MIN_AREA",
        "SUBSIDY_PROGRAM_LISTED",
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
