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


class PolicyCheck(BaseModel):
    policy_id: str
    category: str
    severity: str
    passed: bool
    message: str
    source: str


class FarmerExplanation(BaseModel):
    positive: List[str] = Field(default_factory=list)
    negative: List[str] = Field(default_factory=list)
    top_features: List[FactorContribution] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    ml_score: float
    eligibility_score: float
    compliance_score: float
    growth_score: float
    fraud_safety_score: float
    final_score: float


class FarmerRecord(BaseModel):
    id: str
    rank: int
    score: float
    decision: str
    recommended: bool
    risk_level: str
    explanation: FarmerExplanation
    breakdown: ScoreBreakdown
    policy_checks: List[PolicyCheck] = Field(default_factory=list)
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
    ranking_metrics: Dict[str, float] = Field(default_factory=dict)
    model_version: str = "ranker-2026.1"
    feature_version: str = "features-2026.1"
    policy_version: str = "rules-2026.3"


class CommissionDecision(BaseModel):
    application_id: str
    decision: str
    reason_code: str
    comment: Optional[str] = None
    decided_by: str
    decided_at: str


class CommissionDecisionRequest(BaseModel):
    application_id: str
    decision: str
    reason_code: str
    comment: Optional[str] = None
    decided_by: str


class AuditEntry(BaseModel):
    application_id: str
    action: str
    actor: str
    at: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    meta: ScoreMeta
    feature_importance: List[FactorContribution]
    fairness: Optional[FairnessSummary] = None
    records: List[FarmerRecord]
    shortlist: List[FarmerRecord]
    score_distribution: Dict[str, Any]
