"""Export a star-schema data model for the Power BI dashboard (Milestone 7).

Run from the project root (after notebooks 03-07 have produced their outputs):
    python -m src.visualization.powerbi_export

Writes data/powerbi/:
    fact_sales.csv        one row per sales line (the fact table)
    dim_date.csv          calendar (mark as date table in Power BI)
    dim_store.csv, dim_product.csv
    dim_customer.csv      attributes + RFM scores/segment + at-risk flag + model score
    fact_forecast.csv     monthly actual vs forecasts, Jan 2026 forecast and ranges
    forecast_store_jan2026.csv
    cohort_retention.csv  quarterly cohort retention (long format, for a matrix visual)
    model_metrics.csv     test-period accuracy of every model
"""

import numpy as np
import pandas as pd

from src import config
from src.analysis import eda

OUT_DIR = config.DATA_DIR / "powerbi"
ANALYSIS_DATE = pd.Timestamp(config.END_DATE)


def ntile(values: pd.Series, n: int) -> pd.Series:
    """Replicate SQL NTILE(n) OVER (ORDER BY value): equal-sized buckets 1..n,
    earlier buckets one larger when the rows do not divide evenly."""
    order = values.sort_values(kind="stable").index
    size, extra = divmod(len(values), n)
    buckets = np.concatenate([[b + 1] * (size + (1 if b < extra else 0)) for b in range(n)])
    return pd.Series(buckets, index=order).reindex(values.index)


def rfm_table(sales: pd.DataFrame) -> pd.DataFrame:
    """Same rules as sql/07_rfm_analysis.sql (fixed R and F bands, M quintiles)."""
    c = eda.customer_summary(sales, reference_date=config.END_DATE)
    c = c.sort_values("customer_id").reset_index(drop=True)
    c["r_score"] = pd.cut(c["recency_days"], [-1, 90, 180, 365, 545, np.inf], labels=[5, 4, 3, 2, 1]).astype(int)
    c["f_score"] = pd.cut(c["orders"], [0, 1, 2, 3, 5, np.inf], labels=[1, 2, 3, 4, 5]).astype(int)
    c["m_score"] = ntile(c["spend"], 5)

    def segment(r):
        if r.r_score >= 4:
            return {5: "Champions", 4: "Champions", 3: "Loyal Customers",
                    2: "Potential Loyalists", 1: "New / Recent One-off"}[r.f_score]
        if r.f_score >= 4 and r.m_score == 5:
            return "Cannot Lose Them"
        if r.f_score >= 3:
            return "At Risk"
        return {3: "Needs Attention", 2: "Hibernating", 1: "Lost"}[r.r_score]

    c["rfm_segment"] = c.apply(segment, axis=1)
    c["rfm_code"] = c["r_score"].astype(str) + c["f_score"].astype(str) + c["m_score"].astype(str)
    return c


def cohort_retention(sales: pd.DataFrame) -> pd.DataFrame:
    known = sales[sales["customer_id"].notna()].copy()
    known["quarter"] = known["transaction_date"].dt.to_period("Q")
    first = known.groupby("customer_id")["quarter"].min().rename("cohort")
    act = known[["customer_id", "quarter"]].drop_duplicates().join(first, on="customer_id")
    act["quarters_since_first"] = (act["quarter"] - act["cohort"]).apply(lambda x: x.n)
    sizes = first.value_counts().rename("cohort_size")
    out = (act.groupby(["cohort", "quarters_since_first"])["customer_id"].nunique().rename("active_customers")
           .reset_index().join(sizes, on="cohort"))
    out["retention_pct"] = out["active_customers"] / out["cohort_size"]
    out["cohort"] = out["cohort"].astype(str)
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sales = eda.load_analytical()

    fact = sales[["transaction_id", "order_id", "transaction_date", "hour", "day_part", "customer_id", "store_id",
                  "product_id", "promotion_id", "payment_method", "quantity", "unit_price", "gross_amount",
                  "discount_amount", "total_amount", "cost_amount", "profit", "is_promo", "is_walk_in"]]
    fact = fact.rename(columns={"transaction_date": "date", "total_amount": "net_revenue"})
    fact.to_csv(OUT_DIR / "fact_sales.csv", index=False, date_format="%Y-%m-%d")

    cal = pd.read_csv(config.CLEANED_DIR / "calendar.csv", parse_dates=["date"])
    cal["month_start"] = cal["date"].dt.to_period("M").dt.to_timestamp()
    cal["month_short"] = cal["date"].dt.strftime("%b")
    cal["year_quarter"] = cal["year"].astype(str) + "-Q" + cal["quarter"].astype(str)
    cal.to_csv(OUT_DIR / "dim_date.csv", index=False, date_format="%Y-%m-%d")

    pd.read_csv(config.CLEANED_DIR / "stores.csv").to_csv(OUT_DIR / "dim_store.csv", index=False)
    pd.read_csv(config.CLEANED_DIR / "products.csv").to_csv(OUT_DIR / "dim_product.csv", index=False)

    customers = pd.read_csv(config.CLEANED_DIR / "customers.csv")
    rfm = rfm_table(sales)[["customer_id", "orders", "spend", "first_purchase", "last_purchase", "recency_days",
                            "r_score", "f_score", "m_score", "rfm_code", "rfm_segment"]]
    risk = pd.read_csv(config.PROCESSED_DIR / "customer_risk_scores.csv")[
        ["customer_id", "at_risk_rule", "model_churn_probability", "risk_band"]]
    dim_customer = (customers.merge(rfm, on="customer_id", how="left").merge(risk, on="customer_id", how="left")
                    .rename(columns={"spend": "lifetime_spend_kes"}))
    dim_customer["customer_status"] = np.select(
        [dim_customer["orders"].isna(), dim_customer["at_risk_rule"] == 1, dim_customer["orders"] >= 2],
        ["Walk-in only (no identified orders)", "At risk (silent > 180 days)", "Active established"],
        default="One-off buyer")
    # Whole-number columns stay integers (nullable Int64) despite blanks for walk-in-only customers.
    for col in ["orders", "recency_days", "r_score", "f_score", "m_score", "at_risk_rule"]:
        dim_customer[col] = dim_customer[col].astype("Int64")
    stores = pd.read_csv(config.CLEANED_DIR / "stores.csv")
    dim_customer["preferred_store"] = dim_customer["preferred_store_id"].map(stores.set_index("store_id")["town"])
    dim_customer.to_csv(OUT_DIR / "dim_customer.csv", index=False, date_format="%Y-%m-%d")

    forecast = pd.read_csv(config.PROCESSED_DIR / "forecast_monthly.csv", parse_dates=["month"])
    forecast.to_csv(OUT_DIR / "fact_forecast.csv", index=False, date_format="%Y-%m-%d")
    pd.read_csv(config.PROCESSED_DIR / "forecast_jan2026_by_store.csv").to_csv(
        OUT_DIR / "forecast_store_jan2026.csv", index=False)
    cohort_retention(sales).to_csv(OUT_DIR / "cohort_retention.csv", index=False)
    pd.read_csv(config.REPORTS_DIR / "model_metrics.csv").to_csv(OUT_DIR / "model_metrics.csv", index=False)

    for f in sorted(OUT_DIR.glob("*.csv")):
        print(f"  {f.name:<28} {sum(1 for _ in open(f, encoding='utf-8')) - 1:>6,} rows")
    return dim_customer


if __name__ == "__main__":
    main()
