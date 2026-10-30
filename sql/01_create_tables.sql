-- =============================================================================
-- 01_create_tables.sql
-- Duka Bora retail database: normalized schema with primary/foreign keys.
-- PostgreSQL 18. Safe to re-run: drops and recreates the "retail" schema.
--
-- Design (third normal form):
--   * Order-level facts (date, time, customer, store, payment) are stored ONCE
--     in "orders" instead of being repeated on every product line.
--   * "sales_transactions" holds one row per product line and references its order.
--   * Money columns are GENERATED from quantity, price, cost and discount, so
--     they can never disagree with the base fields.
--   * CHECK constraints enforce the business rules found during cleaning.
-- =============================================================================

DROP SCHEMA IF EXISTS retail CASCADE;
CREATE SCHEMA retail;
SET search_path TO retail;

-- -----------------------------------------------------------------------------
-- Dimension tables
-- -----------------------------------------------------------------------------
CREATE TABLE stores (
    store_id        VARCHAR(3)   PRIMARY KEY,
    store_name      TEXT         NOT NULL UNIQUE,
    town            TEXT         NOT NULL,
    county          TEXT         NOT NULL,
    store_format    TEXT         NOT NULL CHECK (store_format IN ('Flagship', 'Standard', 'Compact')),
    opening_date    DATE         NOT NULL,
    floor_area_sqm  INTEGER      NOT NULL CHECK (floor_area_sqm > 0)
);

CREATE TABLE products (
    product_id         VARCHAR(4)     PRIMARY KEY,
    product_name       TEXT           NOT NULL,
    category           TEXT           NOT NULL CHECK (category IN (
                           'Food and Groceries', 'Beverages', 'Household Products',
                           'Personal Care', 'Clothing', 'Electronics')),
    brand              TEXT           NOT NULL,
    pack_size          TEXT           NOT NULL,
    selling_price_kes  NUMERIC(10, 2) NOT NULL CHECK (selling_price_kes > 0),
    unit_cost_kes      NUMERIC(10, 2) NOT NULL CHECK (unit_cost_kes > 0),
    CHECK (unit_cost_kes < selling_price_kes)          -- every product sells above cost
);

CREATE TABLE customers (
    customer_id         VARCHAR(5)  PRIMARY KEY,
    gender              TEXT        NOT NULL CHECK (gender IN ('Female', 'Male')),
    age_band            TEXT        NOT NULL,
    home_county         TEXT        NOT NULL,
    registration_date   DATE        NOT NULL,
    loyalty_member      BOOLEAN     NOT NULL,
    preferred_store_id  VARCHAR(3)  NOT NULL REFERENCES stores (store_id)
);

CREATE TABLE promotions (
    promotion_id         VARCHAR(4)     PRIMARY KEY,
    promotion_name       TEXT           NOT NULL,
    promotion_type       TEXT           NOT NULL,
    start_date           DATE           NOT NULL,
    end_date             DATE           NOT NULL,
    target_category      TEXT           NOT NULL,
    discount_percentage  NUMERIC(5, 2)  NOT NULL CHECK (discount_percentage > 0 AND discount_percentage < 100),
    CHECK (end_date >= start_date)
);

CREATE TABLE calendar (
    calendar_date      DATE      PRIMARY KEY,
    year               SMALLINT  NOT NULL,
    quarter            SMALLINT  NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month              SMALLINT  NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name         TEXT      NOT NULL,
    year_month         CHAR(7)   NOT NULL,
    iso_week           SMALLINT  NOT NULL,
    day_of_month       SMALLINT  NOT NULL,
    day_of_week        TEXT      NOT NULL,
    day_of_week_num    SMALLINT  NOT NULL CHECK (day_of_week_num BETWEEN 1 AND 7),
    is_weekend         BOOLEAN   NOT NULL,
    is_payday_window   BOOLEAN   NOT NULL,
    holiday_name       TEXT,                          -- NULL on ordinary days (not missing data)
    is_public_holiday  BOOLEAN   NOT NULL
);

-- -----------------------------------------------------------------------------
-- Fact tables
-- -----------------------------------------------------------------------------
CREATE TABLE orders (
    order_id          VARCHAR(8)  PRIMARY KEY,
    transaction_date  DATE        NOT NULL REFERENCES calendar (calendar_date),
    transaction_time  TIME        NOT NULL,
    customer_id       VARCHAR(5)  REFERENCES customers (customer_id),   -- NULL = walk-in (card not scanned)
    store_id          VARCHAR(3)  NOT NULL REFERENCES stores (store_id),
    payment_method    TEXT        NOT NULL CHECK (payment_method IN (
                          'M-Pesa', 'Cash', 'Debit/Credit Card', 'Bank Transfer', 'Unknown'))
);

CREATE TABLE sales_transactions (
    transaction_id       VARCHAR(8)     PRIMARY KEY,
    order_id             VARCHAR(8)     NOT NULL REFERENCES orders (order_id),
    product_id           VARCHAR(4)     NOT NULL REFERENCES products (product_id),
    promotion_id         VARCHAR(4)     REFERENCES promotions (promotion_id),   -- NULL = full price
    quantity             INTEGER        NOT NULL CHECK (quantity > 0),
    unit_price           NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    unit_cost            NUMERIC(10, 2) NOT NULL CHECK (unit_cost > 0),
    discount_percentage  NUMERIC(5, 2)  NOT NULL DEFAULT 0 CHECK (discount_percentage >= 0 AND discount_percentage < 100),

    -- Derived money columns: computed by the database, never typed in.
    gross_amount     NUMERIC(12, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    discount_amount  NUMERIC(12, 2) GENERATED ALWAYS AS (ROUND(quantity * unit_price * discount_percentage / 100, 2)) STORED,
    total_amount     NUMERIC(12, 2) GENERATED ALWAYS AS (
                         quantity * unit_price - ROUND(quantity * unit_price * discount_percentage / 100, 2)) STORED,
    cost_amount      NUMERIC(12, 2) GENERATED ALWAYS AS (quantity * unit_cost) STORED,
    profit           NUMERIC(12, 2) GENERATED ALWAYS AS (
                         quantity * unit_price - ROUND(quantity * unit_price * discount_percentage / 100, 2)
                         - quantity * unit_cost) STORED,

    -- A discount is only allowed when the line is on a promotion, and vice versa.
    CHECK ((promotion_id IS NULL AND discount_percentage = 0)
        OR (promotion_id IS NOT NULL AND discount_percentage > 0)),
    UNIQUE (order_id, product_id)                     -- a product appears once per receipt
);

-- Indexes on foreign keys and dates used in joins and filters.
CREATE INDEX idx_orders_date      ON orders (transaction_date);
CREATE INDEX idx_orders_customer  ON orders (customer_id);
CREATE INDEX idx_orders_store     ON orders (store_id);
CREATE INDEX idx_sales_order      ON sales_transactions (order_id);
CREATE INDEX idx_sales_product    ON sales_transactions (product_id);
CREATE INDEX idx_sales_promotion  ON sales_transactions (promotion_id);

-- -----------------------------------------------------------------------------
-- Convenience view: one row per line with all attributes (used by later
-- scripts and by Power BI). Views store no data, so normalization is kept.
-- -----------------------------------------------------------------------------
CREATE VIEW v_sales_lines AS
SELECT
    s.transaction_id, s.order_id, o.transaction_date, o.transaction_time,
    o.customer_id, o.store_id, st.store_name, st.town, st.county,
    s.product_id, p.product_name, p.category,
    s.promotion_id, o.payment_method,
    s.quantity, s.unit_price, s.unit_cost, s.discount_percentage,
    s.gross_amount, s.discount_amount, s.total_amount, s.cost_amount, s.profit,
    c.year, c.quarter, c.month, c.year_month, c.day_of_week, c.day_of_week_num,
    c.is_weekend, c.is_payday_window, c.is_public_holiday
FROM sales_transactions s
JOIN orders   o  ON o.order_id = s.order_id
JOIN stores   st ON st.store_id = o.store_id
JOIN products p  ON p.product_id = s.product_id
JOIN calendar c  ON c.calendar_date = o.transaction_date;
