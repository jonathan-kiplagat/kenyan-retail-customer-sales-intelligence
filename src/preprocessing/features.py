"""Feature engineering: build the joined, analysis-ready sales dataset."""

import pandas as pd


def build_analytical_dataset(sales, customers, products, stores, calendar) -> pd.DataFrame:
    """One row per cleaned sales line, with product, store, customer and
    calendar attributes plus derived analytical features."""
    cal = calendar.copy()
    # A holiday eve is the day before a public holiday (stock-up shopping).
    cal["is_holiday_eve"] = cal["is_public_holiday"].shift(-1, fill_value=False)

    df = (sales
          .merge(products[["product_id", "product_name", "category", "brand"]], on="product_id", how="left")
          .merge(stores[["store_id", "store_name", "town", "county", "store_format"]], on="store_id", how="left")
          .merge(customers[["customer_id", "gender", "age_band", "home_county", "loyalty_member"]]
                 .rename(columns={"home_county": "customer_home_county"}), on="customer_id", how="left")
          .merge(cal[["date", "year", "quarter", "month", "month_name", "year_month", "iso_week",
                      "day_of_week", "day_of_week_num", "is_weekend", "is_payday_window",
                      "is_public_holiday", "holiday_name", "is_holiday_eve"]],
                 left_on="transaction_date", right_on="date", how="left")
          .drop(columns="date"))

    # Line-level features
    df["is_promo"] = df["promotion_id"].notna()
    df["is_walk_in"] = df["customer_id"].isna()
    df["profit_margin"] = (df["profit"] / df["total_amount"]).round(4)
    df["hour"] = pd.to_datetime(df["transaction_time"], format="%H:%M").dt.hour
    df["day_part"] = pd.cut(df["hour"], bins=[0, 11, 14, 17, 24], right=False,
                            labels=["Morning", "Midday", "Afternoon", "Evening"])

    # Order-level features (basket size and value, repeated on each line)
    order = df.groupby("order_id").agg(order_value=("total_amount", "sum"),
                                       order_lines=("transaction_id", "size"),
                                       order_units=("quantity", "sum"))
    df = df.merge(order, on="order_id", how="left")

    # Customer cohort = month of the customer's first purchase in the data
    first = df.groupby("customer_id")["transaction_date"].min().dt.to_period("M").astype(str)
    df["cohort_month"] = df["customer_id"].map(first)
    return df
