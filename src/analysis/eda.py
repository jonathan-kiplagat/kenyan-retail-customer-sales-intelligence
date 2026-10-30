"""Reusable summary tables for exploratory data analysis (Milestone 3).

Every function takes the analytical dataset (data/processed/sales_analytical.csv)
and returns a tidy DataFrame, so the notebook only has to plot and interpret.
"""

import numpy as np
import pandas as pd

from src import config


def load_analytical() -> pd.DataFrame:
    return pd.read_csv(config.PROCESSED_DIR / "sales_analytical.csv", parse_dates=["transaction_date"])


def orders_table(sales: pd.DataFrame) -> pd.DataFrame:
    """One row per order (receipt). Average order value must be computed here,
    not on lines, otherwise multi-line baskets are split into small 'orders'."""
    return (sales.groupby("order_id")
            .agg(transaction_date=("transaction_date", "first"), town=("town", "first"),
                 customer_id=("customer_id", "first"), payment_method=("payment_method", "first"),
                 order_value=("total_amount", "sum"), order_profit=("profit", "sum"),
                 lines=("transaction_id", "size"), units=("quantity", "sum"))
            .reset_index())


def kpi_summary(sales: pd.DataFrame) -> pd.Series:
    orders = orders_table(sales)
    return pd.Series({
        "Net revenue (KES)": sales["total_amount"].sum(),
        "Gross profit (KES)": sales["profit"].sum(),
        "Gross margin": sales["profit"].sum() / sales["total_amount"].sum(),
        "Discounts given (KES)": sales["discount_amount"].sum(),
        "Orders": len(orders),
        "Units sold": sales["quantity"].sum(),
        "Identified customers": sales["customer_id"].nunique(),
        "Average order value (KES)": orders["order_value"].mean(),
        "Median order value (KES)": orders["order_value"].median(),
    })


def daily_orders_with_calendar(sales: pd.DataFrame) -> pd.DataFrame:
    """Orders per calendar day INCLUDING zero-order days, joined to calendar flags.

    Averaging per calendar day (not per order) is what makes 'busier on paydays'
    a fair comparison: there are fewer payday days than ordinary days.
    """
    cal = pd.read_csv(config.CLEANED_DIR / "calendar.csv", parse_dates=["date"])
    cal["is_holiday_eve"] = cal["is_public_holiday"].shift(-1, fill_value=False)
    per_day = orders_table(sales).groupby("transaction_date").size()
    cal["orders"] = per_day.reindex(cal["date"], fill_value=0).to_numpy()
    revenue = sales.groupby("transaction_date")["total_amount"].sum()
    cal["revenue"] = revenue.reindex(cal["date"], fill_value=0).to_numpy()
    return cal


def product_summary(sales: pd.DataFrame) -> pd.DataFrame:
    p = (sales.groupby(["product_id", "product_name", "category"])
         .agg(units=("quantity", "sum"), lines=("transaction_id", "size"),
              revenue=("total_amount", "sum"), profit=("profit", "sum"))
         .reset_index())
    p["margin"] = p["profit"] / p["revenue"]
    return p


def customer_summary(sales: pd.DataFrame, reference_date: str = config.END_DATE) -> pd.DataFrame:
    """Per-customer behaviour. Walk-in lines (no customer ID) are excluded."""
    known = sales[sales["customer_id"].notna()]
    c = (known.groupby("customer_id")
         .agg(orders=("order_id", "nunique"), spend=("total_amount", "sum"),
              profit=("profit", "sum"), first_purchase=("transaction_date", "min"),
              last_purchase=("transaction_date", "max"), loyalty_member=("loyalty_member", "first"),
              gender=("gender", "first"), age_band=("age_band", "first"))
         .reset_index())
    c["avg_order_value"] = c["spend"] / c["orders"]
    c["recency_days"] = (pd.Timestamp(reference_date) - c["last_purchase"]).dt.days
    return c


def cumulative_revenue_share(customers: pd.DataFrame) -> pd.DataFrame:
    """Pareto curve: share of revenue earned by the top x% of customers."""
    s = customers["spend"].sort_values(ascending=False).to_numpy()
    return pd.DataFrame({
        "customer_share": np.arange(1, len(s) + 1) / len(s),
        "revenue_share": np.cumsum(s) / s.sum(),
    })


def store_summary(sales: pd.DataFrame) -> pd.DataFrame:
    stores = pd.read_csv(config.CLEANED_DIR / "stores.csv")
    orders = orders_table(sales)
    s = (sales.groupby("town")
         .agg(revenue=("total_amount", "sum"), profit=("profit", "sum"),
              units=("quantity", "sum"), customers=("customer_id", "nunique"))
         .join(orders.groupby("town").agg(orders=("order_id", "size"),
                                          avg_order_value=("order_value", "mean")))
         .reset_index()
         .merge(stores[["town", "county", "store_format", "floor_area_sqm"]], on="town"))
    s["margin"] = s["profit"] / s["revenue"]
    s["revenue_share"] = s["revenue"] / s["revenue"].sum()
    s["revenue_per_sqm"] = s["revenue"] / s["floor_area_sqm"]
    return s.sort_values("revenue", ascending=False).reset_index(drop=True)


def promotion_performance(sales: pd.DataFrame, window_days: int = 28) -> pd.DataFrame:
    """Compare each campaign's target-category demand with a nearby baseline.

    Baseline = the same category on days within `window_days` before the start
    AND after the end of the campaign, excluding days when that category was on
    any promotion and days outside the study period. Using both sides avoids an
    empty baseline for campaigns at the very start of the data (January 2024).

    This is a descriptive before/after comparison, NOT a causal estimate:
    campaigns run in seasonal peaks (e.g. back-to-school), so part of any
    'lift' is seasonality.
    """
    promos = pd.read_csv(config.CLEANED_DIR / "promotions.csv", parse_dates=["start_date", "end_date"])
    start, end = pd.Timestamp(config.START_DATE), pd.Timestamp(config.END_DATE)
    days = pd.date_range(start, end, freq="D")
    rows = []
    for p in promos.itertuples():
        cat_sales = sales[sales["category"] == p.target_category]
        units_by_day = cat_sales.groupby("transaction_date")["quantity"].sum().reindex(days, fill_value=0)

        promo_days_for_cat = pd.DatetimeIndex([])
        for q in promos[promos["target_category"] == p.target_category].itertuples():
            promo_days_for_cat = promo_days_for_cat.union(pd.date_range(q.start_date, q.end_date))

        in_window = pd.date_range(p.start_date, p.end_date)
        before = pd.date_range(p.start_date - pd.Timedelta(days=window_days), p.start_date - pd.Timedelta(days=1))
        after = pd.date_range(p.end_date + pd.Timedelta(days=1), p.end_date + pd.Timedelta(days=window_days))
        baseline_days = before.union(after).difference(promo_days_for_cat)
        baseline_days = baseline_days[(baseline_days >= start) & (baseline_days <= end)]

        campaign_lines = cat_sales[cat_sales["promotion_id"] == p.promotion_id]
        rows.append({
            "promotion_id": p.promotion_id,
            "promotion_name": p.promotion_name,
            "year": p.start_date.year,
            "target_category": p.target_category,
            "discount_pct": p.discount_percentage,
            "days": len(in_window),
            "units_per_day_promo": units_by_day.loc[in_window].mean(),
            "units_per_day_baseline": units_by_day.loc[baseline_days].mean(),
            "promo_revenue": campaign_lines["total_amount"].sum(),
            "discount_cost": campaign_lines["discount_amount"].sum(),
            "promo_profit": campaign_lines["profit"].sum(),
        })
    out = pd.DataFrame(rows)
    out["unit_lift"] = out["units_per_day_promo"] / out["units_per_day_baseline"] - 1
    out["promo_margin"] = out["promo_profit"] / out["promo_revenue"]
    return out
