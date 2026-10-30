-- =============================================================================
-- 04_sales_analysis.sql
-- Business questions on stores, products, categories, time and order value.
-- Techniques: JOINs, aggregation, GROUP BY / HAVING, CASE, CTEs,
-- window functions (SUM OVER, LAG, AVG OVER), ranking (RANK, DENSE_RANK,
-- ROW_NUMBER) and date functions (DATE_TRUNC, EXTRACT, TO_CHAR).
-- =============================================================================
SET search_path TO retail;

-- Q4.1 Which stores generate the highest revenue?
-- JOIN lines -> orders -> stores, aggregate, then RANK stores by revenue.
-- Share of chain revenue uses a window SUM over all stores.
SELECT
    RANK() OVER (ORDER BY SUM(s.total_amount) DESC)                    AS revenue_rank,
    st.store_name,
    st.county,
    COUNT(DISTINCT o.order_id)                                         AS orders,
    SUM(s.total_amount)                                                AS revenue_kes,
    SUM(s.profit)                                                      AS profit_kes,
    ROUND(100.0 * SUM(s.profit) / SUM(s.total_amount), 1)              AS margin_pct,
    ROUND(100.0 * SUM(s.total_amount) / SUM(SUM(s.total_amount)) OVER (), 1) AS revenue_share_pct
FROM sales_transactions s
JOIN orders o  ON o.order_id = s.order_id
JOIN stores st ON st.store_id = o.store_id
GROUP BY st.store_name, st.county
ORDER BY revenue_rank;

-- Q4.2 Which products generate the highest profit? (Top 10)
-- DENSE_RANK gives tied products the same rank without gaps.
SELECT *
FROM (
    SELECT
        DENSE_RANK() OVER (ORDER BY SUM(s.profit) DESC)        AS profit_rank,
        p.product_name,
        p.category,
        SUM(s.quantity)                                        AS units,
        SUM(s.total_amount)                                    AS revenue_kes,
        SUM(s.profit)                                          AS profit_kes,
        ROUND(100.0 * SUM(s.profit) / SUM(s.total_amount), 1)  AS margin_pct
    FROM sales_transactions s
    JOIN products p ON p.product_id = s.product_id
    GROUP BY p.product_name, p.category
) ranked
WHERE profit_rank <= 10
ORDER BY profit_rank;

-- Q4.3 Which categories perform best?
-- HAVING keeps only categories that earned at least KES 100,000 in revenue
-- (all six qualify); CASE labels each category's margin level.
SELECT
    p.category,
    COUNT(*)                                               AS lines,
    SUM(s.quantity)                                        AS units,
    SUM(s.total_amount)                                    AS revenue_kes,
    SUM(s.profit)                                          AS profit_kes,
    ROUND(100.0 * SUM(s.profit) / SUM(s.total_amount), 1)  AS margin_pct,
    ROUND(100.0 * SUM(s.profit) / SUM(SUM(s.profit)) OVER (), 1) AS profit_share_pct,
    CASE
        WHEN SUM(s.profit) / SUM(s.total_amount) >= 0.35 THEN 'High margin'
        WHEN SUM(s.profit) / SUM(s.total_amount) >= 0.20 THEN 'Medium margin'
        ELSE 'Low margin'
    END                                                    AS margin_band
FROM sales_transactions s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.category
HAVING SUM(s.total_amount) >= 100000
ORDER BY profit_kes DESC;

-- Q4.4 What are the monthly sales trends?
-- CTE builds monthly totals; LAG compares with the previous month and with the
-- same month last year (12 rows back); a window SUM gives the running total,
-- and AVG over 3 rows smooths the noisy months.
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', o.transaction_date)::date AS month,
        COUNT(DISTINCT o.order_id)                    AS orders,
        SUM(s.total_amount)                           AS revenue_kes,
        SUM(s.profit)                                 AS profit_kes
    FROM sales_transactions s
    JOIN orders o ON o.order_id = s.order_id
    GROUP BY 1
)
SELECT
    TO_CHAR(month, 'YYYY-MM')                                                   AS month,
    orders,
    revenue_kes,
    profit_kes,
    ROUND(100.0 * (revenue_kes / LAG(revenue_kes) OVER (ORDER BY month) - 1), 1)     AS mom_growth_pct,
    ROUND(100.0 * (revenue_kes / LAG(revenue_kes, 12) OVER (ORDER BY month) - 1), 1) AS yoy_growth_pct,
    ROUND(AVG(revenue_kes) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS rolling_3m_avg_kes,
    SUM(revenue_kes) OVER (ORDER BY month)                                      AS running_total_kes
FROM monthly
ORDER BY month;

-- Q4.5 Year-on-year summary. CASE inside SUM pivots years into columns.
SELECT
    metric,
    y2024,
    y2025,
    ROUND(100.0 * (y2025 / y2024 - 1), 1) AS growth_pct
FROM (
    SELECT 'Revenue (KES)' AS metric,
           SUM(CASE WHEN EXTRACT(YEAR FROM o.transaction_date) = 2024 THEN s.total_amount END) AS y2024,
           SUM(CASE WHEN EXTRACT(YEAR FROM o.transaction_date) = 2025 THEN s.total_amount END) AS y2025
    FROM sales_transactions s JOIN orders o ON o.order_id = s.order_id
    UNION ALL
    SELECT 'Profit (KES)',
           SUM(CASE WHEN EXTRACT(YEAR FROM o.transaction_date) = 2024 THEN s.profit END),
           SUM(CASE WHEN EXTRACT(YEAR FROM o.transaction_date) = 2025 THEN s.profit END)
    FROM sales_transactions s JOIN orders o ON o.order_id = s.order_id
    UNION ALL
    SELECT 'Units sold',
           SUM(CASE WHEN EXTRACT(YEAR FROM o.transaction_date) = 2024 THEN s.quantity END),
           SUM(CASE WHEN EXTRACT(YEAR FROM o.transaction_date) = 2025 THEN s.quantity END)
    FROM sales_transactions s JOIN orders o ON o.order_id = s.order_id
    UNION ALL
    SELECT 'Orders',
           COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM transaction_date) = 2024),
           COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM transaction_date) = 2025)
    FROM orders
) t;

-- Q4.6 What is the average order value?
-- Order value must be summed per order FIRST (CTE), then averaged; averaging
-- line amounts would understate it. PERCENTILE_CONT gives the median.
WITH order_values AS (
    SELECT o.order_id, o.store_id, o.payment_method, SUM(s.total_amount) AS order_value
    FROM orders o
    JOIN sales_transactions s ON s.order_id = o.order_id
    GROUP BY o.order_id, o.store_id, o.payment_method
)
SELECT
    'All orders'                                                      AS segment,
    COUNT(*)                                                          AS orders,
    ROUND(AVG(order_value), 2)                                        AS avg_order_value_kes,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY order_value)::numeric, 2) AS median_order_value_kes
FROM order_values
UNION ALL
SELECT st.store_name, COUNT(*), ROUND(AVG(order_value), 2),
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY order_value)::numeric, 2)
FROM order_values ov JOIN stores st ON st.store_id = ov.store_id
GROUP BY st.store_name
UNION ALL
SELECT 'Paid by ' || payment_method, COUNT(*), ROUND(AVG(order_value), 2),
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY order_value)::numeric, 2)
FROM order_values
GROUP BY payment_method
ORDER BY orders DESC;

-- Q4.7 Date-based pattern: orders and revenue by day of week.
-- Orders per day divides by ALL calendar days of that weekday (from the
-- calendar dimension), including days with no orders, so the comparison is fair.
WITH days AS (
    SELECT day_of_week_num, day_of_week, COUNT(*) AS calendar_days
    FROM calendar
    GROUP BY day_of_week_num, day_of_week
),
by_day AS (
    SELECT c.day_of_week_num,
           COUNT(DISTINCT o.order_id) AS orders,
           SUM(s.total_amount)        AS revenue_kes
    FROM orders o
    JOIN calendar c           ON c.calendar_date = o.transaction_date
    JOIN sales_transactions s ON s.order_id = o.order_id
    GROUP BY c.day_of_week_num
)
SELECT d.day_of_week_num, d.day_of_week, d.calendar_days, b.orders, b.revenue_kes,
       ROUND(b.orders::numeric / d.calendar_days, 2) AS orders_per_calendar_day
FROM days d
JOIN by_day b USING (day_of_week_num)
ORDER BY d.day_of_week_num;

-- Q4.8 Best-selling product in each store (ROW_NUMBER per partition).
WITH store_product AS (
    SELECT st.store_name, p.product_name, SUM(s.quantity) AS units,
           ROW_NUMBER() OVER (PARTITION BY st.store_name ORDER BY SUM(s.quantity) DESC, p.product_name) AS rn
    FROM sales_transactions s
    JOIN orders o   ON o.order_id = s.order_id
    JOIN stores st  ON st.store_id = o.store_id
    JOIN products p ON p.product_id = s.product_id
    GROUP BY st.store_name, p.product_name
)
SELECT store_name, product_name AS top_product_by_units, units
FROM store_product
WHERE rn = 1
ORDER BY units DESC;
