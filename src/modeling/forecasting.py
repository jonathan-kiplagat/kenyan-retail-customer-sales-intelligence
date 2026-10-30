"""Monthly revenue forecasting (Milestone 6).

Design
- Target: net revenue per month, for the whole chain and for each store.
- Chronological split: train = 2024, validation = Jan-Jun 2025, test = Jul-Dec 2025.
- Walk-forward (rolling-origin) evaluation: to forecast month t, every model is
  fitted ONLY on months before t. This mimics real use (forecast next month
  from the past) and makes target leakage impossible.

Models
- Baselines: naive (last month), seasonal naive (same month last year),
  3-month moving average.
- Statistical: Holt's exponential smoothing (level + damped trend). A seasonal
  ETS model needs at least two full years before the first forecast, which
  this data does not have.
- Machine learning: Random Forest on a store x month panel with lag features,
  calendar features and the PLANNED promotion/holiday calendar (known in
  advance, so not leakage). Store forecasts are summed to a chain forecast.
"""

import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from src import config

TRAIN_END = pd.Timestamp("2024-12-01")
VALIDATION_MONTHS = pd.date_range("2025-01-01", "2025-06-01", freq="MS")
TEST_MONTHS = pd.date_range("2025-07-01", "2025-12-01", freq="MS")
NEXT_MONTH = pd.Timestamp("2026-01-01")

FEATURES = ["lag_1", "lag_2", "lag_3", "rolling_mean_3", "rolling_mean_6", "store_level",
            "month_sin", "month_cos", "is_december", "is_january",
            "holidays_in_month", "promo_days_in_month", "promo_categories", "time_index"]


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------
def monthly_store_revenue(sales: pd.DataFrame) -> pd.DataFrame:
    """Long table: one row per store per month (all 24 x 6 combinations)."""
    m = (sales.groupby([pd.Grouper(key="transaction_date", freq="MS"), "town"])["total_amount"]
         .sum().unstack(fill_value=0).stack().rename("revenue").reset_index()
         .rename(columns={"transaction_date": "month"}))
    return m.sort_values(["town", "month"]).reset_index(drop=True)


def calendar_features(months: pd.DatetimeIndex) -> pd.DataFrame:
    """Features known IN ADVANCE for any month: seasonality, holidays, planned promotions.

    Holidays come from the public holiday file. Promotions come from the campaign
    plan, which management sets before the month starts, so using them is not leakage.
    For months beyond the data (January 2026) holidays and promotions are taken from
    the same month one year earlier, the plan management would most likely repeat.
    """
    holidays = pd.read_csv(config.EXTERNAL_DIR / "kenya_public_holidays_2024_2025.csv", parse_dates=["date"])
    promos = pd.read_csv(config.CLEANED_DIR / "promotions.csv", parse_dates=["start_date", "end_date"])
    last_known = pd.Timestamp(config.END_DATE)
    rows = []
    for m in months:
        ref = m if m <= last_known else m - pd.DateOffset(years=1)   # repeat last year's plan
        days = pd.date_range(ref, ref + pd.offsets.MonthEnd(0))
        promo_days, promo_cats = set(), set()
        for p in promos.itertuples():
            overlap = days[(days >= p.start_date) & (days <= p.end_date)]
            promo_days.update(overlap)
            if len(overlap):
                promo_cats.add(p.target_category)
        rows.append({"month": m,
                     "month_sin": np.sin(2 * np.pi * m.month / 12),
                     "month_cos": np.cos(2 * np.pi * m.month / 12),
                     "is_december": int(m.month == 12), "is_january": int(m.month == 1),
                     "holidays_in_month": int(holidays["date"].isin(days).sum()),
                     "promo_days_in_month": len(promo_days), "promo_categories": len(promo_cats)})
    return pd.DataFrame(rows)


def build_panel(store_month: pd.DataFrame, extra_months=()) -> pd.DataFrame:
    """Add lag and calendar features. Lags only look BACKWARDS (shift >= 1)."""
    months = pd.DatetimeIndex(sorted(set(store_month["month"]) | set(extra_months)))
    stores = store_month["town"].unique()
    grid = pd.MultiIndex.from_product([stores, months], names=["town", "month"]).to_frame(index=False)
    p = grid.merge(store_month, on=["town", "month"], how="left").sort_values(["town", "month"])
    g = p.groupby("town")["revenue"]
    for k in (1, 2, 3):
        p[f"lag_{k}"] = g.shift(k)
    p["rolling_mean_3"] = g.transform(lambda s: s.shift(1).rolling(3).mean())
    p["rolling_mean_6"] = g.transform(lambda s: s.shift(1).rolling(6, min_periods=3).mean())
    p["time_index"] = (p["month"].dt.year - 2024) * 12 + p["month"].dt.month
    p = p.merge(calendar_features(months), on="month", how="left")
    return p.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Chain-level models (one series)
# ---------------------------------------------------------------------------
def naive(history: pd.Series) -> float:
    return float(history.iloc[-1])


def seasonal_naive(history: pd.Series, target_month: pd.Timestamp) -> float:
    return float(history.loc[target_month - pd.DateOffset(years=1)])


def moving_average(history: pd.Series, window: int = 3) -> float:
    return float(history.iloc[-window:].mean())


def holt(history: pd.Series, damped: bool = True) -> float:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")          # small-sample convergence warnings
        fit = ExponentialSmoothing(history.to_numpy(), trend="add", damped_trend=damped,
                                   initialization_method="estimated").fit()
    return float(fit.forecast(1)[0])


# ---------------------------------------------------------------------------
# Random Forest on the store panel
# ---------------------------------------------------------------------------
def random_forest_store_forecast(panel: pd.DataFrame, target_month: pd.Timestamp,
                                 rf_params: dict, seed: int = config.RANDOM_SEED) -> pd.Series:
    """Train on store-months strictly before target_month; predict each store."""
    data = panel.copy()
    # Store level = the store's average revenue over the TRAINING window only
    # (computed per forecast origin, so no future information leaks in).
    past = data[data["month"] < target_month]
    data["store_level"] = data["town"].map(past.groupby("town")["revenue"].mean())
    train = data[(data["month"] < target_month)].dropna(subset=FEATURES + ["revenue"])
    target = data[data["month"] == target_month]
    model = RandomForestRegressor(random_state=seed, n_jobs=-1, **rf_params)
    model.fit(train[FEATURES], train["revenue"])
    return pd.Series(model.predict(target[FEATURES]), index=target["town"].to_numpy())


def fitted_random_forest(panel: pd.DataFrame, before_month: pd.Timestamp, rf_params: dict,
                         seed: int = config.RANDOM_SEED):
    """Return a fitted model and its training data (used for feature importance)."""
    data = panel.copy()
    past = data[data["month"] < before_month]
    data["store_level"] = data["town"].map(past.groupby("town")["revenue"].mean())
    train = data[data["month"] < before_month].dropna(subset=FEATURES + ["revenue"])
    model = RandomForestRegressor(random_state=seed, n_jobs=-1, **rf_params).fit(train[FEATURES], train["revenue"])
    return model, train


# ---------------------------------------------------------------------------
# Walk-forward evaluation
# ---------------------------------------------------------------------------
def walk_forward(store_month: pd.DataFrame, months, rf_params: dict, holt_damped: bool = True) -> tuple:
    """Forecast each month in `months` using only earlier months.

    Returns (chain_predictions, store_predictions):
    - chain: one row per month with the actual and every model's forecast;
    - store: one row per store-month with actual, naive and Random Forest forecasts.
    """
    chain = store_month.groupby("month")["revenue"].sum()
    panel = build_panel(store_month)
    chain_rows, store_rows = [], []
    for m in months:
        hist = chain[chain.index < m]
        rf_store = random_forest_store_forecast(panel, m, rf_params)
        chain_rows.append({
            "month": m, "actual": chain.loc[m],
            "Naive (last month)": naive(hist),
            "Seasonal naive (last year)": seasonal_naive(hist, m),
            "Moving average (3 months)": moving_average(hist, 3),
            "Holt exponential smoothing": holt(hist, damped=holt_damped),
            "Random Forest (store panel)": rf_store.sum(),
        })
        actual_store = store_month[store_month["month"] == m].set_index("town")["revenue"]
        prev_store = store_month[store_month["month"] == m - pd.DateOffset(months=1)].set_index("town")["revenue"]
        for town in actual_store.index:
            store_rows.append({"month": m, "town": town, "actual": actual_store[town],
                               "Naive (last month)": prev_store[town],
                               "Random Forest (store panel)": rf_store[town]})
    return pd.DataFrame(chain_rows).set_index("month"), pd.DataFrame(store_rows)


def forecast_next_month(store_month: pd.DataFrame, model_name: str, rf_params: dict,
                        holt_damped: bool = True, target_month: pd.Timestamp = NEXT_MONTH):
    """Chain and store forecasts for the month after the data ends."""
    chain = store_month.groupby("month")["revenue"].sum()
    panel = build_panel(store_month, extra_months=[target_month])
    rf_store = random_forest_store_forecast(panel, target_month, rf_params)
    chain_forecasts = {
        "Naive (last month)": naive(chain),
        "Seasonal naive (last year)": seasonal_naive(chain, target_month),
        "Moving average (3 months)": moving_average(chain, 3),
        "Holt exponential smoothing": holt(chain, damped=holt_damped),
        "Random Forest (store panel)": rf_store.sum(),
    }
    return chain_forecasts[model_name], chain_forecasts, rf_store
