# Milestone 2: Data Cleaning and Preparation

The raw extracts in `data/raw/` were turned into validated, analysis-ready tables using Python and pandas. Every decision is documented. Nothing was deleted or filled in silently, and the raw files were never overwritten.

## Deliverables

| Deliverable | Location |
|---|---|
| Cleaning notebook (executed, with outputs) | [notebooks/03_data_cleaning.ipynb](../notebooks/03_data_cleaning.ipynb) |
| Cleaning functions | [src/preprocessing/cleaning.py](../src/preprocessing/cleaning.py) |
| Feature engineering | [src/preprocessing/features.py](../src/preprocessing/features.py) |
| Reproducible pipeline script | [src/preprocessing/pipeline.py](../src/preprocessing/pipeline.py), run with `python -m src.preprocessing.pipeline` |
| Cleaned normalized tables | [data/cleaned/](../data/cleaned/): 6 CSVs, 2,988 sales lines |
| Joined analytical dataset | [data/processed/sales_analytical.csv](../data/processed/sales_analytical.csv): 2,988 rows × 51 columns |
| Before-and-after quality report | [reports/data_quality_before_after.csv](../reports/data_quality_before_after.csv) |
| Automated checks | [tests/test_cleaning.py](../tests/test_cleaning.py) (9 tests, all passing) |
| Figures | `reports/figures/m2_*.png` |

## Before and after

| Metric | Raw | Cleaned |
|---|---:|---:|
| Rows | 3,000 | 2,988 |
| Exact duplicate rows | 12 | 0 |
| Missing customer ID | 25 | 21 (flagged as walk-in) |
| Missing payment method | 10 | 0 (7 labelled "Unknown") |
| Non-standard payment labels | 30 | 0 |
| Dates not in ISO format | 15 | 0 |
| Amounts stored as text | 10 | 0 |
| Lines failing revenue reconciliation | 10 | 0 |
| Quantity above 100 (entry errors) | 4 | 0 |

## Cleaning decisions and reasons

| Issue | Rows | Decision | Reason |
|---|---:|---|---|
| Exact duplicate rows | 12 | Removed | Receipts submitted twice. No conflicting transaction IDs remained afterwards |
| Dates in DD/MM/YYYY format | 15 | Parsed with an explicit format | Letting pandas guess can swap day and month |
| Totals stored as text ("KES 1,234.00") | 10 | Removed "KES" and commas, converted to numbers | The value was right; only the format was wrong |
| Payment label variants | 30 | Mapped to 4 standard labels with an explicit lookup | Every mapping can be reviewed; an unknown spelling stops the pipeline |
| Missing payment method | 10 | 3 recovered from another line of the same order; 7 set to "Unknown" | Payment is captured once per receipt. Filling the rest with the most common method would inflate M-Pesa |
| Missing customer ID | 25 | 4 recovered from the same order; 21 kept and flagged `is_walk_in` | The sale is real, so it counts in revenue. These lines are excluded from customer analytics rather than assigned to a guessed customer |
| Quantity 999 | 4 | Restored to the quantity implied by the receipt total (1 unit each) | The total and the quantity contradict each other. Left in, they would have added about KES 1.44M of phantom revenue |
| Bulk purchases (60 waters, 48 sugar) | 2 | **Kept** | The totals match the quantities, so these are genuine sales |
| Unit price 10× the shelf price | 3 | Replaced with the product's usual price for that year | No business reason for a 10× price; promotions are recorded separately |
| Total saved without the discount | 6 | Recalculated from the formula | The promotion and discount are valid and match the campaign; the stored total was a calculation bug |
| High-value lines (IQR outliers, 11.9%) | 356 | **Kept** | Real electronics and clothing sales; the skew is handled in later analysis |
| Category, county and gender label variants | 11 | Standardized | Inconsistent master data |

Revenue, discount, cost and profit were then **recalculated from the base fields** (quantity, unit price, unit cost, discount percentage), so every line reconciles exactly.

## Validation results
- Every primary key is unique and non-blank. Every foreign key resolves (customer, product, store, promotion).
- Every order is internally consistent: one date, store, customer and payment method per receipt.
- All 315 promotion lines fall inside their campaign window, use the campaign's discount and belong to its target category. No unpromoted line has a discount.
- No customer registered after their first purchase, and every product's unit cost is below its price.
- The notebook and the pipeline script produce identical output.

## Audit
After cleaning was finished, the results were compared with `docs/dq_injection_log.csv` and with the generator's clean data, cell by cell. **All 126 injected issues were detected.** The only cells that differ from the true data are the 21 customer IDs and 7 payment methods for which no evidence existed. Leaving them flagged rather than guessed is the correct outcome.

## Engineered features (in `sales_analytical.csv`)
- **Money:** `gross_amount`, `cost_amount`, `profit_margin`.
- **Flags:** `is_promo`, `is_walk_in`.
- **Time:** `hour`, `day_part`.
- **Calendar:** `is_weekend`, `is_payday_window`, `is_public_holiday`, `is_holiday_eve`.
- **Basket:** `order_value`, `order_lines`, `order_units`.
- **Customer:** `cohort_month`.
