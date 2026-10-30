"""Checks on the cleaned data produced by src/preprocessing/pipeline.py."""

import pandas as pd
import pytest

from src.preprocessing import cleaning as cl
from src.preprocessing.pipeline import run


@pytest.fixture(scope="module")
def result():
    return run()


def test_duplicates_removed(result):
    sales = result["sales"]
    assert len(sales) == 2988
    assert not sales.duplicated().any()
    assert sales["transaction_id"].is_unique


def test_labels_are_standard(result):
    assert set(result["sales"]["payment_method"]) <= set(cl.PAYMENT_METHODS) | {"Unknown"}
    assert set(result["products"]["category"]) == set(cl.CATEGORIES)
    assert set(result["customers"]["gender"]) == {"Female", "Male"}
    assert result["stores"]["county"].str.strip().eq(result["stores"]["county"]).all()


def test_types(result):
    sales = result["sales"]
    assert pd.api.types.is_datetime64_any_dtype(sales["transaction_date"])
    assert pd.api.types.is_numeric_dtype(sales["total_amount"])


def test_foreign_keys(result):
    fk = cl.check_foreign_keys(result["sales"], result["customers"], result["products"],
                               result["stores"], result["promotions"])
    assert fk["unmatched"].sum() == 0


def test_financials_reconcile(result):
    s = result["sales"]
    assert (cl.reconciliation_gap(s).abs() <= 0.01).all()
    assert ((s["total_amount"] - s["cost_amount"] - s["profit"]).abs() <= 0.01).all()


def test_no_entry_error_quantities(result):
    assert result["sales"]["quantity"].max() < 100


def test_orders_are_consistent(result):
    assert cl.check_order_consistency(result["sales"]).sum() == 0


def test_promotions_valid(result):
    s = result["analytical"]
    checks = cl.check_promotions(s, result["promotions"])
    assert checks.drop("promo_lines").sum() == 0


def test_analytical_dataset_complete(result):
    a = result["analytical"]
    assert len(a) == len(result["sales"])
    assert a[["category", "town", "year_month"]].notna().all().all()
