"""Reproducible cleaning pipeline (Milestone 2).

Run from the project root:
    python -m src.preprocessing.pipeline

Reads data/raw/, writes cleaned tables to data/cleaned/ and the joined
analytical dataset to data/processed/sales_analytical.csv. The notebook
03_data_cleaning.ipynb walks through the same steps one at a time.
"""

import pandas as pd

from src import config
from src.preprocessing import cleaning as cl
from src.preprocessing.features import build_analytical_dataset

TABLES = ["sales_transactions", "customers", "products", "stores", "promotions", "calendar"]

SALES_COLUMNS = [
    "transaction_id", "order_id", "transaction_date", "transaction_time", "customer_id",
    "store_id", "product_id", "quantity", "unit_price", "unit_cost", "gross_amount",
    "discount_percentage", "discount_amount", "total_amount", "cost_amount", "profit",
    "payment_method", "promotion_id", "is_walk_in",
]


def load_raw() -> dict:
    return {t: pd.read_csv(config.RAW_DIR / f"{t}.csv") for t in TABLES}


def clean_dimensions(raw: dict) -> dict:
    customers = raw["customers"].copy()
    customers["gender"] = cl.standardise_gender(customers["gender"])
    customers["registration_date"] = pd.to_datetime(customers["registration_date"], format="%Y-%m-%d")

    products = raw["products"].copy()
    products["category"] = cl.standardise_category(products["category"])

    stores = raw["stores"].copy()
    stores["county"] = stores["county"].str.strip().str.title()
    stores["opening_date"] = pd.to_datetime(stores["opening_date"], format="%Y-%m-%d")

    promotions = raw["promotions"].copy()
    for col in ["start_date", "end_date"]:
        promotions[col] = pd.to_datetime(promotions[col], format="%Y-%m-%d")

    calendar = raw["calendar"].copy()
    calendar["date"] = pd.to_datetime(calendar["date"], format="%Y-%m-%d")
    return {"customers": customers, "products": products, "stores": stores,
            "promotions": promotions, "calendar": calendar}


def clean_sales(raw_sales: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply the sales cleaning steps in a fixed order; return data + step counts."""
    steps = {}
    s = raw_sales.drop_duplicates().reset_index(drop=True)
    steps["exact_duplicates_removed"] = len(raw_sales) - len(s)

    s["transaction_date"] = cl.parse_mixed_dates(s["transaction_date"])
    s["total_amount"] = cl.parse_amount(s["total_amount"])

    labels_before = s["payment_method"].copy()
    s["payment_method"] = cl.standardise_payment(s["payment_method"])
    steps["payment_labels_standardised"] = int((labels_before != s["payment_method"]).sum()
                                               - labels_before.isna().sum())

    s, steps["payment_filled_from_same_order"] = cl.fill_from_same_order(s, "payment_method")
    steps["payment_set_unknown"] = int(s["payment_method"].isna().sum())
    s["payment_method"] = s["payment_method"].fillna("Unknown")

    s, steps["customer_filled_from_same_order"] = cl.fill_from_same_order(s, "customer_id")
    s["is_walk_in"] = s["customer_id"].isna()
    steps["customer_left_blank_walk_in"] = int(s["is_walk_in"].sum())

    # Quantity first: it needs the ORIGINAL recorded total as evidence.
    s, qty_report = cl.fix_quantity_entry_errors(s)
    steps["quantity_entry_errors_fixed"] = len(qty_report)
    s, price_report = cl.fix_price_typos(s)
    steps["price_typos_fixed"] = len(price_report)

    steps["rows_reconciling_before_recalc"] = int((cl.reconciliation_gap(s).abs() <= 0.01).sum())
    s = cl.recalculate_financials(s)
    steps["rows_recalculated_total_changed"] = int(len(s) - steps["rows_reconciling_before_recalc"])
    return s[SALES_COLUMNS], steps


def run() -> dict:
    raw = load_raw()
    dims = clean_dimensions(raw)
    sales, steps = clean_sales(raw["sales_transactions"])
    analytical = build_analytical_dataset(sales, dims["customers"], dims["products"],
                                          dims["stores"], dims["calendar"])

    config.CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    sales.to_csv(config.CLEANED_DIR / "sales_transactions.csv", index=False, date_format="%Y-%m-%d")
    for name, df in dims.items():
        df.to_csv(config.CLEANED_DIR / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    analytical.to_csv(config.PROCESSED_DIR / "sales_analytical.csv", index=False, date_format="%Y-%m-%d")
    return {"sales": sales, "analytical": analytical, "steps": steps, **dims}


if __name__ == "__main__":
    result = run()
    print(f"Cleaned sales rows: {len(result['sales']):,}")
    for step, n in result["steps"].items():
        print(f"  {step:<36} {n}")
