"""Quality-assurance checks on the generated raw data (Milestone 1).

Run from the project root:  python -m pytest -q
"""

import pandas as pd
import pytest

from src import config
from src.data_generation.generate_data import generate_clean_dataset


@pytest.fixture(scope="module")
def raw():
    names = ["sales_transactions", "customers", "products", "stores", "promotions", "calendar"]
    return {n: pd.read_csv(config.RAW_DIR / f"{n}.csv") for n in names}


@pytest.fixture(scope="module")
def clean():
    return generate_clean_dataset()


def test_raw_sales_has_exactly_3000_rows(raw):
    assert len(raw["sales_transactions"]) == config.RAW_SALES_ROWS


def test_dimension_sizes(raw):
    assert len(raw["products"]) == 40
    assert len(raw["stores"]) == 6
    assert len(raw["calendar"]) == 731
    assert len(raw["customers"]) == pytest.approx(1800, rel=0.05)
    # Categories are unique after trimming/case-fixing the injected label issues.
    assert raw["products"]["category"].str.strip().str.lower().replace(
        {"food & groceries": "food and groceries"}).nunique() == 6


def test_foreign_keys_resolve(raw):
    s = raw["sales_transactions"]
    assert s["store_id"].isin(raw["stores"]["store_id"]).all()
    assert s["product_id"].isin(raw["products"]["product_id"]).all()
    assert s["promotion_id"].dropna().isin(raw["promotions"]["promotion_id"]).all()
    assert s["customer_id"].dropna().isin(raw["customers"]["customer_id"]).all()


def test_payment_methods_cover_requirement(clean):
    methods = set(clean["sales_transactions"]["payment_method"])
    assert methods == {"M-Pesa", "Cash", "Debit/Credit Card", "Bank Transfer"}


def test_study_period(clean):
    dates = pd.to_datetime(clean["sales_transactions"]["transaction_date"])
    assert dates.min() >= pd.Timestamp(config.START_DATE)
    assert dates.max() <= pd.Timestamp(config.END_DATE)


def test_clean_financials_reconcile(clean):
    s = clean["sales_transactions"]
    gross = s["quantity"] * s["unit_price"]
    assert (abs(gross * s["discount_percentage"] / 100 - s["discount_amount"]) < 0.01).all()
    assert (abs(gross - s["discount_amount"] - s["total_amount"]) < 0.01).all()
    assert (abs(s["total_amount"] - s["quantity"] * s["unit_cost"] - s["profit"]) < 0.01).all()


def test_generator_is_reproducible(clean):
    again = generate_clean_dataset()
    pd.testing.assert_frame_equal(clean["sales_transactions"], again["sales_transactions"])


def test_injected_issues_are_logged(raw):
    log = pd.read_csv(config.DOCS_DIR / "dq_injection_log.csv")
    dup_logged = (log["issue_type"] == "duplicate_row").sum()
    assert raw["sales_transactions"].duplicated().sum() == dup_logged == 12
