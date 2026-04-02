from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


STATUS_POSITIVE = {
    "исполнена",
    "одобрена",
    "approved",
    "executed",
    "success",
}

STATUS_NEGATIVE = {
    "отклонена",
    "отозвано",
    "rejected",
    "declined",
}


@dataclass
class PreparedData:
    source_df: pd.DataFrame
    enriched_df: pd.DataFrame
    feature_df: pd.DataFrame
    feature_columns: List[str]
    id_column: Optional[str]
    target_column: Optional[str]
    mode: str
    excluded_columns: List[str]
    filter_columns: Dict[str, Optional[str]]
    system_explanation: str
    target_series: Optional[pd.Series]


def _find_column(columns: List[str], hints: List[str]) -> Optional[str]:
    for col in columns:
        low = col.lower()
        if any(h in low for h in hints):
            return col
    return None


def _normalize_text_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def _build_status_flag(status: pd.Series) -> pd.Series:
    low = _normalize_text_series(status)
    out = pd.Series(np.nan, index=status.index, dtype="float64")
    out[low.isin(STATUS_POSITIVE)] = 1.0
    out[low.isin(STATUS_NEGATIVE)] = 0.0
    return out


def _infer_target(df: pd.DataFrame, target_column: Optional[str]) -> Tuple[Optional[pd.Series], Optional[str], str]:
    if target_column and target_column in df.columns:
        y = pd.to_numeric(df[target_column], errors="coerce")
        if y.notna().sum() >= 20 and y.nunique(dropna=True) > 1:
            return y, target_column, "supervised"

    status_col = _find_column(df.columns.tolist(), ["статус", "status"])
    if status_col:
        y = _build_status_flag(df[status_col])
        if y.notna().sum() >= 20 and y.nunique(dropna=True) > 1:
            return y, status_col, "proxy_status_supervised"

    amount_col = _find_column(df.columns.tolist(), ["сумм", "amount", "subsid"])
    if amount_col:
        amount = pd.to_numeric(df[amount_col], errors="coerce")
        if amount.notna().sum() >= 20:
            threshold = float(amount.quantile(0.6))
            y = (amount >= threshold).astype(float)
            return y, None, "proxy_amount_supervised"

    return None, None, "unsupervised"


def _engineer_common_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    out = df.copy()
    cols = out.columns.tolist()
    region_col = _find_column(cols, ["область", "region"])
    akimat_col = _find_column(cols, ["акимат", "akimat"])
    district_col = _find_column(cols, ["район", "district"])
    subsidy_type_col = _find_column(cols, ["наименование субсид", "subsidy", "program"])
    status_col = _find_column(cols, ["статус", "status"])
    amount_col = _find_column(cols, ["причитающая сумма", "amount", "sum"])
    normative_col = _find_column(cols, ["норматив", "normative"])
    date_col = _find_column(cols, ["дата", "date", "time"])

    if date_col:
        dt = pd.to_datetime(out[date_col], errors="coerce", dayfirst=True)
    else:
        dt = None

    if amount_col:
        amount = pd.to_numeric(out[amount_col], errors="coerce")
        out["fe_amount_log"] = np.log1p(amount.fillna(0.0))
        out["fe_amount_z"] = (amount - amount.mean()) / (amount.std() + 1e-9)
    else:
        amount = pd.Series(np.nan, index=out.index, dtype="float64")

    if normative_col:
        norm = pd.to_numeric(out[normative_col], errors="coerce")
        out["fe_normative_log"] = np.log1p(norm.fillna(0.0))
        if amount_col:
            out["fe_subsidy_efficiency"] = amount / (norm + 1e-9)
    else:
        norm = pd.Series(np.nan, index=out.index, dtype="float64")

    if status_col:
        out["fe_success_flag"] = _build_status_flag(out[status_col])

    # Synthetic farm key for historical metrics when explicit farmer ID is missing.
    key_cols: List[str] = []
    for col in [region_col, district_col, akimat_col, subsidy_type_col]:
        if col:
            key_cols.append(col)
    if key_cols:
        key_frame = out[key_cols].fillna("missing").astype(str)
        out["fe_entity_key"] = key_frame.agg("|".join, axis=1)
    else:
        out["fe_entity_key"] = out.index.astype(str)

    if "fe_success_flag" in out.columns:
        out["fe_entity_reliability"] = out.groupby("fe_entity_key")["fe_success_flag"].transform("mean")
        if region_col:
            out["fe_region_reliability"] = out.groupby(region_col)["fe_success_flag"].transform("mean")
        if subsidy_type_col:
            out["fe_program_reliability"] = out.groupby(subsidy_type_col)["fe_success_flag"].transform("mean")

    out["fe_entity_activity"] = out.groupby("fe_entity_key")["fe_entity_key"].transform("size")

    if amount_col and subsidy_type_col:
        out["fe_productivity_program_relative"] = (
            amount / (out.groupby(subsidy_type_col)[amount_col].transform("median") + 1e-9)
        )

    if dt is not None and amount_col and region_col:
        tmp = pd.DataFrame({"region": out[region_col], "date": dt, "amount": amount}).dropna(subset=["date"])
        if not tmp.empty:
            tmp["month"] = tmp["date"].dt.to_period("M").astype(str)
            monthly = tmp.groupby(["region", "month"], as_index=False)["amount"].mean()
            monthly["region_growth"] = monthly.groupby("region")["amount"].pct_change().replace([np.inf, -np.inf], np.nan)
            growth_map = monthly.groupby("region")["region_growth"].median().to_dict()
            out["fe_growth_potential"] = out[region_col].map(growth_map)

    if amount_col:
        q = amount.quantile([0.33, 0.66]).values
        low, high = float(q[0]), float(q[1])
        out["fe_farm_size_bucket"] = np.select(
            [amount < low, amount < high],
            ["small", "medium"],
            default="large",
        )
    else:
        out["fe_farm_size_bucket"] = "unknown"

    filter_columns = {
        "region": region_col,
        "subsidy_type": subsidy_type_col,
        "farm_size_bucket": "fe_farm_size_bucket",
    }
    return out, filter_columns


def prepare_features(
    df: pd.DataFrame,
    id_column: Optional[str] = None,
    target_column: Optional[str] = None,
) -> PreparedData:
    source = df.copy()
    source.columns = [str(c).strip() for c in source.columns]

    out, filter_columns = _engineer_common_features(source)

    cols = out.columns.tolist()
    inferred_id_col = id_column if id_column in cols else _find_column(cols, ["inn", "bin", "id", "фермер", "номер заявки"])
    target_series, inferred_target_col, mode = _infer_target(out, target_column)

    excluded: List[str] = []
    if inferred_id_col:
        excluded.append(f"{inferred_id_col}: id-like column")
    if inferred_target_col and inferred_target_col in out.columns:
        excluded.append(f"{inferred_target_col}: target-like column")

    raw_exclusion_tokens = ["№", "номер", "дата", "date", "time", "timestamp"]
    drop_columns = set()
    if inferred_id_col:
        drop_columns.add(inferred_id_col)
    if inferred_target_col and inferred_target_col in out.columns:
        drop_columns.add(inferred_target_col)

    for col in out.columns:
        low = col.lower()
        if any(t in low for t in raw_exclusion_tokens):
            drop_columns.add(col)
            excluded.append(f"{col}: technical column")

    # Avoid leakage if target is derived from status.
    if mode == "proxy_status_supervised":
        status_col = _find_column(cols, ["статус", "status"])
        if status_col:
            drop_columns.add(status_col)
            excluded.append(f"{status_col}: leakage prevention")
        for status_feature in [
            "fe_success_flag",
            "fe_entity_reliability",
            "fe_region_reliability",
            "fe_program_reliability",
        ]:
            if status_feature in out.columns:
                drop_columns.add(status_feature)
                excluded.append(f"{status_feature}: derived from target-like status")

    if "fe_entity_key" in out.columns:
        drop_columns.add("fe_entity_key")
        excluded.append("fe_entity_key: grouping helper only")

    feature_df = out.drop(columns=list(drop_columns), errors="ignore")
    feature_df = feature_df.dropna(axis=1, how="all")

    for col in feature_df.columns:
        if feature_df[col].dtype == object:
            feature_df[col] = feature_df[col].fillna("missing").astype(str)

    system_explanation = (
        "Model prioritizes productivity, subsidy efficiency, reliability history, and growth signals "
        "while excluding technical identifiers and timestamps."
    )

    return PreparedData(
        source_df=source.reset_index(drop=True),
        enriched_df=out.reset_index(drop=True),
        feature_df=feature_df.reset_index(drop=True),
        feature_columns=feature_df.columns.tolist(),
        id_column=inferred_id_col,
        target_column=inferred_target_col if mode == "supervised" else None,
        mode=mode,
        excluded_columns=sorted(set(excluded)),
        filter_columns=filter_columns,
        system_explanation=system_explanation,
        target_series=target_series,
    )
