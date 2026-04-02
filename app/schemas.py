from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FactorContribution(BaseModel):
    feature: str
    contribution: float


class ComplianceFlag(BaseModel):
    code: str
    severity: str
    message: str
    passed: bool


class FarmerExplanation(BaseModel):
    positive: List[str] = Field(default_factory=list)
    negative: List[str] = Field(default_factory=list)
    top_features: List[FactorContribution] = Field(default_factory=list)


class FarmerRecord(BaseModel):
    id: str
    rank: int
    score: float
    explanation: FarmerExplanation
    compliance_flags: List[ComplianceFlag] = Field(default_factory=list)
    attributes: Dict[str, Any]


class FairnessGroupMetric(BaseModel):
    group: str
    count: int
    mean_score: float
    median_score: float


class FairnessSummary(BaseModel):
    protected_attribute: str
    groups: List[FairnessGroupMetric]
    mean_score_gap: float


class ScoreMeta(BaseModel):
    rows: int
    source_columns: int
    engineered_features: int
    target_column: Optional[str] = None
    mode: str
    selected_model: str
    model_comparison: Dict[str, float]
    score_min: float
    score_max: float
    score_mean: float
    excluded_columns: List[str]
    system_explanation: str
    compliance_summary: Dict[str, int] = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    meta: ScoreMeta
    feature_importance: List[FactorContribution]
    fairness: Optional[FairnessSummary] = None
    records: List[FarmerRecord]
    shortlist: List[FarmerRecord]
    score_distribution: Dict[str, Any]
