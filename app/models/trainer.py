from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import make_scorer, mean_absolute_error
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass
class ModelTrainingOutput:
    score_values: np.ndarray
    selected_model_name: str
    model_comparison: Dict[str, float]
    feature_importance: List[Tuple[str, float]]
    local_contributions: np.ndarray
    feature_names: List[str]
    mode: str


def _normalize_0_100(values: np.ndarray) -> np.ndarray:
    low = float(np.min(values))
    high = float(np.max(values))
    if np.isclose(low, high):
        return np.full_like(values, 50.0, dtype=float)
    return (values - low) / (high - low) * 100.0


def _build_preprocessor(df: pd.DataFrame) -> Tuple[ColumnTransformer, List[str], List[str]]:
    numeric_cols = df.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols]

    num_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler(with_mean=False)),
        ]
    )
    cat_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipe, numeric_cols),
            ("cat", cat_pipe, categorical_cols),
        ],
        remainder="drop",
        sparse_threshold=0.3,
    )
    return preprocessor, numeric_cols, categorical_cols


def _feature_names(preprocessor: ColumnTransformer, numeric_cols: List[str], categorical_cols: List[str]) -> List[str]:
    out = list(numeric_cols)
    if categorical_cols:
        cat_pipeline = preprocessor.named_transformers_.get("cat")
        if cat_pipeline is not None:
            encoder = cat_pipeline.named_steps["onehot"]
            out.extend(encoder.get_feature_names_out(categorical_cols).tolist())
    return out


def _safe_auc_cv(model: BaseEstimator, x: pd.DataFrame, y: pd.Series) -> float:
    y_int = y.astype(int)
    if y_int.nunique() < 2:
        return 0.0
    splits = min(5, max(2, int(y_int.value_counts().min())))
    cv = StratifiedKFold(n_splits=splits, shuffle=True, random_state=42)
    scores = cross_val_score(model, x, y_int, cv=cv, scoring="roc_auc")
    return float(np.mean(scores))


def _safe_mae_cv(model: BaseEstimator, x: pd.DataFrame, y: pd.Series) -> float:
    if y.nunique() < 2:
        return 0.0
    cv = KFold(n_splits=min(5, max(2, len(y) // 1000 + 2)), shuffle=True, random_state=42)
    scorer = make_scorer(mean_absolute_error, greater_is_better=False)
    scores = cross_val_score(model, x, y, cv=cv, scoring=scorer)
    return float(np.mean(scores))


def _predict_raw(model: Pipeline, x: pd.DataFrame, problem_type: str) -> np.ndarray:
    if problem_type == "classification":
        if hasattr(model, "predict_proba"):
            return model.predict_proba(x)[:, 1]
        return model.decision_function(x)
    if problem_type == "regression":
        return model.predict(x)
    raise ValueError(f"Unsupported problem type: {problem_type}")


def _sparse_row_contrib(x_matrix, coef: np.ndarray, top_k: int = 3) -> np.ndarray:
    if sparse.issparse(x_matrix):
        contrib = x_matrix.multiply(coef)
        return contrib.toarray()
    return np.asarray(x_matrix) * coef


def _fit_surrogate(preprocessor: ColumnTransformer, x: pd.DataFrame, raw_scores: np.ndarray) -> Tuple[np.ndarray, List[str], List[Tuple[str, float]]]:
    x_enc = preprocessor.transform(x)
    feature_names = _feature_names(
        preprocessor,
        preprocessor.transformers_[0][2],  # numeric columns
        preprocessor.transformers_[1][2],  # categorical columns
    )

    surrogate = Ridge(alpha=10.0, random_state=42)
    surrogate.fit(x_enc, raw_scores)
    coef = surrogate.coef_
    local_contributions = _sparse_row_contrib(x_enc, coef)
    denom = float(np.sum(np.abs(coef)) + 1e-9)
    importance = sorted(
        [(feature_names[i], float(coef[i] / denom * 100.0)) for i in range(len(feature_names))],
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    return local_contributions, feature_names, importance


def train_scoring_model(x: pd.DataFrame, y: Optional[pd.Series], mode: str) -> ModelTrainingOutput:
    preprocessor, numeric_cols, categorical_cols = _build_preprocessor(x)
    n_components = min(64, max(2, len(numeric_cols) + len(categorical_cols)))

    if y is not None and y.notna().sum() >= 30:
        y_clean = y.dropna()
        x_clean = x.loc[y_clean.index]
        unique_count = y_clean.nunique()

        if unique_count <= 10 and set(y_clean.unique()).issubset({0, 1, 0.0, 1.0}):
            problem_type = "classification"
            model_candidates: Dict[str, Pipeline] = {
                "logistic_regression": Pipeline(
                    steps=[
                        ("prep", preprocessor),
                        ("model", LogisticRegression(max_iter=3000, class_weight="balanced")),
                    ]
                ),
                "hgb_classifier": Pipeline(
                    steps=[
                        ("prep", preprocessor),
                        ("svd", TruncatedSVD(n_components=n_components, random_state=42)),
                        ("model", HistGradientBoostingClassifier(random_state=42)),
                    ]
                ),
            }
            comparison = {name: _safe_auc_cv(model, x_clean, y_clean) for name, model in model_candidates.items()}
            selected_name = max(comparison, key=comparison.get)
            selected = model_candidates[selected_name]
            selected.fit(x_clean, y_clean.astype(int))
            raw_scores = _predict_raw(selected, x, problem_type)
            selected_mode = "supervised_classification"
        else:
            problem_type = "regression"
            model_candidates = {
                "ridge_regression": Pipeline(
                    steps=[
                        ("prep", preprocessor),
                        ("model", Ridge(alpha=1.0, random_state=42)),
                    ]
                ),
                "random_forest_regression": Pipeline(
                    steps=[
                        ("prep", preprocessor),
                        ("svd", TruncatedSVD(n_components=n_components, random_state=42)),
                        ("model", RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)),
                    ]
                ),
            }
            # Higher is better because scorer returns negative MAE.
            comparison = {name: _safe_mae_cv(model, x_clean, y_clean) for name, model in model_candidates.items()}
            selected_name = max(comparison, key=comparison.get)
            selected = model_candidates[selected_name]
            selected.fit(x_clean, y_clean)
            raw_scores = _predict_raw(selected, x, problem_type)
            selected_mode = "supervised_regression"
    else:
        comparison = {}
        selected_name = "unsupervised_svd"
        selected_mode = "unsupervised"
        prep = preprocessor.fit(x)
        x_enc = prep.transform(x)
        if sparse.issparse(x_enc):
            x_enc = x_enc.asfptype()
        svd = TruncatedSVD(n_components=1, random_state=42)
        raw_scores = svd.fit_transform(x_enc).reshape(-1)
        # Build feature importance from projection.
        feature_names = _feature_names(prep, numeric_cols, categorical_cols)
        comp = svd.components_[0]
        importance = sorted(
            [(feature_names[i], float(comp[i])) for i in range(len(feature_names))],
            key=lambda t: abs(t[1]),
            reverse=True,
        )
        local_contrib = _sparse_row_contrib(x_enc, comp)
        scores = _normalize_0_100(raw_scores)
        return ModelTrainingOutput(
            score_values=scores,
            selected_model_name=selected_name,
            model_comparison=comparison,
            feature_importance=importance[:20],
            local_contributions=local_contrib,
            feature_names=feature_names,
            mode=selected_mode,
        )

    scores = _normalize_0_100(raw_scores)

    prep_fitted = selected.named_steps["prep"]
    local_contrib, feature_names, importance = _fit_surrogate(prep_fitted, x, raw_scores)
    return ModelTrainingOutput(
        score_values=scores,
        selected_model_name=selected_name,
        model_comparison=comparison,
        feature_importance=importance[:20],
        local_contributions=local_contrib,
        feature_names=feature_names,
        mode=selected_mode,
    )
