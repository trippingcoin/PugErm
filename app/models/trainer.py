from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import shap
from scipy import sparse
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

_XGB_IMPORT_ERROR: Optional[str] = None
_LGBM_IMPORT_ERROR: Optional[str] = None
_CATBOOST_IMPORT_ERROR: Optional[str] = None

try:
    from xgboost import XGBClassifier, XGBRegressor
except Exception as exc:
    _XGB_IMPORT_ERROR = str(exc)
    XGBClassifier = None
    XGBRegressor = None

try:
    from lightgbm import LGBMClassifier, LGBMRegressor
except Exception as exc:
    _LGBM_IMPORT_ERROR = str(exc)
    LGBMClassifier = None
    LGBMRegressor = None

try:
    from catboost import CatBoostClassifier, CatBoostRegressor
except Exception as exc:
    _CATBOOST_IMPORT_ERROR = str(exc)
    CatBoostClassifier = None
    CatBoostRegressor = None


@dataclass
class ModelTrainingOutput:
    score_values: np.ndarray
    selected_model_name: str
    model_comparison: Dict[str, float]
    feature_importance: List[Tuple[str, float]]
    local_contributions: np.ndarray
    feature_names: List[str]
    mode: str
    shap_values: Optional[np.ndarray] = None


def get_ml_backend_status() -> Dict[str, Dict[str, Optional[str]]]:
    return {
        "xgboost": {
            "available": XGBClassifier is not None and XGBRegressor is not None,
            "error": _XGB_IMPORT_ERROR,
        },
        "lightgbm": {
            "available": LGBMClassifier is not None and LGBMRegressor is not None,
            "error": _LGBM_IMPORT_ERROR,
        },
        "catboost": {
            "available": CatBoostClassifier is not None and CatBoostRegressor is not None,
            "error": _CATBOOST_IMPORT_ERROR,
        },
    }


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


def _to_dense(x_matrix) -> np.ndarray:
    return x_matrix.toarray() if sparse.issparse(x_matrix) else np.asarray(x_matrix)


def _rank_corr(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    a = pd.Series(y_true).rank(pct=True).values
    b = pd.Series(y_pred).rank(pct=True).values
    corr = np.corrcoef(a, b)[0, 1]
    return 0.0 if np.isnan(corr) else float(corr)


def _fit_shap_explainer(xgb_model, x_dense: np.ndarray, feature_names: List[str]):
    """Returns (shap_values, feature_importance) using TreeExplainer."""
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer.shap_values(x_dense)
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance = sorted(
        [(feature_names[i], float(mean_abs_shap[i])) for i in range(len(feature_names))],
        key=lambda t: abs(t[1]),
        reverse=True,
    )
    return shap_values, importance


def _build_classifier_candidates() -> Dict[str, object]:
    models: Dict[str, object] = {}
    if XGBClassifier is not None:
        models["xgb"] = XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
    if LGBMClassifier is not None:
        models["lgbm"] = LGBMClassifier(
            n_estimators=500,
            num_leaves=63,
            learning_rate=0.05,
            min_child_samples=20,
            reg_alpha=0.1,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    if CatBoostClassifier is not None:
        models["catboost"] = CatBoostClassifier(
            iterations=400,
            depth=8,
            l2_leaf_reg=5,
            learning_rate=0.05,
            random_seed=42,
            verbose=0,
        )
    return models


def _build_regressor_candidates() -> Dict[str, object]:
    models: Dict[str, object] = {}
    if XGBRegressor is not None:
        models["xgb"] = XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
    if LGBMRegressor is not None:
        models["lgbm"] = LGBMRegressor(
            n_estimators=500,
            num_leaves=63,
            learning_rate=0.05,
            min_child_samples=20,
            reg_alpha=0.1,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    if CatBoostRegressor is not None:
        models["catboost"] = CatBoostRegressor(
            iterations=400,
            depth=8,
            l2_leaf_reg=5,
            learning_rate=0.05,
            random_seed=42,
            verbose=0,
        )
    return models


def train_scoring_model(x: pd.DataFrame, y: Optional[pd.Series]) -> ModelTrainingOutput:
    preprocessor, numeric_cols, categorical_cols = _build_preprocessor(x)

    if y is not None and y.notna().sum() >= 30:
        y_clean = y.dropna()
        x_clean = x.loc[y_clean.index]
        unique_count = y_clean.nunique()

        prep_fitted = preprocessor.fit(x_clean)
        feature_names = _feature_names(prep_fitted, numeric_cols, categorical_cols)

        x_clean_enc = prep_fitted.transform(x_clean)
        x_clean_dense = _to_dense(x_clean_enc)
        x_full_enc = prep_fitted.transform(x)
        x_full_dense = _to_dense(x_full_enc)

        if unique_count <= 10 and set(y_clean.unique()).issubset({0, 1, 0.0, 1.0}):
            y_bin = y_clean.astype(int).values

            base_models = _build_classifier_candidates()
            if not base_models:
                raise RuntimeError("No supervised classifier backends are available.")

            skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            oof_preds: Dict[str, np.ndarray] = {}
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="X does not have valid feature names, but LGBMClassifier was fitted with feature names",
                    category=UserWarning,
                )
                for name, model in base_models.items():
                    pred = cross_val_predict(model, x_clean_dense, y_bin, cv=skf, method="predict_proba")
                    oof_preds[name] = pred[:, 1]

            meta_features = np.column_stack(list(oof_preds.values()))
            meta_model = LogisticRegression(max_iter=2000)
            meta_model.fit(meta_features, y_bin)

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="X does not have valid feature names, but LGBMClassifier was fitted with feature names",
                    category=UserWarning,
                )
                for model in base_models.values():
                    model.fit(x_clean_dense, y_bin)

                base_preds_full = np.column_stack([m.predict_proba(x_full_dense)[:, 1] for m in base_models.values()])
            raw_scores = meta_model.predict_proba(base_preds_full)[:, 1]

            stack_train_pred = meta_model.predict_proba(meta_features)[:, 1]
            comparison = {name: float(roc_auc_score(y_bin, pred)) for name, pred in oof_preds.items()}
            comparison["stacking"] = float(roc_auc_score(y_bin, stack_train_pred))

            if "xgb" in base_models:
                shap_values, importance = _fit_shap_explainer(base_models["xgb"], x_full_dense, feature_names)
            else:
                shap_values = np.zeros((x_full_dense.shape[0], x_full_dense.shape[1]), dtype=float)
                importance = [(name, float(score)) for name, score in comparison.items() if name != "stacking"]
            selected_name = "stacking_" + "_".join(base_models.keys())
            selected_mode = "supervised_stacking_ensemble"
            local_contrib = np.asarray(shap_values)
        else:
            y_reg = y_clean.astype(float).values
            base_models = _build_regressor_candidates()
            if not base_models:
                raise RuntimeError("No supervised regressor backends are available.")

            kf = KFold(n_splits=5, shuffle=True, random_state=42)
            oof_preds: Dict[str, np.ndarray] = {}
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="X does not have valid feature names, but LGBMRegressor was fitted with feature names",
                    category=UserWarning,
                )
                for name, model in base_models.items():
                    oof_preds[name] = cross_val_predict(model, x_clean_dense, y_reg, cv=kf)

            meta_features = np.column_stack(list(oof_preds.values()))
            meta_model = Ridge(alpha=1.0)
            meta_model.fit(meta_features, y_reg)

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="X does not have valid feature names, but LGBMRegressor was fitted with feature names",
                    category=UserWarning,
                )
                for model in base_models.values():
                    model.fit(x_clean_dense, y_reg)

                base_preds_full = np.column_stack([m.predict(x_full_dense) for m in base_models.values()])
            raw_scores = meta_model.predict(base_preds_full)

            stacked_train = meta_model.predict(meta_features)
            comparison = {name: _rank_corr(y_reg, pred) for name, pred in oof_preds.items()}
            comparison["stacking"] = _rank_corr(y_reg, stacked_train)

            if "xgb" in base_models:
                shap_values, importance = _fit_shap_explainer(base_models["xgb"], x_full_dense, feature_names)
            else:
                shap_values = np.zeros((x_full_dense.shape[0], x_full_dense.shape[1]), dtype=float)
                importance = [(name, float(score)) for name, score in comparison.items() if name != "stacking"]
            selected_name = "stacking_" + "_".join(base_models.keys())
            selected_mode = "supervised_stacking_ensemble"
            local_contrib = np.asarray(shap_values)

        scores = _normalize_0_100(raw_scores)
        return ModelTrainingOutput(
            score_values=scores,
            selected_model_name=selected_name,
            model_comparison=comparison,
            feature_importance=importance[:20],
            local_contributions=local_contrib,
            feature_names=feature_names,
            mode=selected_mode,
            shap_values=np.asarray(shap_values),
        )

    comparison: Dict[str, float] = {}
    selected_name = "unsupervised_svd"
    selected_mode = "unsupervised"
    prep = preprocessor.fit(x)
    x_enc = prep.transform(x)
    if sparse.issparse(x_enc):
        x_enc = x_enc.asfptype()
    svd = TruncatedSVD(n_components=1, random_state=42)
    raw_scores = svd.fit_transform(x_enc).reshape(-1)
    feature_names = _feature_names(prep, numeric_cols, categorical_cols)
    comp = svd.components_[0]
    importance = sorted(
        [(feature_names[i], float(comp[i])) for i in range(len(feature_names))],
        key=lambda t: abs(t[1]),
        reverse=True,
    )
    local_contrib = x_enc.multiply(comp).toarray() if sparse.issparse(x_enc) else np.asarray(x_enc) * comp
    scores = _normalize_0_100(raw_scores)
    return ModelTrainingOutput(
        score_values=scores,
        selected_model_name=selected_name,
        model_comparison=comparison,
        feature_importance=importance[:20],
        local_contributions=local_contrib,
        feature_names=feature_names,
        mode=selected_mode,
        shap_values=None,
    )
