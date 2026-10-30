"""At-risk (churn) customer modelling (Milestone 6).

Definitions
- Inactivity threshold: 180 days. Derived from the data: 90% of observed gaps
  between a customer's consecutive orders are 173 days or shorter, so a
  customer silent for more than 180 days is behaving unlike 9 in 10 returns.
- Population: established customers, meaning 2+ orders by the snapshot date.
  "Drifting away" only makes sense for someone who had a buying habit.
- Label (churned = 1): NO purchase in the 6 months after the snapshot date.
- Features use ONLY orders on or before the snapshot date (no leakage).

Out-of-time validation
- Train: snapshot 2024-12-31, outcome window Jan-Jun 2025.
- Test:  snapshot 2025-06-30, outcome window Jul-Dec 2025.
- Score: snapshot 2025-12-31 (outcome unknown) -> current at-risk list.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src import config

INACTIVITY_THRESHOLD_DAYS = 180
HORIZON_MONTHS = 6
TRAIN_SNAPSHOT = pd.Timestamp("2024-12-31")
TEST_SNAPSHOT = pd.Timestamp("2025-06-30")
SCORE_SNAPSHOT = pd.Timestamp(config.END_DATE)

FEATURES = ["recency_days", "frequency", "monetary_kes", "tenure_days", "avg_order_value",
            "avg_gap_days", "overdue_ratio", "n_categories", "promo_share", "loyalty_member"]


def inter_purchase_gaps(orders: pd.DataFrame) -> pd.Series:
    """Days between consecutive orders of the same customer (walk-ins excluded)."""
    known = orders[orders["customer_id"].notna()].sort_values(["customer_id", "transaction_date"])
    return known.groupby("customer_id")["transaction_date"].diff().dt.days.dropna()


def customer_features(sales: pd.DataFrame, snapshot: pd.Timestamp, min_orders: int = 2) -> pd.DataFrame:
    """One row per established customer, built from history up to `snapshot` only."""
    hist = sales[(sales["transaction_date"] <= snapshot) & sales["customer_id"].notna()]
    orders = (hist.groupby(["customer_id", "order_id"])
              .agg(date=("transaction_date", "first"), value=("total_amount", "sum")).reset_index())
    per_customer = orders.sort_values("date").groupby("customer_id")
    f = per_customer.agg(first=("date", "min"), last=("date", "max"), frequency=("order_id", "nunique"),
                         monetary_kes=("value", "sum"))
    f["avg_gap_days"] = per_customer["date"].apply(lambda d: d.diff().dt.days.mean())
    f["recency_days"] = (snapshot - f["last"]).dt.days
    f["tenure_days"] = (snapshot - f["first"]).dt.days
    f["avg_order_value"] = f["monetary_kes"] / f["frequency"]
    # How overdue is the customer relative to their OWN usual rhythm? >1 = later than usual.
    f["overdue_ratio"] = f["recency_days"] / f["avg_gap_days"].clip(lower=1)
    f["n_categories"] = hist.groupby("customer_id")["category"].nunique()
    f["promo_share"] = hist.groupby("customer_id")["is_promo"].mean()
    f["loyalty_member"] = (hist.groupby("customer_id")["loyalty_member"].first() == "Yes").astype(int)
    f = f[f["frequency"] >= min_orders].copy()
    f["snapshot"] = snapshot
    return f.reset_index()


def add_churn_label(features: pd.DataFrame, sales: pd.DataFrame, snapshot: pd.Timestamp,
                    horizon_months: int = HORIZON_MONTHS) -> pd.DataFrame:
    """churned = 1 if the customer made no purchase in the horizon after the snapshot."""
    end = snapshot + pd.DateOffset(months=horizon_months)
    future = sales[(sales["transaction_date"] > snapshot) & (sales["transaction_date"] <= end)]
    out = features.copy()
    out["churned"] = (~out["customer_id"].isin(future["customer_id"])).astype(int)
    return out


def baseline_rule(features: pd.DataFrame, threshold_days: int = INACTIVITY_THRESHOLD_DAYS) -> np.ndarray:
    """Simple business rule: flag as churn risk if silent longer than the threshold."""
    return (features["recency_days"] > threshold_days).astype(int).to_numpy()


def logistic_model():
    # Scaling puts features on comparable scales so coefficients can be compared;
    # class_weight="balanced" stops the model from simply predicting the majority class.
    return make_pipeline(StandardScaler(),
                         LogisticRegression(class_weight="balanced", max_iter=1000, random_state=config.RANDOM_SEED))


def random_forest_model():
    return RandomForestClassifier(n_estimators=500, max_depth=4, min_samples_leaf=5, class_weight="balanced",
                                  random_state=config.RANDOM_SEED, n_jobs=-1)
