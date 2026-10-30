"""Leakage and correctness checks for the forecasting and churn code."""

import pandas as pd
import pytest

from src.analysis import eda
from src.modeling import churn as ch
from src.modeling import forecasting as fc
from src.modeling import metrics as mt


@pytest.fixture(scope="module")
def sales():
    return eda.load_analytical()


@pytest.fixture(scope="module")
def store_month(sales):
    return fc.monthly_store_revenue(sales)


def test_lag_features_look_backwards_only(store_month):
    panel = fc.build_panel(store_month)
    one = panel[panel["town"] == "Thika"].set_index("month")
    assert one.loc["2024-05-01", "lag_1"] == one.loc["2024-04-01", "revenue"]
    assert one.loc["2024-05-01", "lag_3"] == one.loc["2024-02-01", "revenue"]


def test_forecast_unchanged_when_future_data_changes(store_month):
    """If any future value leaked into training, altering it would change the forecast."""
    target = pd.Timestamp("2025-03-01")
    params = {"n_estimators": 50, "max_depth": 3, "min_samples_leaf": 1}
    original = fc.random_forest_store_forecast(fc.build_panel(store_month), target, params)
    tampered = store_month.copy()
    tampered.loc[tampered["month"] >= target, "revenue"] *= 10
    changed = fc.random_forest_store_forecast(fc.build_panel(tampered), target, params)
    pd.testing.assert_series_equal(original, changed)


def test_churn_features_use_only_history(sales):
    feats = ch.customer_features(sales, ch.TRAIN_SNAPSHOT)
    assert (feats["last"] <= ch.TRAIN_SNAPSHOT).all()
    assert (feats["recency_days"] >= 0).all()
    assert (feats["frequency"] >= 2).all()


def test_churn_label_uses_only_outcome_window(sales):
    feats = ch.customer_features(sales, ch.TRAIN_SNAPSHOT)
    labelled = ch.add_churn_label(feats, sales, ch.TRAIN_SNAPSHOT)
    window = sales[(sales["transaction_date"] > ch.TRAIN_SNAPSHOT)
                   & (sales["transaction_date"] <= ch.TRAIN_SNAPSHOT + pd.DateOffset(months=6))]
    returned = set(window["customer_id"].dropna())
    assert ((labelled["churned"] == 0) == labelled["customer_id"].isin(returned)).all()


def test_metrics():
    assert mt.mae([100, 200], [110, 190]) == 10
    assert mt.rmse([0, 0], [3, 4]) == pytest.approx(3.5355, rel=1e-3)
    assert mt.mape([100, 200], [110, 180]) == pytest.approx(10.0)
