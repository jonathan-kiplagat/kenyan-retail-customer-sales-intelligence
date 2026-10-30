"""Inject a small, controlled and fully logged set of data-quality issues.

Why: real point-of-sale extracts are never perfectly clean. Milestone 2 must
find and fix these problems WITHOUT reading this file or the log; the log is
only used afterwards as an audit ("did the cleaning catch everything?").

Every change is written to docs/dq_injection_log.csv with the original value,
so the true (clean) value of every touched cell is known.
"""

import numpy as np
import pandas as pd

N_DUPLICATES = 12


def inject_quality_issues(tables: dict, rng: np.random.Generator):
    sales = tables["sales_transactions"].copy()
    products = tables["products"].copy()
    stores = tables["stores"].copy()
    customers = tables["customers"].copy()
    log = []

    def record(table, key, column, issue, original, injected):
        log.append({
            "table": table, "record_key": key, "column": column, "issue_type": issue,
            "original_value": original, "injected_value": injected,
        })

    # Text columns must hold strings like "KES 1,200.00" -> make them object dtype.
    for col in ["total_amount", "transaction_date", "payment_method", "customer_id"]:
        sales[col] = sales[col].astype(object)

    # Each issue uses its own rows so the problems do not overlap.
    pool = list(rng.permutation(sales.index))

    def take(n):
        return [pool.pop() for _ in range(n)]

    # 1) Missing customer IDs (receipt printed without scanning the loyalty card).
    for i in take(25):
        record("sales_transactions", sales.at[i, "transaction_id"], "customer_id",
               "missing_value", sales.at[i, "customer_id"], None)
        sales.at[i, "customer_id"] = np.nan

    # 2) Missing payment method (till did not capture the tender type).
    for i in take(10):
        record("sales_transactions", sales.at[i, "transaction_id"], "payment_method",
               "missing_value", sales.at[i, "payment_method"], None)
        sales.at[i, "payment_method"] = np.nan

    # 3) Inconsistent payment labels (manual entry at different tills).
    variants = {"M-Pesa": ["mpesa", "MPESA", "M-PESA", "m-pesa "],
                "Cash": ["cash", "CASH ", " Cash"],
                "Debit/Credit Card": ["Card", "card", "credit card"],
                "Bank Transfer": ["bank transfer", "Bank"]}
    for i in take(30):
        original = sales.at[i, "payment_method"]
        bad = rng.choice(variants[original])
        record("sales_transactions", sales.at[i, "transaction_id"], "payment_method",
               "inconsistent_label", original, bad)
        sales.at[i, "payment_method"] = bad

    # 4) Dates exported in day/month/year format from one older till.
    for i in take(15):
        original = sales.at[i, "transaction_date"]
        bad = pd.Timestamp(original).strftime("%d/%m/%Y")
        record("sales_transactions", sales.at[i, "transaction_id"], "transaction_date",
               "inconsistent_date_format", original, bad)
        sales.at[i, "transaction_date"] = bad

    # 5) Amounts stored as formatted text instead of numbers.
    for i in take(10):
        original = sales.at[i, "total_amount"]
        bad = f"KES {original:,.2f}"
        record("sales_transactions", sales.at[i, "transaction_id"], "total_amount",
               "numeric_stored_as_text", original, bad)
        sales.at[i, "total_amount"] = bad

    # 6) Quantity keyed as 999 (entry error). Totals are left as originally
    #    rung up, so quantity x price no longer reconciles with total_amount.
    cheap = [i for i in pool if sales.at[i, "unit_price"] < 1000][:4]
    for i in cheap:
        pool.remove(i)
        record("sales_transactions", sales.at[i, "transaction_id"], "quantity",
               "outlier_entry_error", sales.at[i, "quantity"], 999)
        sales.at[i, "quantity"] = 999

    # 7) Extra zero typed on the unit price; the till recomputed totals from it,
    #    so the row is internally consistent. Only a catalogue check reveals it.
    for i in take(3):
        original = sales.at[i, "unit_price"]
        bad = original * 10
        record("sales_transactions", sales.at[i, "transaction_id"], "unit_price",
               "price_typo", original, bad)
        gross = sales.at[i, "quantity"] * bad
        disc = round(gross * sales.at[i, "discount_percentage"] / 100, 2)
        sales.at[i, "unit_price"] = bad
        sales.at[i, "discount_amount"] = disc
        sales.at[i, "total_amount"] = round(gross - disc, 2)
        sales.at[i, "profit"] = round(gross - disc - sales.at[i, "quantity"] * sales.at[i, "unit_cost"], 2)

    # 8) total_amount saved without the discount (promo lines only).
    promo_rows = [i for i in pool if sales.at[i, "discount_percentage"] > 0][:6]
    for i in promo_rows:
        pool.remove(i)
        original = sales.at[i, "total_amount"]
        bad = round(sales.at[i, "quantity"] * sales.at[i, "unit_price"], 2)
        record("sales_transactions", sales.at[i, "transaction_id"], "total_amount",
               "calculation_mismatch", original, bad)
        sales.at[i, "total_amount"] = bad

    # 9) Exact duplicate rows (double-submitted receipts), placed right after
    #    the original. Taken from untouched rows so duplicates are exact copies.
    dup_idx = take(N_DUPLICATES)
    for i in dup_idx:
        record("sales_transactions", sales.at[i, "transaction_id"], "(entire row)",
               "duplicate_row", None, "row repeated")
    dups = sales.loc[dup_idx]
    sales = pd.concat([sales, dups]).sort_index(kind="stable").reset_index(drop=True)

    # 10) Dimension tables: inconsistent category / county / gender labels.
    for pid, bad in (("P007", "food & groceries"), ("P026", "Personal care ")):
        i = products.index[products["product_id"] == pid][0]
        record("products", pid, "category", "inconsistent_label", products.at[i, "category"], bad)
        products.at[i, "category"] = bad
    i = stores.index[stores["store_id"] == "S06"][0]
    record("stores", "S06", "county", "inconsistent_label", stores.at[i, "county"], " nakuru")
    stores.at[i, "county"] = " nakuru"
    for i in rng.choice(customers.index, size=8, replace=False):
        original = customers.at[i, "gender"]
        bad = {"Female": "F", "Male": "m"}[original]
        record("customers", customers.at[i, "customer_id"], "gender", "inconsistent_label", original, bad)
        customers.at[i, "gender"] = bad

    raw = dict(tables)
    raw.update(sales_transactions=sales, products=products, stores=stores, customers=customers)
    return raw, pd.DataFrame(log)
