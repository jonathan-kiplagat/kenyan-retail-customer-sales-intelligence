"""Generate the synthetic Duka Bora retail dataset (Milestone 1).

Run from the project root:
    python -m src.data_generation.generate_data

Pipeline
    1. Build the calendar (joined to the verified public-holiday file).
    2. Compute a daily "shopping intensity" (seasonality, weekday, payday, holidays,
       promotions, growth).
    3. Create ~1,800 customers with hidden behaviour segments.
    4. Give each customer a number of orders and place them on dates.
    5. Fill every order with product lines (exactly 2,988 clean lines).
    6. Price the lines, apply promotions and choose payment methods.
    7. Inject a small, logged set of data-quality issues -> exactly 3,000 raw rows.
    8. Write the CSV files to data/raw/ and the audit log to docs/.

The output is fully reproducible because every random draw comes from one
NumPy Generator seeded with config.RANDOM_SEED.
"""

import numpy as np
import pandas as pd

from src import config
from src.data_generation import reference_data as ref
from src.data_generation.inject_quality_issues import inject_quality_issues

N_CUSTOMERS = 1800
TARGET_ORDERS = 2650
CLEAN_LINES = config.RAW_SALES_ROWS - 12  # 12 duplicate rows are added later

# Hidden behaviour segments: (share of customers, possible order counts).
# Not exported -- RFM analysis must rediscover these patterns from behaviour.
SEGMENTS = {
    "one_off": (0.78, [1]),
    "occasional": (0.13, [2]),
    "regular": (0.065, [3, 4, 5]),
    "loyal": (0.025, [6, 7, 8, 9, 10, 11]),
}

MONTH_FACTOR = {1: 0.85, 2: 0.90, 3: 0.95, 4: 1.05, 5: 0.95, 6: 0.95,
                7: 0.95, 8: 1.00, 9: 0.97, 10: 1.00, 11: 1.08, 12: 1.35}
WEEKDAY_FACTOR = {0: 0.85, 1: 0.85, 2: 0.90, 3: 0.95, 4: 1.10, 5: 1.30, 6: 1.05}

# Seasonal tilts on which categories end up in baskets.
CATEGORY_MONTH_TILT = {
    "Clothing": {1: 2.0, 4: 1.2, 5: 1.6, 9: 1.6, 12: 1.5},
    "Electronics": {11: 1.8, 12: 1.8},
    "Beverages": {1: 1.15, 2: 1.15, 3: 1.15, 12: 1.4},
    "Food and Groceries": {4: 1.15, 12: 1.15},
    "Household Products": {6: 1.1, 7: 1.1},
    "Personal Care": {2: 1.2},
}
CATEGORY_STORE_TILT = {
    "S02": {"Electronics": 1.6, "Personal Care": 1.25, "Clothing": 1.2, "Food and Groceries": 0.85},
    "S03": {"Food and Groceries": 1.2, "Electronics": 0.7},
    "S04": {"Beverages": 1.35},
    "S05": {"Food and Groceries": 1.1},
    "S06": {"Household Products": 1.15},
}
PROMO_CATEGORY_TILT = 1.7     # promoted category is more likely to be bought
PROMO_QUANTITY_LIFT = 1.3     # and bought in larger quantities

PAYMENT_BASE = {  # M-Pesa, Cash, Card, Bank Transfer
    "S01": [0.58, 0.18, 0.17, 0.07],
    "S02": [0.45, 0.10, 0.33, 0.12],
    "S03": [0.60, 0.28, 0.08, 0.04],
    "S04": [0.55, 0.22, 0.16, 0.07],
    "S05": [0.58, 0.26, 0.11, 0.05],
    "S06": [0.58, 0.23, 0.13, 0.06],
}
OPENING_HOURS = np.arange(7, 21)  # 07:00 - 20:59
HOUR_WEIGHTS = np.array([0.02, 0.04, 0.05, 0.06, 0.07, 0.09, 0.09,
                         0.07, 0.06, 0.07, 0.10, 0.11, 0.10, 0.07])


# ---------------------------------------------------------------------------
# 1. Calendar
# ---------------------------------------------------------------------------
def build_calendar(holidays: pd.DataFrame) -> pd.DataFrame:
    """One row per day of the study period with date attributes and holiday flags."""
    dates = pd.date_range(config.START_DATE, config.END_DATE, freq="D")
    cal = pd.DataFrame({"date": dates})
    cal["year"] = cal["date"].dt.year
    cal["quarter"] = cal["date"].dt.quarter
    cal["month"] = cal["date"].dt.month
    cal["month_name"] = cal["date"].dt.month_name()
    cal["year_month"] = cal["date"].dt.strftime("%Y-%m")
    cal["iso_week"] = cal["date"].dt.isocalendar().week.astype(int)
    cal["day_of_month"] = cal["date"].dt.day
    cal["day_of_week"] = cal["date"].dt.day_name()
    cal["day_of_week_num"] = cal["date"].dt.day_of_week + 1  # 1 = Monday
    cal["is_weekend"] = cal["day_of_week_num"] >= 6
    # Kenyan salaries are typically paid around month-end: 25th to the 3rd.
    cal["is_payday_window"] = (cal["day_of_month"] >= 25) | (cal["day_of_month"] <= 3)

    hol = holidays[["date", "holiday_name"]].copy()
    hol["date"] = pd.to_datetime(hol["date"])
    cal = cal.merge(hol, on="date", how="left")
    cal["is_public_holiday"] = cal["holiday_name"].notna()
    return cal


# ---------------------------------------------------------------------------
# 2. Daily shopping intensity
# ---------------------------------------------------------------------------
def daily_intensity(cal: pd.DataFrame, promotions: pd.DataFrame) -> np.ndarray:
    """Relative likelihood that an order happens on each calendar day."""
    days_elapsed = (cal["date"] - cal["date"].min()).dt.days.to_numpy()
    growth = 1 + 0.03 * days_elapsed / 365          # ~3% volume growth per year
    month = cal["month"].map(MONTH_FACTOR).to_numpy()
    weekday = (cal["day_of_week_num"] - 1).map(WEEKDAY_FACTOR).to_numpy()
    payday = np.where(cal["is_payday_window"], 1.20, 1.0)

    # Shoppers stock up the day before a holiday; holidays themselves are busy too.
    holiday = np.where(cal["is_public_holiday"], 1.10, 1.0)
    eve = np.where(cal["is_public_holiday"].shift(-1, fill_value=False), 1.25, 1.0)

    promo_active = np.zeros(len(cal), dtype=bool)
    for _, p in promotions.iterrows():
        promo_active |= cal["date"].between(p["start_date"], p["end_date"]).to_numpy()
    promo = np.where(promo_active, 1.10, 1.0)

    return growth * month * weekday * payday * holiday * eve * promo


# ---------------------------------------------------------------------------
# 3-4. Customers and their orders
# ---------------------------------------------------------------------------
def assign_order_counts(rng, segments: np.ndarray) -> np.ndarray:
    """Draw orders per customer from its segment, then nudge to TARGET_ORDERS."""
    counts = np.array([rng.choice(SEGMENTS[s][1]) for s in segments])
    repeaters = np.flatnonzero(counts >= 2)
    while counts.sum() != TARGET_ORDERS:
        i = rng.choice(repeaters)
        if counts.sum() > TARGET_ORDERS and counts[i] > 2:
            counts[i] -= 1
        elif counts.sum() < TARGET_ORDERS:
            counts[i] += 1
    return counts


def sample_dates(rng, intensity, lo, hi, k):
    """Pick k distinct day indices in [lo, hi] with probability ~ intensity."""
    window = np.arange(lo, hi + 1)
    weights = intensity[lo:hi + 1] / intensity[lo:hi + 1].sum()
    return np.sort(rng.choice(window, size=k, replace=False, p=weights))


def generate_customers_and_orders(rng, cal, intensity):
    n_days = len(cal)
    seg_names = list(SEGMENTS)
    seg_shares = [SEGMENTS[s][0] for s in seg_names]
    segments = rng.choice(seg_names, size=N_CUSTOMERS, p=seg_shares)
    order_counts = assign_order_counts(rng, segments)

    stores = ref.STORES
    preferred = rng.choice(stores["store_id"], size=N_CUSTOMERS, p=stores["traffic_weight"])
    last_start = cal.index[cal["date"] == "2025-09-30"][0]
    early_end = cal.index[cal["date"] == "2024-09-30"][0]

    order_rows, drifter_flags = [], []
    for c in range(N_CUSTOMERS):
        seg, k = segments[c], order_counts[c]
        drifter = False
        if k == 1:
            days = sample_dates(rng, intensity, 0, n_days - 1, 1)
        else:
            # Repeat customers may have joined up to six months BEFORE the study
            # period (negative start). Without this, activity piles up late in
            # 2025 and fakes a large growth trend.
            start_hi = early_end if seg == "loyal" else last_start
            start = max(int(rng.integers(-180, start_hi + 1)), 0)
            if seg in ("loyal", "regular") and rng.random() < 0.33:
                # "Drifting away": active for a while, then stops buying.
                drifter = True
                end = start + int(rng.integers(120, 361))
            elif seg == "occasional":
                end = start + int(rng.integers(30, 401))
            else:
                end = n_days - 1
            end = min(max(end, start + 2 * k), n_days - 1)  # window must fit k days
            days = sample_dates(rng, intensity, start, end, k)
        drifter_flags.append(drifter)
        for d in days:
            # Customers mostly shop at their home store.
            store = preferred[c] if rng.random() < 0.85 else rng.choice(
                stores["store_id"], p=stores["traffic_weight"])
            order_rows.append((c, seg, d, store))

    orders = pd.DataFrame(order_rows, columns=["cust_idx", "segment", "day_idx", "store_id"])
    orders["transaction_date"] = cal["date"].to_numpy()[orders["day_idx"]]

    hours = rng.choice(OPENING_HOURS, size=len(orders), p=HOUR_WEIGHTS / HOUR_WEIGHTS.sum())
    minutes = rng.integers(0, 60, size=len(orders))
    orders["transaction_time"] = [f"{h:02d}:{m:02d}" for h, m in zip(hours, minutes)]

    orders = orders.sort_values(["transaction_date", "transaction_time", "cust_idx"]).reset_index(drop=True)
    orders["order_id"] = [f"ORD{i:05d}" for i in range(1, len(orders) + 1)]

    customers = build_customer_table(rng, segments, preferred, orders)
    orders = orders.merge(customers[["cust_idx", "customer_id"]], on="cust_idx")
    return customers, orders.sort_values("order_id").reset_index(drop=True)


def build_customer_table(rng, segments, preferred, orders):
    """Customer attributes. Customer IDs are numbered in registration order."""
    first_purchase = orders.groupby("cust_idx")["transaction_date"].min()
    n = len(segments)
    store_county = ref.STORES.set_index("store_id")["county"]
    counties = ref.STORES["county"].unique()

    home_county = np.array([
        store_county[s] if rng.random() < 0.9 else rng.choice(counties) for s in preferred
    ])
    # 55% register at first purchase; the rest are older loyalty-card holders.
    first = first_purchase.reindex(range(n)).to_numpy()
    earliest = np.datetime64("2020-01-01")
    reg = []
    for fp in first:
        if rng.random() < 0.55:
            reg.append(fp)
        else:
            span = int((fp - earliest).astype("timedelta64[D]").astype(int))
            reg.append(earliest + np.timedelta64(int(rng.integers(0, max(span, 1))), "D"))
    loyalty_prob = {"one_off": 0.25, "occasional": 0.45, "regular": 0.70, "loyal": 0.90}

    customers = pd.DataFrame({
        "cust_idx": range(n),
        "gender": rng.choice(["Female", "Male"], size=n, p=[0.54, 0.46]),
        "age_band": rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"], size=n,
                               p=[0.18, 0.34, 0.25, 0.14, 0.09]),
        "home_county": home_county,
        "registration_date": pd.to_datetime(reg),
        "loyalty_member": [
            "Yes" if rng.random() < loyalty_prob[s] else "No" for s in segments
        ],
        "preferred_store_id": preferred,
    })
    customers = customers.sort_values(["registration_date", "cust_idx"]).reset_index(drop=True)
    customers["customer_id"] = [f"C{i:04d}" for i in range(1, n + 1)]
    return customers


# ---------------------------------------------------------------------------
# 5-6. Basket lines, prices, promotions, payments
# ---------------------------------------------------------------------------
def active_promotions(promotions, date):
    mask = (promotions["start_date"] <= date) & (promotions["end_date"] >= date)
    return promotions.loc[mask].set_index("target_category")


def lines_per_order(rng, orders):
    """Every order has >=1 line; extra lines go to bigger-basket orders."""
    basket = orders["store_id"].map(ref.STORES.set_index("store_id")["basket_factor"])
    seg_factor = orders["segment"].map({"one_off": 0.8, "occasional": 1.0, "regular": 1.3, "loyal": 1.6})
    weights = (basket * seg_factor).to_numpy()
    n_lines = np.ones(len(orders), dtype=int)
    extra = CLEAN_LINES - len(orders)
    while extra > 0:
        i = rng.choice(len(orders), p=weights / weights.sum())
        if n_lines[i] < 4:
            n_lines[i] += 1
            extra -= 1
    return n_lines


def generate_lines(rng, orders, promotions):
    products = ref.PRODUCTS
    by_cat = {c: products[products["category"] == c] for c in ref.CATEGORIES}
    n_lines = lines_per_order(rng, orders)
    rows = []
    for order, k in zip(orders.itertuples(index=False), n_lines):
        date = order.transaction_date
        promos = active_promotions(promotions, date)
        weights = []
        for cat in ref.CATEGORIES:
            w = ref.CATEGORY_BASE_WEIGHTS[cat]
            w *= CATEGORY_MONTH_TILT.get(cat, {}).get(date.month, 1.0)
            w *= CATEGORY_STORE_TILT.get(order.store_id, {}).get(cat, 1.0)
            if cat in promos.index:
                w *= PROMO_CATEGORY_TILT
            weights.append(w)
        weights = np.array(weights) / sum(weights)

        chosen = set()
        while len(chosen) < k:
            cat = rng.choice(ref.CATEGORIES, p=weights)
            pool = by_cat[cat]
            pid = rng.choice(pool["product_id"], p=pool["popularity"] / pool["popularity"].sum())
            if pid in chosen:
                continue
            chosen.add(pid)
            prod = pool.set_index("product_id").loc[pid]
            promo = promos.loc[cat] if cat in promos.index else None

            # Quantity = 1 + Poisson extra units; promotions lift the extra units.
            extra_mean = prod["mean_quantity"] - 1
            if promo is not None:
                extra_mean = extra_mean * PROMO_QUANTITY_LIFT + 0.3
            cap = {"Electronics": 2, "Clothing": 4}.get(cat, 12)
            qty = int(min(1 + rng.poisson(extra_mean), cap))
            rows.append({
                "order_id": order.order_id,
                "product_id": pid,
                "category": cat,
                "quantity": qty,
                "promotion_id": promo["promotion_id"] if promo is not None else None,
                "discount_rate": promo["discount_percentage"] if promo is not None else 0.0,
            })
    return pd.DataFrame(rows)


def add_bulk_purchases(lines):
    """Two GENUINE bulk purchases (e.g. a school and a church event).

    These are legitimate high-quantity outliers that Milestone 2 must
    investigate and keep -- unlike the injected quantity=999 entry errors.
    """
    for pid, qty in (("P011", 60), ("P004", 48)):
        idx = lines.index[lines["product_id"] == pid][10]  # an arbitrary but fixed line
        lines.loc[idx, "quantity"] = qty
    return lines


def price_lines(lines, orders):
    prod = ref.PRODUCTS.set_index("product_id")
    lines = lines.merge(orders[["order_id", "transaction_date"]], on="order_id")
    uplift = np.where(lines["transaction_date"] >= ref.PRICE_REVIEW_DATE, 1 + ref.PRICE_REVIEW_UPLIFT, 1.0)
    lines["unit_price"] = np.round(lines["product_id"].map(prod["selling_price_kes"]) * uplift)
    lines["unit_cost"] = np.round(lines["product_id"].map(prod["unit_cost_kes"]) * uplift, 2)

    gross = lines["quantity"] * lines["unit_price"]
    lines["discount_percentage"] = lines["discount_rate"] * 100
    lines["discount_amount"] = np.round(gross * lines["discount_rate"], 2)
    lines["total_amount"] = np.round(gross - lines["discount_amount"], 2)
    lines["profit"] = np.round(lines["total_amount"] - lines["quantity"] * lines["unit_cost"], 2)
    return lines.drop(columns=["transaction_date"])


def choose_payments(rng, orders, lines):
    """One payment method per order, depending on store and basket value."""
    order_value = lines.groupby("order_id")["total_amount"].sum()
    methods = []
    for order in orders.itertuples(index=False):
        p = np.array(PAYMENT_BASE[order.store_id], dtype=float)
        value = order_value[order.order_id]
        if value >= 10_000:            # big tickets: card / bank transfer
            p *= [1.0, 0.3, 1.8, 4.0]
        elif value < 500:              # small change: more cash
            p *= [1.0, 1.5, 0.7, 0.2]
        methods.append(rng.choice(ref.PAYMENT_METHODS, p=p / p.sum()))
    return pd.Series(methods, index=orders["order_id"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
SALES_COLUMNS = [
    "transaction_id", "order_id", "transaction_date", "transaction_time",
    "customer_id", "store_id", "product_id", "quantity", "unit_price",
    "unit_cost", "discount_percentage", "discount_amount", "total_amount",
    "profit", "payment_method", "promotion_id",
]


def generate_clean_dataset(seed: int = config.RANDOM_SEED) -> dict:
    """Return all tables before any data-quality issues are injected."""
    rng = np.random.default_rng(seed)
    holidays = pd.read_csv(config.EXTERNAL_DIR / "kenya_public_holidays_2024_2025.csv")
    promotions = ref.PROMOTIONS.copy()
    promotions[["start_date", "end_date"]] = promotions[["start_date", "end_date"]].apply(pd.to_datetime)

    cal = build_calendar(holidays)
    intensity = daily_intensity(cal, promotions)
    customers, orders = generate_customers_and_orders(rng, cal, intensity)
    lines = generate_lines(rng, orders, promotions)
    lines = add_bulk_purchases(lines)
    lines = price_lines(lines, orders)
    orders["payment_method"] = orders["order_id"].map(choose_payments(rng, orders, lines))

    sales = lines.merge(
        orders[["order_id", "transaction_date", "transaction_time", "customer_id",
                "store_id", "payment_method"]],
        on="order_id",
    ).sort_values(["order_id", "product_id"]).reset_index(drop=True)
    sales["transaction_id"] = [f"TXN{i:05d}" for i in range(1, len(sales) + 1)]
    sales["transaction_date"] = sales["transaction_date"].dt.strftime("%Y-%m-%d")

    promotions_out = ref.PROMOTIONS.copy()
    promotions_out["discount_percentage"] = promotions_out["discount_percentage"] * 100

    return {
        "sales_transactions": sales[SALES_COLUMNS],
        "customers": customers[["customer_id", "gender", "age_band", "home_county",
                                "registration_date", "loyalty_member", "preferred_store_id"]]
        .assign(registration_date=lambda d: d["registration_date"].dt.strftime("%Y-%m-%d")),
        "products": ref.PRODUCTS.drop(columns=["popularity", "mean_quantity"]),
        "stores": ref.STORES.drop(columns=["traffic_weight", "basket_factor"]),
        "promotions": promotions_out,
        "calendar": cal.assign(date=cal["date"].dt.strftime("%Y-%m-%d")),
    }


def main():
    rng_issues = np.random.default_rng(config.RANDOM_SEED + 1)
    tables = generate_clean_dataset()
    raw_tables, issue_log = inject_quality_issues(tables, rng_issues)

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in raw_tables.items():
        df.to_csv(config.RAW_DIR / f"{name}.csv", index=False)
    issue_log.to_csv(config.DOCS_DIR / "dq_injection_log.csv", index=False)

    sales = raw_tables["sales_transactions"]
    print(f"Raw sales rows written: {len(sales):,}")
    for name, df in raw_tables.items():
        print(f"  {name:<20} {len(df):>6,} rows")
    print(f"Injected issues logged: {len(issue_log)} -> docs/dq_injection_log.csv")


if __name__ == "__main__":
    main()
