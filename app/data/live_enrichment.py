from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


def _norm_region(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("ё", "е")
        .replace("қ", "к")
        .replace("ғ", "г")
        .replace("ү", "у")
        .replace("ұ", "у")
    )


@dataclass
class SourceSpec:
    name: str
    url: Optional[str]
    region_key: str
    value_key: str
    query_region_param: Optional[str] = None


def _fetch_json(url: str, timeout_sec: float = 8.0) -> Optional[object]:
    if not url:
        return None
    try:
        req = Request(url, headers={"User-Agent": "AgriScore-KZ/1.0"})
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))
    except (URLError, TimeoutError, ValueError):
        return None


def _extract_items(payload: object) -> List[dict]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("results", "data", "items", "value"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def _fetch_source_for_regions(spec: SourceSpec, regions: Iterable[str]) -> Dict[str, float]:
    if not spec.url:
        return {}

    out: Dict[str, float] = {}
    if spec.query_region_param:
        for region in regions:
            params = urlencode({spec.query_region_param: region})
            joiner = "&" if "?" in spec.url else "?"
            payload = _fetch_json(f"{spec.url}{joiner}{params}")
            for item in _extract_items(payload):
                reg = _norm_region(item.get(spec.region_key, region))
                try:
                    val = float(item.get(spec.value_key))
                except (TypeError, ValueError):
                    continue
                out[reg] = val
    else:
        payload = _fetch_json(spec.url)
        for item in _extract_items(payload):
            reg = _norm_region(item.get(spec.region_key))
            if not reg:
                continue
            try:
                val = float(item.get(spec.value_key))
            except (TypeError, ValueError):
                continue
            out[reg] = val
    return out


def fetch_live_region_enrichment(regions: Iterable[str]) -> pd.DataFrame:
    region_list = sorted({_norm_region(r) for r in regions if str(r).strip()})
    if not region_list:
        return pd.DataFrame(columns=["region_norm"])

    sources = [
        SourceSpec(
            name="egov",
            url=os.getenv("AGRISCORE_EGOV_REGION_STATS_URL"),
            region_key=os.getenv("AGRISCORE_EGOV_REGION_KEY", "region"),
            value_key=os.getenv("AGRISCORE_EGOV_VALUE_KEY", "value"),
            query_region_param=os.getenv("AGRISCORE_EGOV_QUERY_REGION_PARAM"),
        ),
        SourceSpec(
            name="statgov",
            url=os.getenv("AGRISCORE_STAT_REGION_STATS_URL"),
            region_key=os.getenv("AGRISCORE_STAT_REGION_KEY", "region"),
            value_key=os.getenv("AGRISCORE_STAT_VALUE_KEY", "value"),
            query_region_param=os.getenv("AGRISCORE_STAT_QUERY_REGION_PARAM"),
        ),
        SourceSpec(
            name="weather",
            url=os.getenv("AGRISCORE_WEATHER_REGION_URL"),
            region_key=os.getenv("AGRISCORE_WEATHER_REGION_KEY", "region"),
            value_key=os.getenv("AGRISCORE_WEATHER_VALUE_KEY", "value"),
            query_region_param=os.getenv("AGRISCORE_WEATHER_QUERY_REGION_PARAM"),
        ),
        SourceSpec(
            name="market",
            url=os.getenv("AGRISCORE_MARKET_REGION_URL"),
            region_key=os.getenv("AGRISCORE_MARKET_REGION_KEY", "region"),
            value_key=os.getenv("AGRISCORE_MARKET_VALUE_KEY", "value"),
            query_region_param=os.getenv("AGRISCORE_MARKET_QUERY_REGION_PARAM"),
        ),
    ]

    frame = pd.DataFrame({"region_norm": region_list})
    for spec in sources:
        values = _fetch_source_for_regions(spec, region_list)
        frame[f"fe_ext_{spec.name}"] = frame["region_norm"].map(values)
    return frame
