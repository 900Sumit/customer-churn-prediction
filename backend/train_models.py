"""Model training, evaluation, and serialization script for ChurnLab.

Trains Logistic Regression and CatBoost classifiers on customer churn data,
evaluates both models plus an ensemble on a stratified holdout split,
and saves the trained pipelines and evaluation metrics to the models/ directory.

Usage:
    python train_models.py [--data-path path/to/telco.csv] [--save-models]
"""

import argparse
import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from production_pipeline import engineer_features

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"

NUMERIC_FEATURES = [
    "SeniorCitizen", "tenure", "MonthlyCharges",
    "TotalCharges", "ServiceCount", "AverageMonthlySpending"
]

CATEGORICAL_FEATURES = [
    "gender", "Partner", "Dependents",
    "PhoneService", "MultipleLines", "InternetService",
    "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies",
    "Contract", "PaperlessBilling", "PaymentMethod",
    "TenureGroup"
]


def build_preprocessor():
    """Build the production-identical column transformer."""
    num_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    cat_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer(
        transformers=[
            ("num", num_pipeline, NUMERIC_FEATURES),
            ("cat", cat_pipeline, CATEGORICAL_FEATURES),
        ]
    )


def create_lr_pipeline():
    preprocessor = build_preprocessor()
    classifier = LogisticRegression(
        C=10.0,
        class_weight="balanced",
        max_iter=2000,
        random_state=42,
        solver="saga",
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])


def create_catboost_pipeline():
    preprocessor = build_preprocessor()
    classifier = CatBoostClassifier(
        allow_writing_files=False,
        depth=4,
        iterations=300,
        learning_rate=0.03,
        random_seed=42,
        verbose=0,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])


def evaluate_model(name, y_true, y_pred, y_prob):
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    return {
        "model_type": name,
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
    }


def train_and_evaluate(data_path: str, save_models: bool = False):
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)

    target_col = "Churn"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in {data_path}")

    # Map target Churn to binary 0/1
    y = df[target_col].map(lambda v: 1 if str(v).strip().lower() in {"yes", "1", "true"} else 0)
    raw_x = df.drop(columns=[target_col])
    if "customerID" in raw_x.columns:
        raw_x = raw_x.drop(columns=["customerID"])

    # Engineer features
    print("Engineering features...")
    x_engineered = engineer_features(raw_x)

    # Train / test split (80/20 stratified)
    x_train, x_test, y_train, y_test = train_test_split(
        x_engineered, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Dataset: total={len(df)}, train={len(x_train)}, test={len(x_test)}")

    # 1. Logistic Regression
    print("Training Logistic Regression pipeline...")
    lr_pipeline = create_lr_pipeline()
    lr_pipeline.fit(x_train, y_train)
    lr_pred = lr_pipeline.predict(x_test)
    lr_prob = lr_pipeline.predict_proba(x_test)[:, 1]
    lr_metrics = evaluate_model("LogisticRegression", y_test, lr_pred, lr_prob)

    # 2. CatBoost
    print("Training CatBoost pipeline...")
    cb_pipeline = create_catboost_pipeline()
    cb_pipeline.fit(x_train, y_train)
    cb_pred = cb_pipeline.predict(x_test)
    cb_prob = cb_pipeline.predict_proba(x_test)[:, 1]
    cb_metrics = evaluate_model("CatBoostClassifier", y_test, cb_pred, cb_prob)

    # 3. Soft-Voting Ensemble (50% LR + 50% CatBoost)
    print("Evaluating Ensemble...")
    ensemble_prob = 0.5 * lr_prob + 0.5 * cb_prob
    ensemble_pred = (ensemble_prob >= 0.5).astype(int)
    ensemble_metrics = evaluate_model(
        "Soft-Voting Weighted Average (50% LR + 50% CatBoost)",
        y_test, ensemble_pred, ensemble_prob
    )

    results = {
        "dataset": Path(data_path).name,
        "total_samples": int(len(df)),
        "train_samples": int(len(x_train)),
        "test_samples": int(len(x_test)),
        "churn_distribution": {
            "No": int((y == 0).sum()),
            "Yes": int((y == 1).sum()),
            "churn_rate_pct": round(float((y == 1).mean() * 100), 2),
        },
        "models": {
            "logistic_regression": lr_metrics,
            "catboost": cb_metrics,
            "ensemble": ensemble_metrics,
        },
        "data_split": {"test_size": 0.20, "stratified": True, "random_state": 42},
    }

    # Save metrics
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    metrics_file = MODEL_DIR / "evaluation_metrics.json"
    with open(metrics_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Evaluation metrics saved to {metrics_file}")

    if save_models:
        lr_file = MODEL_DIR / "churn_lr_pipeline.joblib"
        cb_file = MODEL_DIR / "churn_catboost_pipeline.joblib"
        joblib.dump(lr_pipeline, lr_file)
        joblib.dump(cb_pipeline, cb_file)
        print(f"Models saved to {lr_file} and {cb_file}")

    print("\n--- Summary Results ---")
    for name, m in results["models"].items():
        print(f"{name:20s}: Accuracy={m['accuracy']:.4f}, F1={m['f1_score']:.4f}, ROC-AUC={m['roc_auc']:.4f}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train customer churn prediction models.")
    parser.add_argument("--data-path", type=str, default="", help="Path to input CSV")
    parser.add_argument("--save-models", action="store_true", help="Overwrite saved joblib model files")
    args = parser.parse_args()

    if not args.data_path:
        print("No --data-path provided. Using canonical benchmark metrics.")
    else:
        train_and_evaluate(args.data_path, save_models=args.save_models)
