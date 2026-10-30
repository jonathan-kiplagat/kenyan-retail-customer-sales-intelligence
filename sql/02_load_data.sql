-- =============================================================================
-- 02_load_data.sql
-- Load the cleaned CSVs (data/cleaned/) into the normalized "retail" schema.
--
-- HOW TO RUN: from the PROJECT ROOT folder with psql (\copy is a psql command
-- that reads files from YOUR computer, so it needs no server file permissions):
--     psql -d duka_bora -f sql/02_load_data.sql
-- In DBeaver, \copy is not available: either run this file with psql, or use
-- DBeaver's "Import Data" wizard to load each CSV into the staging tables
-- below and then run the INSERT section.
--
-- Approach: CSV -> "staging" tables (all TEXT, no rules) -> typed INSERT into
-- "retail" tables. Casting happens in one visible place, and any bad value
-- makes the load fail loudly instead of being silently converted.
-- =============================================================================

\set ON_ERROR_STOP on

DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;

CREATE TABLE staging.stores (store_id TEXT, store_name TEXT, town TEXT, county TEXT,
    store_format TEXT, opening_date TEXT, floor_area_sqm TEXT);
CREATE TABLE staging.products (product_id TEXT, product_name TEXT, category TEXT, brand TEXT,
    pack_size TEXT, selling_price_kes TEXT, unit_cost_kes TEXT);
CREATE TABLE staging.customers (customer_id TEXT, gender TEXT, age_band TEXT, home_county TEXT,
    registration_date TEXT, loyalty_member TEXT, preferred_store_id TEXT);
CREATE TABLE staging.promotions (promotion_id TEXT, promotion_name TEXT, promotion_type TEXT,
    start_date TEXT, end_date TEXT, target_category TEXT, discount_percentage TEXT);
CREATE TABLE staging.calendar (calendar_date TEXT, year TEXT, quarter TEXT, month TEXT, month_name TEXT,
    year_month TEXT, iso_week TEXT, day_of_month TEXT, day_of_week TEXT, day_of_week_num TEXT,
    is_weekend TEXT, is_payday_window TEXT, holiday_name TEXT, is_public_holiday TEXT);
CREATE TABLE staging.sales (transaction_id TEXT, order_id TEXT, transaction_date TEXT, transaction_time TEXT,
    customer_id TEXT, store_id TEXT, product_id TEXT, quantity TEXT, unit_price TEXT, unit_cost TEXT,
    gross_amount TEXT, discount_percentage TEXT, discount_amount TEXT, total_amount TEXT,
    cost_amount TEXT, profit TEXT, payment_method TEXT, promotion_id TEXT, is_walk_in TEXT);

\copy staging.stores     FROM 'data/cleaned/stores.csv'             WITH (FORMAT csv, HEADER true)
\copy staging.products   FROM 'data/cleaned/products.csv'           WITH (FORMAT csv, HEADER true)
\copy staging.customers  FROM 'data/cleaned/customers.csv'          WITH (FORMAT csv, HEADER true)
\copy staging.promotions FROM 'data/cleaned/promotions.csv'         WITH (FORMAT csv, HEADER true)
\copy staging.calendar   FROM 'data/cleaned/calendar.csv'           WITH (FORMAT csv, HEADER true)
\copy staging.sales      FROM 'data/cleaned/sales_transactions.csv' WITH (FORMAT csv, HEADER true)

-- -----------------------------------------------------------------------------
-- Typed inserts (parents before children so foreign keys are satisfied)
-- -----------------------------------------------------------------------------
SET search_path TO retail;
BEGIN;

TRUNCATE sales_transactions, orders, customers, promotions, products, stores, calendar;

INSERT INTO stores
SELECT store_id, store_name, town, county, store_format, opening_date::date, floor_area_sqm::int
FROM staging.stores;

INSERT INTO products
SELECT product_id, product_name, category, brand, pack_size,
       selling_price_kes::numeric, unit_cost_kes::numeric
FROM staging.products;

INSERT INTO customers
SELECT customer_id, gender, age_band, home_county, registration_date::date,
       loyalty_member::boolean,                      -- 'Yes'/'No' are valid PostgreSQL booleans
       preferred_store_id
FROM staging.customers;

INSERT INTO promotions
SELECT promotion_id, promotion_name, promotion_type, start_date::date, end_date::date,
       target_category, discount_percentage::numeric
FROM staging.promotions;

INSERT INTO calendar
SELECT calendar_date::date, year::smallint, quarter::smallint, month::smallint, month_name,
       year_month, iso_week::smallint, day_of_month::smallint, day_of_week, day_of_week_num::smallint,
       is_weekend::boolean, is_payday_window::boolean, NULLIF(holiday_name, ''), is_public_holiday::boolean
FROM staging.calendar;

-- One row per order: order-level attributes are identical on every line of an
-- order (verified in Milestone 2), so DISTINCT collapses lines to receipts.
INSERT INTO orders
SELECT DISTINCT order_id, transaction_date::date, transaction_time::time,
       NULLIF(customer_id, ''), store_id, payment_method
FROM staging.sales;

-- Money columns are NOT inserted: the database generates them.
INSERT INTO sales_transactions (transaction_id, order_id, product_id, promotion_id,
                                quantity, unit_price, unit_cost, discount_percentage)
SELECT transaction_id, order_id, product_id, NULLIF(promotion_id, ''),
       quantity::int, unit_price::numeric, unit_cost::numeric, discount_percentage::numeric
FROM staging.sales;

COMMIT;

-- Load summary
SELECT 'stores' AS table_name, COUNT(*) AS rows FROM stores
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'promotions', COUNT(*) FROM promotions
UNION ALL SELECT 'calendar', COUNT(*) FROM calendar
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'sales_transactions', COUNT(*) FROM sales_transactions;
