"""Cleaning and validation functions for Milestone 2.

Each function does ONE job and returns a new DataFrame (inputs are never
modified in place), so every step can be shown and explained in the notebook.

Guiding rules
- Never delete or impute silently: every fix is counted and reported.
- Recover missing values only from evidence inside the data (e.g. another
  line of the same receipt). Otherwise keep them blank and flag them.
- Derived money columns are recalculated from the base fields
  (quantity, unit_price, unit_cost, discount_percentage) so there is a single
  source of truth.
"""

import numpy as np
import pandas as pd

CATEGORIES = ["Food and Groceries", "Beverages", "Household Products",
              "Personal Care", "Clothing", "Electronics"]
PAYMENT_METHODS = ["M-Pesa", "Cash", "Debit/Credit Card", "Bank Transfer"]

# Every raw spelling seen during inspection -> one standard label.
PAYMENT_MAP = {
    "mpesa": "M-Pesa", "m-pesa": "M-Pesa",
    "cash": "Cash",
    "card": "Debit/Credit Card", "credit card": "Debit/Credit Card",
    "debit/credit card": "Debit/Credit Card",
    "bank": "Bank Transfer", "bank transfer": "Bank Transfer",
}
GENDER_MAP = {"f": "Female", "female": "Female", "m": "Male", "male": "Male"}


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------
def reconciliation_gap(sales: pd.DataFrame) -> pd.Series:
    """Recorded total minus the total implied by quantity, price and discount."""
    total = pd.to_numeric(sales["total_amount"], errors="coerce")
    expected = sales["quantity"] * sales["unit_price"] * (1 - sales["discount_percentage"] / 100)
    return total - expected


def sales_quality_profile(sales: pd.DataFrame) -> pd.Series:
    """Key data-quality metrics for the sales table (used before AND after)."""
    iso_dates = pd.to_datetime(sales["transaction_date"], format="%Y-%m-%d", errors="coerce")
    numeric_total = pd.to_numeric(sales["total_amount"], errors="coerce")
    return pd.Series({
        "rows": len(sales),
        "exact_duplicate_rows": int(sales.duplicated().sum()),
        "duplicate_transaction_ids": int(sales["transaction_id"].duplicated().sum()),
        "missing_customer_id": int(sales["customer_id"].isna().sum()),
        "missing_payment_method": int(sales["payment_method"].isna().sum()),
        "non_standard_payment_labels": int((~sales["payment_method"].isin(PAYMENT_METHODS + ["Unknown"])
                                            & sales["payment_method"].notna()).sum()),
        "dates_not_in_iso_format": int(iso_dates.isna().sum()),
        "total_amount_not_numeric": int(numeric_total.isna().sum()),
        "rows_failing_reconciliation": int((reconciliation_gap(sales).abs() > 0.01).sum()),
        "quantity_above_100": int((sales["quantity"] > 100).sum()),
    })


# ---------------------------------------------------------------------------
# Type fixes
# ---------------------------------------------------------------------------
def parse_mixed_dates(series: pd.Series) -> pd.Series:
    """Parse ISO dates (YYYY-MM-DD) and the day-first DD/MM/YYYY variant.

    The two formats are parsed explicitly rather than letting pandas guess,
    because guessing can silently swap day and month (03/04 -> 4 March?).
    """
    iso = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
    day_first = pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")
    parsed = iso.fillna(day_first)
    unparsed = parsed.isna() & series.notna()
    if unparsed.any():
        raise ValueError(f"Unrecognised date values: {series[unparsed].unique()[:5]}")
    return parsed


def parse_amount(series: pd.Series) -> pd.Series:
    """'KES 1,234.50' -> 1234.5 ; numbers pass through unchanged."""
    cleaned = (series.astype(str)
               .str.replace("KES", "", regex=False)
               .str.replace(",", "", regex=False)
               .str.strip())
    return pd.to_numeric(cleaned, errors="raise")


# ---------------------------------------------------------------------------
# Label standardisation
# ---------------------------------------------------------------------------
def standardise_payment(series: pd.Series) -> pd.Series:
    key = series.str.strip().str.lower()
    mapped = key.map(PAYMENT_MAP)
    unknown = mapped.isna() & series.notna()
    if unknown.any():
        raise ValueError(f"Unmapped payment labels: {series[unknown].unique()}")
    return mapped


def standardise_category(series: pd.Series) -> pd.Series:
    """Match labels to the 6 official categories ignoring case, spaces and '&'."""
    def key(text):
        return " ".join(str(text).lower().replace("&", "and").split())
    lookup = {key(c): c for c in CATEGORIES}
    mapped = series.map(lambda v: lookup.get(key(v)))
    if mapped.isna().any():
        raise ValueError(f"Unmapped categories: {series[mapped.isna()].unique()}")
    return mapped


def standardise_gender(series: pd.Series) -> pd.Series:
    return series.str.strip().str.lower().map(GENDER_MAP)


# ---------------------------------------------------------------------------
# Missing values recovered from the same receipt
# ---------------------------------------------------------------------------
def fill_from_same_order(sales: pd.DataFrame, column: str) -> tuple[pd.DataFrame, int]:
    """Fill blanks with the value on another line of the same order.

    Justification: payment method and customer are captured once per receipt,
    so every line of an order must share them. Returns (data, cells filled).
    """
    out = sales.copy()
    order_value = out.groupby("order_id")[column].transform(
        lambda s: s.dropna().iloc[0] if s.notna().any() else np.nan)
    to_fill = out[column].isna() & order_value.notna()
    out.loc[to_fill, column] = order_value[to_fill]
    return out, int(to_fill.sum())


# ---------------------------------------------------------------------------
# Value errors
# ---------------------------------------------------------------------------
def modal_price_by_product_year(sales: pd.DataFrame) -> pd.Series:
    """Most common unit price per (product, year): the 'shelf price' evidence."""
    year = sales["transaction_date"].dt.year
    return sales.groupby([sales["product_id"], year])["unit_price"].agg(lambda s: s.mode().iloc[0])


def fix_price_typos(sales: pd.DataFrame, tolerance: float = 0.5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replace unit prices far from the product's usual shelf price that year.

    A price more than 50% away from the mode is not a plausible discount or
    price change (promotions are captured separately in discount_percentage).
    """
    out = sales.copy()
    modal = modal_price_by_product_year(out)
    keys = list(zip(out["product_id"], out["transaction_date"].dt.year))
    expected = pd.Series([modal[k] for k in keys], index=out.index)
    deviation = (out["unit_price"] - expected).abs() / expected
    bad = deviation > tolerance
    report = out.loc[bad, ["transaction_id", "product_id", "unit_price"]].assign(
        shelf_price=expected[bad], ratio=(out.loc[bad, "unit_price"] / expected[bad]).round(2))
    out.loc[bad, "unit_price"] = expected[bad]
    return out, report


def fix_quantity_entry_errors(sales: pd.DataFrame, threshold: int = 100) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Restore keyed-in quantities that contradict the receipt total.

    Rule: quantity above `threshold` AND the recorded total implies a different
    whole-number quantity -> the quantity was mistyped; use the implied one.
    Large quantities that DO reconcile with the total are genuine bulk buys
    and are left untouched.
    """
    out = sales.copy()
    net_price = out["unit_price"] * (1 - out["discount_percentage"] / 100)
    implied = out["total_amount"] / net_price
    is_whole = (implied - implied.round()).abs() < 0.01
    bad = (out["quantity"] > threshold) & is_whole & (implied.round() != out["quantity"])
    report = out.loc[bad, ["transaction_id", "product_id", "quantity", "total_amount"]].assign(
        implied_quantity=implied[bad].round().astype(int))
    out.loc[bad, "quantity"] = implied[bad].round().astype(int)
    return out, report


def recalculate_financials(sales: pd.DataFrame) -> pd.DataFrame:
    """Rebuild every derived money column from the base fields."""
    out = sales.copy()
    gross = out["quantity"] * out["unit_price"]
    out["gross_amount"] = gross.round(2)
    out["discount_amount"] = (gross * out["discount_percentage"] / 100).round(2)
    out["total_amount"] = (gross - out["discount_amount"]).round(2)
    out["cost_amount"] = (out["quantity"] * out["unit_cost"]).round(2)
    out["profit"] = (out["total_amount"] - out["cost_amount"]).round(2)
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def check_foreign_keys(sales, customers, products, stores, promotions) -> pd.DataFrame:
    checks = [("customer_id", customers, "customer_id"), ("product_id", products, "product_id"),
              ("store_id", stores, "store_id"), ("promotion_id", promotions, "promotion_id")]
    rows = []
    for fk, table, pk in checks:
        values = sales[fk].dropna()
        rows.append({"foreign_key": fk, "checked": len(values), "blank": int(sales[fk].isna().sum()),
                     "unmatched": int((~values.isin(table[pk])).sum())})
    return pd.DataFrame(rows)


def check_order_consistency(sales: pd.DataFrame) -> pd.Series:
    """Every line of an order must share date, store, customer and payment."""
    cols = ["transaction_date", "store_id", "customer_id", "payment_method"]
    n_unique = sales.groupby("order_id")[cols].nunique(dropna=True)
    return (n_unique > 1).sum()


def check_promotions(sales: pd.DataFrame, promotions: pd.DataFrame) -> pd.Series:
    """Promo lines must fall inside the campaign window, match its discount
    and belong to its target category; non-promo lines must have 0% discount."""
    promo = sales.merge(promotions, on="promotion_id", how="inner", suffixes=("", "_promo"))
    return pd.Series({
        "promo_lines": len(promo),
        "outside_campaign_window": int((~promo["transaction_date"].between(
            promo["start_date"], promo["end_date"])).sum()),
        "discount_differs_from_campaign": int(
            (promo["discount_percentage"] != promo["discount_percentage_promo"]).sum()),
        "wrong_category": int((promo["category"] != promo["target_category"]).sum()),
        "discount_without_promotion": int(
            ((sales["promotion_id"].isna()) & (sales["discount_percentage"] > 0)).sum()),
    })
