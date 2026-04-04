from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

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
    PolicyCheck,
    ScoreBreakdown,
    ScoreMeta,
    ScoreResponse,
)
from app.services.rules import evaluate_record_rules
from app.utils.logger import get_logger


logger = get_logger("scoring_service")
MODEL_VERSION = "ranker-2026.1"
FEATURE_VERSION = "features-2026.1"
POLICY_VERSION = "rules-2026.3"


@dataclass
class FilterOptions:
    region: Optional[str] = None
    farm_size: Optional[str] = None
    subsidy_type: Optional[str] = None


class ScoringService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._last_response: Optional[ScoreResponse] = None
        self._state_path = Path(".runtime/state/last_score_response.json")
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self) -> None:
        if not self._state_path.exists():
            return
        try:
            raw = self._state_path.read_text(encoding="utf-8")
            self._last_response = ScoreResponse.model_validate_json(raw)
            logger.info("Loaded persisted scoring state from %s", self._state_path)
        except Exception:
            logger.exception("Failed to load persisted scoring state")

    def _save_state(self, response: ScoreResponse) -> None:
        try:
            self._state_path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        except Exception:
            logger.exception("Failed to persist scoring state")

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
        ml_score: float,
        eligibility_score: float,
        compliance_score: float,
        growth_score: float,
        fraud_safety_score: float,
        rule_eval,
        shap_values: Optional[np.ndarray] = None,
    ) -> FarmerRecord:
        record_id = source_row[id_column] if id_column and id_column in source_row else idx + 1
        top: List[FactorContribution] = []
        positive: List[str] = []
        negative: List[str] = []

        if shap_values is not None and idx < len(shap_values):
            shap_row = np.asarray(shap_values[idx], dtype=float)
            if shap_row.ndim > 1:
                shap_row = shap_row.reshape(-1)

            top_positive_idx = np.argsort(shap_row)[-3:][::-1]
            top_negative_idx = np.argsort(shap_row)[:3]
            top_abs_idx = np.argsort(np.abs(shap_row))[-6:][::-1]

            top = [
                FactorContribution(
                    feature=self._human_feature_name(feature_names[i]),
                    contribution=float(shap_row[i]),
                )
                for i in top_abs_idx
            ]

            positive = [
                f"+ {self._human_feature_name(feature_names[i])} (SHAP: +{shap_row[i]:.3f})"
                for i in top_positive_idx
                if shap_row[i] > 0
            ]
            negative = [
                f"- {self._human_feature_name(feature_names[i])} (SHAP: {shap_row[i]:.3f})"
                for i in top_negative_idx
                if shap_row[i] < 0
            ]
        else:
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

        component_positive: List[str] = []
        component_negative: List[str] = []
        if growth_score >= 55:
            component_positive.append(f"+ Высокий потенциал роста (+{(growth_score - 50) / 2:.1f})")
        else:
            component_negative.append(f"- Низкий потенциал роста (-{(50 - growth_score) / 2:.1f})")

        if fraud_safety_score >= 55:
            component_positive.append(f"+ Низкий риск аномалий (+{(fraud_safety_score - 50) / 2:.1f})")
        else:
            component_negative.append(f"- Повышенный риск аномалий (-{(50 - fraud_safety_score) / 2:.1f})")

        if compliance_score >= 80:
            component_positive.append("+ Хорошее нормативное соответствие")
        else:
            component_negative.append("- Есть нормативные риски")

        if not rule_eval.eligibility_passed:
            component_negative.append("- Не пройдены базовые eligibility-критерии")

        recommended = rule_eval.eligibility_passed and score >= 70.0 and fraud_safety_score >= 45.0
        if not rule_eval.eligibility_passed:
            decision = "Not Recommended"
        elif recommended:
            decision = "Recommended for Commission Review"
        elif score >= 55.0:
            decision = "Manual Review Required"
        else:
            decision = "Low Priority"

        failed_high = [f for f in rule_eval.flags if not f.passed and f.severity == "high"]
        failed_medium = [f for f in rule_eval.flags if not f.passed and f.severity == "medium"]
        if failed_high:
            risk_level = "high"
        elif failed_medium:
            risk_level = "medium"
        else:
            risk_level = "low"

        return FarmerRecord(
            id=str(record_id),
            rank=rank,
            score=float(score),
            decision=decision,
            recommended=recommended,
            risk_level=risk_level,
            explanation=FarmerExplanation(
                positive=(positive + component_positive)[:4],
                negative=(negative + component_negative)[:4],
                top_features=top,
            ),
            breakdown=ScoreBreakdown(
                ml_score=float(ml_score),
                eligibility_score=float(eligibility_score),
                compliance_score=float(compliance_score),
                growth_score=float(growth_score),
                fraud_safety_score=float(fraud_safety_score),
                final_score=float(score),
            ),
            policy_checks=[PolicyCheck(**item) for item in rule_eval.policy_checks],
            compliance_flags=[
                ComplianceFlag(code=f.code, severity=f.severity, message=f.message, passed=f.passed) for f in rule_eval.flags
            ],
            attributes=attrs,
        )

    def _generate_text_explanation(self, record: FarmerRecord, lang: str = "ru") -> str:
        score = record.score
        pos = record.explanation.positive[:3]
        neg = record.explanation.negative[:2]

        if lang == "kz":
            level = "жоғары" if score >= 70 else ("орташа" if score >= 50 else "төмен")
            text = f"Сіздің ұпайыңыз {score:.1f}/100 — {level} деңгей.\n"
            text += "Күшті жақтары: " + (", ".join(pos) if pos else "анықталмады") + ".\n"
            text += "Жетілдіру бағыттары: " + (", ".join(neg) if neg else "жоқ") + "."
        else:
            level = "высокий" if score >= 70 else ("средний" if score >= 50 else "низкий")
            text = f"Ваш скор: {score:.1f}/100 — {level} приоритет.\n"
            text += "Сильные стороны: " + (", ".join(pos) if pos else "не определены") + ".\n"
            text += "Области улучшения: " + (", ".join(neg) if neg else "отсутствуют") + "."
        return text

    @staticmethod
    def _normalize_0_100(values: np.ndarray, default: float = 50.0) -> np.ndarray:
        if values.size == 0:
            return values
        low = float(np.nanmin(values))
        high = float(np.nanmax(values))
        if np.isclose(low, high) or np.isnan(low) or np.isnan(high):
            return np.full(values.shape[0], default, dtype=float)
        return (values - low) / (high - low) * 100.0

    def _growth_scores(self, prepared: PreparedData) -> np.ndarray:
        if "fe_growth_potential" not in prepared.enriched_df.columns:
            return np.full(len(prepared.enriched_df), 50.0, dtype=float)
        raw = pd.to_numeric(prepared.enriched_df["fe_growth_potential"], errors="coerce").fillna(0.0).values
        return self._normalize_0_100(raw, default=50.0)

    def _fraud_safety_scores(self, prepared: PreparedData) -> np.ndarray:
        n = len(prepared.enriched_df)
        base_risk = np.zeros(n, dtype=float)

        amount = None
        norm = None
        if "Причитающая сумма" in prepared.enriched_df.columns:
            amount = pd.to_numeric(prepared.enriched_df["Причитающая сумма"], errors="coerce")
        if "Норматив" in prepared.enriched_df.columns:
            norm = pd.to_numeric(prepared.enriched_df["Норматив"], errors="coerce")
        if amount is not None and norm is not None:
            ratio = (amount / (norm + 1e-9)).replace([np.inf, -np.inf], np.nan)
            base_risk += np.where((ratio > 20000) | (ratio < 0.1), 35.0, 0.0)
            ratio_z = (ratio - ratio.median()) / (ratio.std() + 1e-9)
            base_risk += np.clip(np.abs(ratio_z.fillna(0.0).values) * 6.0, 0.0, 30.0)

        if "fe_amount_z" in prepared.enriched_df.columns:
            amount_z = pd.to_numeric(prepared.enriched_df["fe_amount_z"], errors="coerce").fillna(0.0).abs().values
            base_risk += np.clip(amount_z * 8.0, 0.0, 25.0)

        engineered_numeric = prepared.enriched_df.select_dtypes(include=["number"]).copy()
        if not engineered_numeric.empty:
            x = engineered_numeric.fillna(engineered_numeric.median(numeric_only=True)).fillna(0.0)
            try:
                detector = IsolationForest(
                    n_estimators=180,
                    contamination=0.03,
                    random_state=42,
                    n_jobs=-1,
                )
                detector.fit(x)
                anomaly = -detector.decision_function(x)
                anomaly_scaled = self._normalize_0_100(anomaly, default=50.0)
                base_risk += anomaly_scaled * 0.35
            except Exception:
                logger.exception("Anomaly detector failed, fallback to heuristic fraud score only")

        risk = np.clip(base_risk, 0.0, 100.0)
        safety = 100.0 - risk
        return np.clip(safety, 0.0, 100.0)

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
            for _, row in stats.sort_values("count", ascending=False).iterrows()
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

    @staticmethod
    def _dcg(relevances: np.ndarray) -> float:
        if relevances.size == 0:
            return 0.0
        discounts = 1.0 / np.log2(np.arange(2, relevances.size + 2))
        gains = (2.0 ** relevances - 1.0) * discounts
        return float(np.sum(gains))

    def _ranking_metrics(
        self,
        prepared: PreparedData,
        final_scores: np.ndarray,
    ) -> Dict[str, float]:
        status_col = next((c for c in prepared.source_df.columns if "статус" in c.lower() or "status" in c.lower()), None)
        if status_col is None:
            return {}

        status = prepared.source_df[status_col].astype(str).str.strip().str.lower()
        utility_map = {
            "исполнена": 1.0,
            "одобрена": 0.8,
            "сформировано поручение": 0.65,
            "получена": 0.45,
            "отклонена": 0.1,
            "отозвано": 0.05,
            "approved": 0.8,
            "executed": 1.0,
            "rejected": 0.1,
        }
        y = status.map(utility_map).fillna(0.35).to_numpy(dtype=float)
        if y.size < 10:
            return {}

        order_model = np.argsort(-final_scores)
        top_k = min(20, len(order_model))
        model_rel = y[order_model[:top_k]]
        ideal_rel = np.sort(y)[::-1][:top_k]
        model_ndcg = self._dcg(model_rel) / (self._dcg(ideal_rel) + 1e-9)

        threshold = float(np.quantile(y, 0.8))
        model_precision = float(np.mean(model_rel >= threshold))

        date_col = next((c for c in prepared.source_df.columns if "дата" in c.lower() or "date" in c.lower()), None)
        if date_col is not None:
            dt = pd.to_datetime(prepared.source_df[date_col], errors="coerce", dayfirst=True)
            fallback = pd.Series(np.arange(len(dt)), index=dt.index, dtype="float64")
            date_rank = dt.fillna(pd.Timestamp.max)
            order_baseline = np.argsort(date_rank.astype("int64", errors="ignore") if hasattr(date_rank, "astype") else fallback.values)
        else:
            order_baseline = np.arange(len(y))
        base_rel = y[order_baseline[:top_k]]
        base_ndcg = self._dcg(base_rel) / (self._dcg(ideal_rel) + 1e-9)
        base_precision = float(np.mean(base_rel >= threshold))

        model_gain = float(np.mean(model_rel))
        base_gain = float(np.mean(base_rel))
        topk_gain_lift = ((model_gain - base_gain) / (base_gain + 1e-9)) * 100.0

        return {
            "ndcg_at_20_model": round(float(model_ndcg), 4),
            "ndcg_at_20_baseline_fcfs": round(float(base_ndcg), 4),
            "precision_at_20_model": round(float(model_precision), 4),
            "precision_at_20_baseline_fcfs": round(float(base_precision), 4),
            "topk_gain_lift_pct_vs_fcfs": round(float(topk_gain_lift), 2),
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
        )
        ml_scores = np.asarray(trained.score_values, dtype=float)
        growth_scores = self._growth_scores(prepared)
        fraud_safety_scores = self._fraud_safety_scores(prepared)

        eligibility_scores = np.zeros(len(prepared.source_df), dtype=float)
        compliance_scores = np.zeros(len(prepared.source_df), dtype=float)
        eligibility_pass = np.zeros(len(prepared.source_df), dtype=bool)
        rule_evals: List = []
        for idx in range(len(prepared.source_df)):
            attrs = prepared.source_df.iloc[idx].replace({np.nan: None}).to_dict()
            rule_eval = evaluate_record_rules(attrs)
            eligibility_scores[idx] = rule_eval.eligibility_score
            compliance_scores[idx] = rule_eval.compliance_score
            eligibility_pass[idx] = rule_eval.eligibility_passed
            rule_evals.append(rule_eval)

        final_scores = (
            0.60 * ml_scores
            + 0.20 * compliance_scores
            + 0.12 * growth_scores
            + 0.08 * fraud_safety_scores
        )
        final_scores = np.where(eligibility_pass, final_scores, final_scores * 0.35)
        final_scores = np.clip(final_scores, 0.0, 100.0)

        ranking = np.argsort(-final_scores)
        ranks = np.empty_like(ranking)
        ranks[ranking] = np.arange(1, len(ranking) + 1)

        records: List[FarmerRecord] = []
        for idx in range(len(prepared.source_df)):
            rec = self._build_record(
                idx=idx,
                source_row=prepared.source_df.iloc[idx],
                enriched_row=prepared.enriched_df.iloc[idx],
                score=float(final_scores[idx]),
                rank=int(ranks[idx]),
                id_column=prepared.id_column,
                local_contrib=trained.local_contributions[idx],
                feature_names=trained.feature_names,
                ml_score=float(ml_scores[idx]),
                eligibility_score=float(eligibility_scores[idx]),
                compliance_score=float(compliance_scores[idx]),
                growth_score=float(growth_scores[idx]),
                fraud_safety_score=float(fraud_safety_scores[idx]),
                rule_eval=rule_evals[idx],
                shap_values=trained.shap_values,
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
            score_min=float(np.min(final_scores)),
            score_max=float(np.max(final_scores)),
            score_mean=float(np.mean(final_scores)),
            excluded_columns=prepared.excluded_columns,
            system_explanation=(
                "FinalScore = 0.60*ML + 0.20*Compliance + 0.12*Growth + 0.08*FraudSafety; "
                "eligibility failures trigger strong penalty. "
                + prepared.system_explanation
            ),
            compliance_summary={},
            ranking_metrics={},
            model_version=MODEL_VERSION,
            feature_version=FEATURE_VERSION,
            policy_version=POLICY_VERSION,
        )

        fairness = self._fairness_summary(prepared.source_df, records, prepared.filter_columns.get("region"))
        compliance_summary: Dict[str, int] = {"high": 0, "medium": 0, "info": 0}
        for record in records:
            for flag in record.compliance_flags:
                if not flag.passed:
                    compliance_summary[flag.severity] = compliance_summary.get(flag.severity, 0) + 1

        meta.compliance_summary = compliance_summary
        meta.ranking_metrics = self._ranking_metrics(prepared, final_scores)
        response = ScoreResponse(
            meta=meta,
            feature_importance=importance,
            fairness=fairness,
            records=records,
            shortlist=shortlist,
            score_distribution=self._score_distribution(final_scores),
        )

        with self._lock:
            self._last_response = response
            self._save_state(response)

        logger.info("Scoring completed: rows=%s model=%s", meta.rows, meta.selected_model)
        return response

    def get_last_response(self) -> Optional[ScoreResponse]:
        with self._lock:
            return self._last_response

    def get_record_by_id(self, application_id: str) -> Optional[FarmerRecord]:
        with self._lock:
            if self._last_response is None:
                return None
            for record in self._last_response.records:
                if str(record.id) == str(application_id):
                    return record
        return None
