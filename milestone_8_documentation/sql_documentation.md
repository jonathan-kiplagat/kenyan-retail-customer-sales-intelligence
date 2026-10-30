# SQL Documentation

Reference documentation for the PostgreSQL database built in Milestone 4. For the findings, see
[milestone_4_sql/README.md](../milestone_4_sql/README.md).

| Item | Value |
|---|---|
| Database | PostgreSQL 18, database `duka_bora`, schema `retail` |
| Client | DBeaver (analysis and screenshots), psql (loading) |
| Scripts | [sql/01_create_tables.sql](../sql/01_create_tables.sql) to [sql/07_rfm_analysis.sql](../sql/07_rfm_analysis.sql) |
| Runner | [sql/run_sql.ps1](../sql/run_sql.ps1): runs all scripts and saves their output to [milestone_4_sql/outputs/](../milestone_4_sql/outputs/) |
| Source data | `data/cleaned/*.csv` (the Milestone 2 output) |

## 1. How to run

1. **Install PostgreSQL 18** and create an empty database called `duka_bora`.
2. **Create a file named `.env`** in the project root (it is git-ignored, so the password is never committed):
   ```
   PGHOST=localhost
   PGPORT=5432
   PGDATABASE=duka_bora
   PGUSER=postgres
   PGPASSWORD=<your password>
   ```
3. **Run all seven scripts in order**, from the project root in PowerShell:
   ```powershell
   .\sql\run_sql.ps1                 # all scripts
   .\sql\run_sql.ps1 04,05           # selected scripts only
   ```
4. **Explore the results in DBeaver.** Connect to `duka_bora` and run scripts `03` to `07` with *Execute script* (Alt+X).
   Script `02` uses the psql `\copy` command, so it must be run through psql or the runner.

The rebuild is idempotent: script `01` drops and recreates the `retail` schema, so the scripts can be re-run at any time.

## 2. Schema

### Entity-relationship diagram

```
stores (PK store_id) ──< orders (PK order_id) >── customers (PK customer_id)
                            │   │                     │
calendar (PK calendar_date)─┘   │                     └── preferred_store_id → stores
                                │
products (PK product_id) ──< sales_transactions (PK transaction_id) >── promotions (PK promotion_id)
```

The DBeaver ER diagram is in [milestone_4_sql/screenshots/02_er_diagram.png](../milestone_4_sql/screenshots/02_er_diagram.png).

### Tables

| Table | Rows | Grain | Primary key | Foreign keys |
|---|---:|---|---|---|
| `stores` | 6 | One store | `store_id` | — |
| `products` | 40 | One product | `product_id` | — |
| `customers` | 1,800 | One registered customer | `customer_id` | `preferred_store_id` → stores |
| `promotions` | 20 | One campaign | `promotion_id` | — |
| `calendar` | 731 | One day, 2024-01-01 to 2025-12-31 | `calendar_date` | — |
| `orders` | 2,650 | One receipt | `order_id` | `transaction_date` → calendar, `customer_id` → customers (NULL = walk-in), `store_id` → stores |
| `sales_transactions` | 2,988 | One product line on a receipt | `transaction_id` | `order_id` → orders, `product_id` → products, `promotion_id` → promotions (NULL = full price) |

### Normalization (third normal form)
- **Order details are stored once.** The date, time, customer, store and payment method are the same for every line
  of a receipt, so they are stored once in `orders`, not repeated on each line. This removes update anomalies:
  for example, two lines of the same receipt can never show different payment methods.
- **Product, store, customer and promotion attributes** live only in their own tables.
- **Derived money columns are generated, not stored as input.** `gross_amount`, `discount_amount`, `total_amount`,
  `cost_amount` and `profit` are `GENERATED ALWAYS AS (...) STORED` columns calculated from quantity, unit price,
  unit cost and discount. They cannot disagree with their inputs.

### Constraints (business rules enforced by the database)

| Rule | Implementation |
|---|---|
| Quantities and prices are positive | `CHECK (quantity > 0)`, `CHECK (unit_price > 0)` |
| Every product sells above cost | `CHECK (unit_cost_kes < selling_price_kes)` |
| A discount appears only on a promotion line, and every promotion line has one | `CHECK ((promotion_id IS NULL AND discount_percentage = 0) OR (promotion_id IS NOT NULL AND discount_percentage > 0))` |
| A product appears once per receipt | `UNIQUE (order_id, product_id)` |
| Fixed lists of values | `CHECK (... IN (...))` on payment method, category, store format and gender |
| Campaign dates are valid | `CHECK (end_date >= start_date)` |

### Indexes
B-tree indexes on every foreign key used in joins (`orders.customer_id`, `orders.store_id`,
`sales_transactions.order_id`, `product_id`, `promotion_id`) and on `orders.transaction_date`, which is used in date
filters and `DATE_TRUNC` grouping.

### Views

| View | Script | Purpose |
|---|---|---|
| `v_sales_lines` | 01 | One fully joined row per sales line (orders + products + stores) |
| `v_customer_summary` | 05 | One row per identified customer: orders, spend, first and last purchase, recency |
| `v_customer_rfm` | 07 | RFM scores, code and segment per customer |

Views store no data, so the tables stay normalized while queries stay short.

## 3. Loading process (`02_load_data.sql`)

1. **Copy the CSVs into a `staging` schema** using `\copy`. Every staging column is `TEXT`, so a bad value cannot
   fail the load halfway through.
2. **Insert into the typed tables with explicit casts** (`::DATE`, `::NUMERIC`, `NULLIF(x, '')` for blanks).
   Order-level fields are taken once per `order_id` (`SELECT DISTINCT`) to fill `orders`.
3. **Run the typed inserts inside one transaction** (`BEGIN … COMMIT`), parents before children, so a failure leaves
   the database unchanged.
4. **Keep the staging schema.** Script `03` compares the database's generated money columns with the staged CSV
   values (Q3.6).

## 4. Query catalogue

### `03_data_quality_checks.sql`: proving the load is correct

| Query | Check | Expected | Result |
|---|---|---|---|
| Q3.1 | Row counts vs the cleaned CSVs | Equal | Equal for orders, lines, customers, products and stores |
| Q3.2 | Orphan lines (missing order, product or promotion) | 0 | 0 |
| Q3.3 | Orders with no lines | 0 | 0 |
| Q3.4 | Missing values in key columns | Only walk-in customers and unknown payments | 21 walk-in orders, 7 unknown payments, 0 missing stores |
| Q3.5 | Orders outside the study period | 0 | 0 |
| Q3.6 | Database-generated money vs Python-cleaned values | Identical | KES 2,179,214.72 in both |
| Q3.7 | Promotion lines outside their window, discount or category | 0 | 0 |
| Q3.8 | Customers registered after their first purchase | 0 | 0 |
| Q3.9 | Constraint inventory (catalogue query) | — | Lists every PK, FK, UNIQUE and CHECK |

### `04_sales_analysis.sql`: sales performance

| Query | Business question | Techniques |
|---|---|---|
| Q4.1 | Which stores generate the highest revenue? | JOIN, GROUP BY, `RANK() OVER`, share via `SUM() OVER ()` |
| Q4.2 | Which products generate the highest profit? (Top 10) | `DENSE_RANK`, LIMIT |
| Q4.3 | Which categories perform best? | Aggregates, margin calculation, window share |
| Q4.4 | What are the monthly sales trends? | `DATE_TRUNC`, `LAG` (month-on-month and year-on-year), rolling 3-month `AVG OVER (ROWS BETWEEN 2 PRECEDING ...)`, running `SUM OVER` |
| Q4.5 | Year-on-year summary | `SUM(CASE WHEN year = ...)` pivot |
| Q4.6 | What is the average order value? | CTE at order grain, `PERCENTILE_CONT(0.5)` median |
| Q4.7 | Which weekdays are busiest? | Calendar LEFT JOIN, so days with no orders still count |
| Q4.8 | Best-selling product in each store | `ROW_NUMBER() OVER (PARTITION BY store ...)` |

### `05_customer_analysis.sql`: customer behaviour

| Query | Business question | Techniques |
|---|---|---|
| Q5.1 | Who are the top 10 customers by spend? | View, ORDER BY, LIMIT |
| Q5.2 | Which customers have not purchased recently? | Recency from the analysis date, `HAVING` |
| Q5.2b | How many lapsed repeat customers are there, and how much did they spend? | CASE bands, `FILTER` |
| Q5.3 | How concentrated is customer value? | `NTILE(10)`, cumulative share |
| Q5.4 | One-off vs repeat customers | CASE frequency bands |
| Q5.5 | Do loyalty members return more often? | Grouped rates (an association, not a cause) |
| Q5.6 | Do customers shop at their preferred store? | JOIN on `preferred_store_id` |

### `06_cohort_analysis.sql`: retention

| Query | Business question | Techniques |
|---|---|---|
| Q6.1 | Monthly cohort retention (months 0–12) | Multi-step CTE, `AGE`, `FIRST_VALUE`, `FILTER` pivot |
| Q6.2 | Quarterly cohort retention | Same method with larger, easier-to-read cohorts |
| Q6.3 | Did 2024 or 2025 cohorts return more within 6 months? | Equal observation windows, `EXISTS` |

**Not yet observable vs zero:** a cohort period that lies after 31 Dec 2025 is shown as `NULL`, not 0%. A 0% would
wrongly claim that nobody returned.

### `07_rfm_analysis.sql`: customer value segments

| Query | Business question | Techniques |
|---|---|---|
| Q7.1 | What does each R and M score mean? | MIN/MAX per score |
| Q7.2 | Which customers are most valuable? (segment summary) | View, GROUP BY, window share |
| Q7.3 | Recency × frequency grid | Conditional aggregation |
| Q7.4 | Who are the Champions? | Filtered view |
| Q7.5 | Which high-value customers should be won back first? | Segment filter, ORDER BY spend |
| Q7.6 | Which stores have the most at-risk customers? | Segment mix by preferred store |

**Scoring:**
- **Recency:** fixed bands of ≤90, 91–180, 181–365, 366–545 and >545 days.
- **Frequency:** fixed bands of 1, 2, 3, 4–5 and 6+ orders.
- **Monetary:** `NTILE(5)` quintiles of spend.

The reasons for this mix are in [milestone_4_sql/README.md](../milestone_4_sql/README.md#rfm-method).

## 5. Reconciliation with Python

| Figure | SQL | Python (notebooks 04 and 07) |
|---|---:|---:|
| Net revenue | 2,179,214.72 | 2,179,214.72 |
| Orders | 2,650 | 2,650 |
| Repeat customers silent > 180 days | 249 | 249 |
| Champions | 68 | 68 (Power BI export, same rules) |

## 6. Security
- The password is read from the git-ignored `.env` file. It never appears in scripts, output files or the
  repository.
- `run_sql.ps1` passes it to psql through the `PGPASSWORD` environment variable for that process only.
