"""Forecast accuracy metrics."""

import numpy as np
import pandas as pd


def mae(actual, predicted) -> float:
    """Mean absolute error: average size of the miss, in KES."""
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(predicted))))


def rmse(actual, predicted) -> float:
    """Root mean squared error: like MAE but punishes big misses more."""
    return float(np.sqrt(np.mean((np.asarray(actual) - np.asarray(predicted)) ** 2)))


def mape(actual, predicted) -> float:
    """Mean absolute percentage error (%). Safe here: monthly revenue is never zero."""
    a, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs((a - p) / a)) * 100)


def score_table(df: pd.DataFrame, actual_col: str = "actual", model_cols=None) -> pd.DataFrame:
    """MAE / RMSE / MAPE for each model column, sorted best (lowest MAE) first."""
    model_cols = model_cols or [c for c in df.columns if c != actual_col]
    rows = [{"model": m, "MAE": mae(df[actual_col], df[m]), "RMSE": rmse(df[actual_col], df[m]),
             "MAPE_%": mape(df[actual_col], df[m])} for m in model_cols]
    return pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True)
