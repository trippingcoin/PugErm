import argparse
import json
import math
from typing import List, Optional

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Score agricultural producers with ML.")
	parser.add_argument("--input", default="Data.xlsx", help="Path to input file (xlsx or csv).")
	parser.add_argument("--target", default="", help="Optional target column for supervised scoring.")
	parser.add_argument("--id-column", default="", help="Optional id column.")
	parser.add_argument("--shortlist", default="20", help="Shortlist size.")
	return parser.parse_args()


def read_dataframe(path: str) -> pd.DataFrame:
	if path.lower().endswith(".csv"):
		return pd.read_csv(path)
	return pd.read_excel(path)


def pick_id_column(columns: List[str]) -> Optional[str]:
	candidates = ["id", "inn", "bin", "ogrn", "reg", "registry", "farmer"]
	for col in columns:
		low = str(col).lower()
		if any(token in low for token in candidates):
			return col
	return None


def pick_target_column(columns: List[str]) -> Optional[str]:
	candidates = ["target", "label", "outcome", "effect", "result", "profit", "revenue", "efficiency", "score"]
	for col in columns:
		low = str(col).lower()
		if any(token in low for token in candidates):
			return col
	return None


def split_features(df: pd.DataFrame, id_col: Optional[str], target_col: Optional[str]) -> pd.DataFrame:
	cols = list(df.columns)
	drop_cols = [c for c in [id_col, target_col] if c in cols]
	return df.drop(columns=drop_cols) if drop_cols else df.copy()


def build_preprocessor(numeric_cols: List[str], categorical_cols: List[str]) -> ColumnTransformer:
	numeric_pipeline = Pipeline(
		steps=[
			("imputer", SimpleImputer(strategy="median")),
			("scaler", StandardScaler()),
		]
	)
	categorical_pipeline = Pipeline(
		steps=[
			("imputer", SimpleImputer(strategy="most_frequent")),
			("onehot", OneHotEncoder(handle_unknown="ignore")),
		]
	)
	return ColumnTransformer(
		transformers=[
			("num", numeric_pipeline, numeric_cols),
			("cat", categorical_pipeline, categorical_cols),
		],
		remainder="drop",
	)


def get_feature_names(preprocessor: ColumnTransformer, numeric_cols: List[str], categorical_cols: List[str]) -> List[str]:
	feature_names: List[str] = []
	if numeric_cols:
		feature_names.extend(numeric_cols)
	if categorical_cols:
		onehot = preprocessor.named_transformers_.get("cat")
		if onehot is not None:
			encoder = onehot.named_steps.get("onehot")
			if encoder is not None:
				feature_names.extend(encoder.get_feature_names_out(categorical_cols).tolist())
	return feature_names


def normalize_scores(values: np.ndarray) -> np.ndarray:
	value_min = float(np.min(values))
	value_max = float(np.max(values))
	if math.isclose(value_min, value_max):
		return np.full_like(values, 50.0, dtype=float)
	return (values - value_min) / (value_max - value_min) * 100.0


def compute_top_factors(contributions: np.ndarray, feature_names: List[str], top_k: int = 3) -> List[dict]:
	if contributions.size == 0 or not feature_names:
		return []
	indices = np.argsort(np.abs(contributions))[-top_k:][::-1]
	result = []
	for idx in indices:
		result.append(
			{
				"feature": feature_names[idx],
				"contribution": float(contributions[idx]),
			}
		)
	return result


def main() -> None:
	args = parse_args()
	shortlist_size = max(1, int(args.shortlist))

	df = read_dataframe(args.input)
	df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")

	if df.empty:
		raise SystemExit("Input data is empty after cleaning.")

	id_col = args.id_column.strip() or pick_id_column(df.columns.tolist())
	target_col = args.target.strip() or pick_target_column(df.columns.tolist())
	if target_col not in df.columns:
		target_col = None
	if id_col not in df.columns:
		id_col = None

	features = split_features(df, id_col, target_col)
	numeric_cols = features.select_dtypes(include=["number"]).columns.tolist()
	categorical_cols = [c for c in features.columns if c not in numeric_cols]

	preprocessor = build_preprocessor(numeric_cols, categorical_cols)
	x_proc = preprocessor.fit_transform(features)
	feature_names = get_feature_names(preprocessor, numeric_cols, categorical_cols)

	mode = "unsupervised"
	model_info = {"target_column": target_col, "mode": mode}

	x_dense = x_proc.toarray() if hasattr(x_proc, "toarray") else np.asarray(x_proc)
	scores: Optional[np.ndarray] = None
	coef: Optional[np.ndarray] = None

	if target_col is not None:
		y_raw = df[target_col]
		if y_raw.dtype == object:
			y_encoded, _ = pd.factorize(y_raw)
			y_vals = pd.Series(y_encoded, index=y_raw.index, dtype="float64")
		else:
			y_vals = pd.to_numeric(y_raw, errors="coerce")

		mask = y_vals.notna()
		if mask.sum() >= 10 and y_vals[mask].nunique() > 1:
			y_train = y_vals[mask].values
			x_train = x_dense[mask.values]
			unique = np.unique(y_train)
			if len(unique) == 2:
				model = LogisticRegression(max_iter=2000)
				model.fit(x_train, y_train)
				proba = model.predict_proba(x_dense)[:, 1]
				scores = proba * 100.0
				coef = model.coef_[0]
				mode = "supervised_classification"
			else:
				model = Ridge(alpha=1.0)
				model.fit(x_train, y_train)
				pred_scores = model.predict(x_dense)
				scores = normalize_scores(pred_scores)
				coef = model.coef_
				mode = "supervised_regression"
			model_info["mode"] = mode
		else:
			target_col = None
			model_info["target_column"] = None

	if target_col is None:
		svd = TruncatedSVD(n_components=1, random_state=42)
		raw_scores = svd.fit_transform(x_dense).reshape(-1)
		scores = normalize_scores(raw_scores)
		coef = svd.components_[0]
		mode = "unsupervised_svd"
		model_info["mode"] = mode

	if scores is None or coef is None:
		raise SystemExit("Unable to compute scores with the provided data.")

	contributions = x_dense * coef
	global_factors = compute_top_factors(coef, feature_names, top_k=10)

	records = []
	for idx, row in df.iterrows():
		record_id = row[id_col] if id_col is not None else idx + 1
		record = {
			"id": str(record_id),
			"score": float(scores[idx]),
			"top_factors": compute_top_factors(contributions[idx], feature_names, top_k=3),
			"attributes": row.replace({np.nan: None}).to_dict(),
		}
		records.append(record)

	shortlist = sorted(records, key=lambda r: r["score"], reverse=True)[:shortlist_size]

	meta = {
		"rows": int(df.shape[0]),
		"features": int(x_dense.shape[1]),
		"target_column": model_info["target_column"],
		"mode": model_info["mode"],
		"score_min": float(np.min(scores)),
		"score_max": float(np.max(scores)),
		"score_mean": float(np.mean(scores)),
	}

	output = {
		"meta": meta,
		"global_factors": global_factors,
		"records": records,
		"shortlist": shortlist,
	}

	print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
	main()
