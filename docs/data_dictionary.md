# Data Dictionary

All retail tables describe **Duka Bora**, a *fictional* six-store Kenyan supermarket chain.
Every retail record is synthetic (see [data_sources.md](data_sources.md)). Money is in Kenyan Shillings (KES).

**Entity relationships**

```
stores (1) ───< sales_transactions >─── (1) products
                     │       │
customers (1) ───────┘       └─────── (0..1) promotions
calendar (1) ───< sales_transactions   (join on transaction_date = date)
stores (1) ───< customers              (preferred_store_id)
```

`<` marks the "many" side. One order (`order_id`) can contain several transaction lines.

---

## sales_transactions.csv — fact table (exactly 3,000 raw rows)

Grain: **one product line on one receipt.**

| Column | Type | Key | Description | Valid values / rule |
|---|---|---|---|---|
| transaction_id | text | PK | Line identifier, e.g. `TXN00001` | Unique after removing duplicates |
| order_id | text | | Receipt (basket) identifier; groups lines bought together | `ORD00001`… |
| transaction_date | date | FK → calendar.date | Date of sale | 2024-01-01 to 2025-12-31, ISO `YYYY-MM-DD` |
| transaction_time | text | | Time on the receipt (24h) | 07:00–20:59 |
| customer_id | text | FK → customers | Loyalty customer | Blank = card not scanned (walk-in) |
| store_id | text | FK → stores | Selling store | S01–S06 |
| product_id | text | FK → products | Product sold | P001–P040 |
| quantity | integer | | Units sold | ≥ 1 |
| unit_price | decimal | | Shelf price per unit **before** discount, KES | Catalogue price (+4% from 2025-01-01) |
| unit_cost | decimal | | Cost to the retailer per unit, KES | < unit_price |
| discount_percentage | decimal | | Promotion discount, in percent (10 = 10%) | 0, 10, 12, 15 or 20 |
| discount_amount | decimal | | `quantity × unit_price × discount_percentage / 100` | ≥ 0 |
| total_amount | decimal | | Net revenue: `quantity × unit_price − discount_amount` | > 0 |
| profit | decimal | | Gross profit: `total_amount − quantity × unit_cost` | |
| payment_method | text | | Tender type (one per order) | M-Pesa, Cash, Debit/Credit Card, Bank Transfer |
| promotion_id | text | FK → promotions | Campaign that set the discount | Blank = not on promotion (expected, **not** a defect) |

## customers.csv — 1,800 rows

| Column | Type | Key | Description |
|---|---|---|---|
| customer_id | text | PK | `C0001`… numbered in registration order |
| gender | text | | Female / Male |
| age_band | text | | 18-24, 25-34, 35-44, 45-54, 55+ |
| home_county | text | | County of residence |
| registration_date | date | | Date the loyalty account was opened (on or before first purchase) |
| loyalty_member | text | | Yes / No — opted into the points programme |
| preferred_store_id | text | FK → stores | Store the customer usually visits |

No names, phone numbers or other personal identifiers are generated.

## products.csv — 40 rows

| Column | Type | Key | Description |
|---|---|---|---|
| product_id | text | PK | P001–P040 |
| product_name | text | | Generic product name |
| category | text | | Food and Groceries, Beverages, Household Products, Personal Care, Clothing, Electronics |
| brand | text | | **Fictional** brand name |
| pack_size | text | | e.g. `2 kg`, `500 ml` |
| selling_price_kes | decimal | | 2024 catalogue shelf price (illustrative) |
| unit_cost_kes | decimal | | 2024 catalogue unit cost (illustrative) |

## stores.csv — 6 rows

| Column | Type | Key | Description |
|---|---|---|---|
| store_id | text | PK | S01–S06 |
| store_name | text | | Branch name |
| town | text | | Nairobi CBD, Westlands, Thika, Mombasa Town, Kisumu Town, Nakuru Town |
| county | text | | Nairobi, Kiambu, Mombasa, Kisumu, Nakuru |
| store_format | text | | Flagship / Standard / Compact |
| opening_date | date | | Branch opening date (all before 2024) |
| floor_area_sqm | integer | | Sales floor area |

## promotions.csv — 20 rows

| Column | Type | Key | Description |
|---|---|---|---|
| promotion_id | text | PK | PR01–PR20 |
| promotion_name | text | | Campaign name |
| promotion_type | text | | Seasonal, Holiday, Back-to-school, Category |
| start_date / end_date | date | | Inclusive campaign window |
| target_category | text | | Category whose products are discounted |
| discount_percentage | decimal | | Discount in percent |

## calendar.csv — 731 rows (one per day)

| Column | Type | Key | Description |
|---|---|---|---|
| date | date | PK | 2024-01-01 … 2025-12-31 |
| year, quarter, month, month_name, year_month, iso_week, day_of_month | | | Standard date parts |
| day_of_week / day_of_week_num | | | Name and number (1 = Monday) |
| is_weekend | boolean | | Saturday or Sunday |
| is_payday_window | boolean | | Day 25 to day 3 (typical month-end salary period) |
| is_public_holiday / holiday_name | | | From the **verified** holiday file in `data/external/` |

## data/external/kenya_public_holidays_2024_2025.csv — 28 rows (public data)

| Column | Description |
|---|---|
| date | Holiday date |
| holiday_name | Official name |
| holiday_type | Statutory, Statutory Sunday substitute, or Special gazette notice |
| legal_basis | Act section or Gazette notice |
| source_url | Where the date was verified |

---

## Derived fields (created in Milestone 2 onwards)

| Field | Formula |
|---|---|
| gross_amount | `quantity × unit_price` |
| cost_amount | `quantity × unit_cost` |
| net_revenue | `total_amount` (= gross − discount) |
| profit_margin | `profit / total_amount` |
| is_promo | `promotion_id` is not blank |
| order value (AOV) | sum of `total_amount` per `order_id`, then averaged over orders |

## Known raw data-quality issues

The raw files intentionally contain a small set of logged problems (duplicates, missing values,
inconsistent labels, mixed date formats, text amounts, entry-error outliers, price typos and
calculation mismatches). They are listed in `docs/dq_injection_log.csv` and fixed in Milestone 2.
Two **genuine** bulk purchases (60 × bottled water, 48 × sugar) are real outliers and must be kept.
