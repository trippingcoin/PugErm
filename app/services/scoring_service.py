from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.data.features import PreparedData, prepare_features
from app.data.loader import infer_id_column, read_dataframe
from app.models.trainer import ModelTrainingOutput, train_scoring_model
from app.schemas import (
    ComplianceFlag,
    FactorContribution,
    FairnessGroupMetric,
    FairnessSummary,
    FarmerExplanation,
    FarmerRecord,
    ScoreMeta,
    ScoreResponse,
)
from app.services.rules import evaluate_compliance
from app.utils.logger import get_logger


logger = get_logger("scoring_service")


@dataclass
class FilterOptions:
    region: Optional[str] = None
    farm_size: Optional[str] = None
    subsidy_type: Optional[str] = None


class ScoringService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._last_response: Optional[ScoreResponse] = None

    @staticmethod
    def _human_feature_name(name: str) -> str:
        cleaned = name.replace("fe_", "").replace("_", " ")
        text = cleaned.strip().title()
        return text if len(text) <= 90 else f"{text[:87]}..."

    def _build_record(
        self,
        idx: int,
        source_row: pd.Series,
        enriched_row: pd.Series,
        score: float,
        rank: int,
        id_column: Optional[str],
        local_contrib: np.ndarray,
        feature_names: List[str],
    ) -> FarmerRecord:
        record_id = source_row[id_column] if id_column and id_column in source_row else idx + 1
        norm = float(np.sum(np.abs(local_contrib)) + 1e-9)
        normalized = local_contrib / norm * 100.0
        abs_order = np.argsort(np.abs(normalized))[-3:][::-1]
        top = [
            FactorContribution(
                feature=self._human_feature_name(feature_names[i]),
                contribution=float(normalized[i]),
            )
            for i in abs_order
        ]

        positive = [f"+ {x.feature} ({x.contribution:.2f})" for x in top if x.contribution > 0][:3]
        negative = [f"- {x.feature} ({x.contribution:.2f})" for x in top if x.contribution < 0][:3]

        attrs = source_row.replace({np.nan: None}).to_dict()
        if "fe_farm_size_bucket" in enriched_row.index:
            attrs["fe_farm_size_bucket"] = enriched_row["fe_farm_size_bucket"]

        return FarmerRecord(
            id=str(record_id),
            rank=rank,
            score=float(score),
            explanation=FarmerExplanation(
                positive=positive,
                negative=negative,
                top_features=top,
            ),
            compliance_flags=[
                ComplianceFlag(
                    code=f.code,
                    severity=f.severity,
                    message=f.message,
                    passed=f.passed,
                )
                for f in evaluate_compliance(attrs)
            ],
            attributes=attrs,
        )

    @staticmethod
    def _apply_filters(
        records: List[FarmerRecord],
        filters: FilterOptions,
        prepared: PreparedData,
    ) -> List[FarmerRecord]:
        if not records:
            return records

        region_col = prepared.filter_columns.get("region")
        subsidy_col = prepared.filter_columns.get("subsidy_type")
        farm_size_col = prepared.filter_columns.get("farm_size_bucket")

        filtered = records
        if filters.region and region_col:
            filtered = [r for r in filtered if str(r.attributes.get(region_col, "")).lower() == filters.region.lower()]
        if filters.subsidy_type and subsidy_col:
            filtered = [
                r
                for r in filtered
                if str(r.attributes.get(subsidy_col, "")).lower() == filters.subsidy_type.lower()
            ]
        if filters.farm_size and farm_size_col:
            filtered = [
                r
                for r in filtered
                if str(r.attributes.get(farm_size_col, "")).lower() == filters.farm_size.lower()
            ]
        return filtered

    @staticmethod
    def _fairness_summary(source: pd.DataFrame, records: List[FarmerRecord], region_col: Optional[str]) -> Optional[FairnessSummary]:
        if not region_col or region_col not in source.columns:
            return None
        if not records:
            return None

        rec_df = pd.DataFrame(
            {
                "row_index": np.arange(len(records)),
                "score": [r.score for r in records],
                "region": source[region_col].astype(str).values[: len(records)],
            }
        )
        stats = rec_df.groupby("region")["score"].agg(["count", "mean", "median"]).reset_index()
        if stats.empty:
            return None

        groups = [
            FairnessGroupMetric(
                group=str(row["region"]),
                count=int(row["count"]),
                mean_score=float(row["mean"]),
                median_score=float(row["median"]),
            )
            for _, row in stats.sort_values("count", ascending=False).head(10).iterrows()
        ]
        gap = float(stats["mean"].max() - stats["mean"].min()) if len(stats) > 1 else 0.0
        return FairnessSummary(
            protected_attribute=region_col,
            groups=groups,
            mean_score_gap=gap,
        )

    @staticmethod
    def _score_distribution(scores: np.ndarray) -> Dict[str, List[float]]:
        hist, bins = np.histogram(scores, bins=10, range=(0, 100))
        return {
            "bins": bins[:-1].round(2).tolist(),
            "counts": hist.astype(int).tolist(),
        }

    def run_scoring(
        self,
        input_path: str,
        shortlist_n: int = 20,
        target_column: Optional[str] = None,
        id_column: Optional[str] = None,
        filters: Optional[FilterOptions] = None,
    ) -> ScoreResponse:
        logger.info("Scoring started for input=%s", input_path)
        df = read_dataframe(input_path)
        id_inferred = infer_id_column(df.columns.tolist(), id_column)
        prepared = prepare_features(df, id_column=id_inferred, target_column=target_column)

        trained: ModelTrainingOutput = train_scoring_model(
            prepared.feature_df,
            prepared.target_series,
            prepared.mode,
        )

        ranking = np.argsort(-trained.score_values)
        ranks = np.empty_like(ranking)
        ranks[ranking] = np.arange(1, len(ranking) + 1)

        records: List[FarmerRecord] = []
        for idx in range(len(prepared.source_df)):
            rec = self._build_record(
                idx=idx,
                source_row=prepared.source_df.iloc[idx],
                enriched_row=prepared.enriched_df.iloc[idx],
                score=float(trained.score_values[idx]),
                rank=int(ranks[idx]),
                id_column=prepared.id_column,
                local_contrib=trained.local_contributions[idx],
                feature_names=trained.feature_names,
            )
            records.append(rec)

        records.sort(key=lambda r: r.score, reverse=True)
        filters = filters or FilterOptions()
        filtered_records = self._apply_filters(records, filters, prepared)
        shortlist = filtered_records[: max(1, shortlist_n)]

        importance = [
            FactorContribution(feature=self._human_feature_name(name), contribution=value)
            for name, value in trained.feature_importance
        ]

        meta = ScoreMeta(
            rows=int(prepared.source_df.shape[0]),
            source_columns=int(prepared.source_df.shape[1]),
            engineered_features=int(prepared.feature_df.shape[1]),
            target_column=prepared.target_column,
            mode=trained.mode,
            selected_model=trained.selected_model_name,
            model_comparison={k: round(v, 4) for k, v in trained.model_comparison.items()},
            score_min=float(np.min(trained.score_values)),
            score_max=float(np.max(trained.score_values)),
            score_mean=float(np.mean(trained.score_values)),
            excluded_columns=prepared.excluded_columns,
            system_explanation=prepared.system_explanation,
            compliance_summary={},
        )

        fairness = self._fairness_summary(prepared.source_df, records, prepared.filter_columns.get("region"))
        compliance_summary: Dict[str, int] = {"high": 0, "medium": 0, "info": 0}
        for record in records:
            for flag in record.compliance_flags:
                if not flag.passed:
                    compliance_summary[flag.severity] = compliance_summary.get(flag.severity, 0) + 1

        meta.compliance_summary = compliance_summary
        response = ScoreResponse(
            meta=meta,
            feature_importance=importance,
            fairness=fairness,
            records=records,
            shortlist=shortlist,
            score_distribution=self._score_distribution(trained.score_values),
        )

        with self._lock:
            self._last_response = response

        logger.info("Scoring completed: rows=%s model=%s", meta.rows, meta.selected_model)
        return response

    def get_last_response(self) -> Optional[ScoreResponse]:
        with self._lock:
            return self._last_response
