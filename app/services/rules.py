from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RuleFlag:
    code: str
    severity: str
    message: str
    passed: bool


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


def evaluate_compliance(attributes: Dict[str, object]) -> List[RuleFlag]:
    flags: List[RuleFlag] = []

    status = _lower(attributes.get("Статус заявки"))
    direction = _lower(attributes.get("Направление водства"))
    program = _lower(attributes.get("Наименование субсидирования"))
    district = _lower(attributes.get("Район хозяйства"))

    amount = _to_float(attributes.get("Причитающая сумма"))
    normative = _to_float(attributes.get("Норматив"))

    # Rule 1: basic amount validity
    amount_ok = amount is not None and amount > 0
    flags.append(
        RuleFlag(
            code="AMOUNT_POSITIVE",
            severity="high" if not amount_ok else "info",
            message="Причитающая сумма должна быть положительной.",
            passed=amount_ok,
        )
    )

    # Rule 2: normative validity
    norm_ok = normative is not None and normative > 0
    flags.append(
        RuleFlag(
            code="NORMATIVE_POSITIVE",
            severity="high" if not norm_ok else "info",
            message="Норматив должен быть положительным.",
            passed=norm_ok,
        )
    )

    # Rule 3: district should be present
    district_ok = bool(district)
    flags.append(
        RuleFlag(
            code="DISTRICT_PRESENT",
            severity="medium" if not district_ok else "info",
            message="Нужно указать район хозяйства.",
            passed=district_ok,
        )
    )

    # Rule 4: direction/program semantic consistency (heuristic)
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

    # Rule 5: rejection-like statuses are high risk for approval
    bad_status = any(s in status for s in ["отклон", "отозван", "refused", "rejected"])
    flags.append(
        RuleFlag(
            code="STATUS_RISK",
            severity="high" if bad_status else "info",
            message="Статус заявки указывает на повышенный риск отказа/отзыва.",
            passed=not bad_status,
        )
    )

    # Rule 6: outlier ratio for amount/normative
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

    return flags

