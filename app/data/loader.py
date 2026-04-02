from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd


HEADER_HINTS = {
    "ru": [
        "область",
        "акимат",
        "статус",
        "наименование",
        "дата",
        "номер",
    ],
    "en": [
        "region",
        "status",
        "name",
        "date",
        "id",
    ],
}


def _clean_column_name(name: object) -> str:
    text = str(name).strip()
    return text.replace("\n", " ")


def _looks_like_header(row_values: List[object]) -> bool:
    normalized = [str(v).strip().lower() for v in row_values if pd.notna(v)]
    if len(normalized) < 4:
        return False
    joined = " ".join(normalized)
    hits = 0
    for bucket in HEADER_HINTS.values():
        for hint in bucket:
            if hint in joined:
                hits += 1
    return hits >= 2


def _detect_excel_header_row(path: Path, scan_rows: int = 20) -> int:
    preview = pd.read_excel(path, header=None, nrows=scan_rows)
    for idx in range(len(preview.index)):
        values = preview.iloc[idx].tolist()
        if _looks_like_header(values):
            return idx
    return 0


def _postprocess_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_clean_column_name(c) for c in df.columns]
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    df = df.reset_index(drop=True)
    return df


def read_dataframe(path_str: str) -> pd.DataFrame:
    path = Path(path_str)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path)
        return _postprocess_frame(df)

    if suffix == ".json":
        df = pd.read_json(path)
        return _postprocess_frame(df)

    if suffix in {".xlsx", ".xls"}:
        header_row = _detect_excel_header_row(path)
        df = pd.read_excel(path, header=header_row)
        return _postprocess_frame(df)

    raise ValueError(f"Unsupported file type: {suffix}")


def infer_id_column(columns: List[str], preferred: Optional[str] = None) -> Optional[str]:
    if preferred:
        return preferred if preferred in columns else None

    candidates = ["id", "inn", "bin", "ogrn", "registry", "farm", "фермер", "хозяйств", "номер заявки"]
    for col in columns:
        low = col.lower()
        if any(token in low for token in candidates):
            return col
    return None

