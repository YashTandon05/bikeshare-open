"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
     python -m src.train --validation-target-experiment   (Exercise 4;
       validation rows only, writes TARGET_TRANSFORM_VALIDATION)
     python -m src.train --final-target-test              (Exercise 4;
       single final test look, writes TARGET_TRANSFORM_FINAL_TEST)
"""
import json
import sys

import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import (
    METRICS,
    PROCESSED,
    TARGET,
    TARGET_TRANSFORM_FINAL_TEST,
    TARGET_TRANSFORM_VALIDATION,
    TRAIN_END,
    VALID_END,
)
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score() -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    for name, model in MODELS.items():
        model.fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in [("valid", valid), ("test", test)]
        }
    return results


# --- Exercise 4: predict the daily change, validation only ---------------
LAG_COL = "cnt_lag_1"


def reconstruct_from_change(model, X: pd.DataFrame):
    """Level forecast = yesterday's count (known at prediction time) plus the
    predicted change. Reads only the feature frame X; today's count is never
    an input."""
    return X[LAG_COL].to_numpy(dtype=float) + model.predict(X)


def _target_comparison(train: pd.DataFrame, part: pd.DataFrame, cols: list[str]) -> dict:
    """Fit the four MODELS and hgb-on-change on `train` only; score on `part`.
    The true `part[TARGET]` is used for scoring and nothing else."""
    preds = {name: clone(est).fit(train[cols], train[TARGET]).predict(part[cols])
             for name, est in MODELS.items()}
    change_model = clone(MODELS["hgb"]).fit(train[cols], train[TARGET] - train[LAG_COL])
    preds["hgb_daily_change"] = reconstruct_from_change(change_model, part[cols])

    y = part[TARGET]  # used for scoring only
    return {
        name: {"r2": round(float(r2_score(y, p)), 4),
               "mae": round(float(mean_absolute_error(y, p)), 1)}
        for name, p in preds.items()
    }


def validation_target_experiment() -> dict:
    """Ordinary models vs hgb fitted on cnt - cnt_lag_1, on the validation
    rows only. Test rows are dropped before anything is fitted or scored."""
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, _ = temporal_split(df)
    return {
        "experiment": "hgb trained on cnt - cnt_lag_1; prediction = cnt_lag_1 + predicted change",
        "split": "validation only; test rows never fitted, predicted or scored",
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "valid_dates": [str(valid.dteday.min().date()), str(valid.dteday.max().date())],
        "valid": _target_comparison(train, valid, cols),
    }


def final_target_test() -> dict:
    """The single, planned final test look for Exercise 4. Same 15 features,
    same parameters, fitted on the 2011 rows only (no refit on validation),
    so the test numbers belong to exactly the models validated earlier."""
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, _, test = temporal_split(df)
    return {
        "experiment": "hgb trained on cnt - cnt_lag_1; prediction = cnt_lag_1 + predicted change",
        "split": "final test, single look; fitted on 2011 train rows only, no validation refit",
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_test": len(test),
        "test_dates": [str(test.dteday.min().date()), str(test.dteday.max().date())],
        "test": _target_comparison(train, test, cols),
    }


def markdown_table(scores: dict, split: str = "valid") -> str:
    rows = [f"| method | {split} R^2 | {split} MAE (rides) |", "|---|---|---|"]
    rows += [f"| {name} | {s['r2']:.4f} | {s['mae']:.1f} |" for name, s in scores.items()]
    return "\n".join(rows)


if __name__ == "__main__":
    if "--validation-target-experiment" in sys.argv:
        res = validation_target_experiment()
        TARGET_TRANSFORM_VALIDATION.parent.mkdir(parents=True, exist_ok=True)
        TARGET_TRANSFORM_VALIDATION.write_text(json.dumps(res, indent=2))
        print(markdown_table(res["valid"]))
        print(f"OK target experiment: {res['n_valid']} validation rows "
              f"-> {TARGET_TRANSFORM_VALIDATION.name} (test untouched)")
    elif "--final-target-test" in sys.argv:
        res = final_target_test()
        TARGET_TRANSFORM_FINAL_TEST.parent.mkdir(parents=True, exist_ok=True)
        TARGET_TRANSFORM_FINAL_TEST.write_text(json.dumps(res, indent=2))
        print(markdown_table(res["test"], split="test"))
        print(f"OK final target test: {res['n_test']} test rows "
              f"-> {TARGET_TRANSFORM_FINAL_TEST.name}")
    else:
        res = fit_and_score()
        METRICS.parent.mkdir(parents=True, exist_ok=True)
        METRICS.write_text(json.dumps(res, indent=2))
        print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
