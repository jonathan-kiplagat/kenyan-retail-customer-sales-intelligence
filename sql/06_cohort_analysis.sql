-- =============================================================================
-- 06_cohort_analysis.sql
-- Customer retention by acquisition cohort.
--
-- Cohort  = the month (or quarter) of a customer's FIRST purchase in the data.
-- Period k = number of months (quarters) after the cohort month.
-- Retention in period k = share of the cohort that bought again in period k.
--
-- Caveat (left-censoring): the data starts in January 2024, so customers who
-- were already shopping before 2024 appear as "new" in the earliest cohorts.
-- Early-2024 cohorts therefore contain established customers and look more
-- loyal than genuinely new ones. Later cohorts have fewer periods to observe.
-- =============================================================================
SET search_path TO retail;

-- Q6.1 Monthly cohort retention matrix (periods 0-12 months).
-- Blank (NULL) = period not yet observable (after Dec 2025); 0.0 = observed, nobody returned.
WITH customer_orders AS (
    SELECT DISTINCT customer_id, DATE_TRUNC('month', transaction_date)::date AS order_month
    FROM orders
    WHERE customer_id IS NOT NULL
),
cohorts AS (
    SELECT customer_id, MIN(order_month) AS cohort_month
    FROM customer_orders
    GROUP BY customer_id
),
activity AS (
    SELECT c.cohort_month,
           co.customer_id,
           (EXTRACT(YEAR FROM AGE(co.order_month, c.cohort_month)) * 12
            + EXTRACT(MONTH FROM AGE(co.order_month, c.cohort_month)))::int AS months_since_first
    FROM customer_orders co
    JOIN cohorts c USING (customer_id)
),
cohort_counts AS (
    SELECT cohort_month, months_since_first, COUNT(DISTINCT customer_id) AS active_customers
    FROM activity
    GROUP BY cohort_month, months_since_first
),
with_size AS (
    SELECT *, FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY months_since_first) AS cohort_size
    FROM cohort_counts
)
SELECT
    TO_CHAR(cohort_month, 'YYYY-MM') AS cohort,
    MAX(cohort_size)                 AS cohort_size,
    CASE WHEN cohort_month + INTERVAL '1 months' <= DATE '2025-12-01' THEN ROUND(100.0 * COALESCE(MAX(active_customers) FILTER (WHERE months_since_first = 1), 0) / MAX(cohort_size), 1) END AS m1,
    CASE WHEN cohort_month + INTERVAL '2 months' <= DATE '2025-12-01' THEN ROUND(100.0 * COALESCE(MAX(active_customers) FILTER (WHERE months_since_first = 2), 0) / MAX(cohort_size), 1) END AS m2,
    CASE WHEN cohort_month + INTERVAL '3 months' <= DATE '2025-12-01' THEN ROUND(100.0 * COALESCE(MAX(active_customers) FILTER (WHERE months_since_first = 3), 0) / MAX(cohort_size), 1) END AS m3,
    CASE WHEN cohort_month + INTERVAL '6 months' <= DATE '2025-12-01' THEN ROUND(100.0 * COALESCE(MAX(active_customers) FILTER (WHERE months_since_first = 6), 0) / MAX(cohort_size), 1) END AS m6,
    CASE WHEN cohort_month + INTERVAL '9 months' <= DATE '2025-12-01' THEN ROUND(100.0 * COALESCE(MAX(active_customers) FILTER (WHERE months_since_first = 9), 0) / MAX(cohort_size), 1) END AS m9,
    CASE WHEN cohort_month + INTERVAL '12 months' <= DATE '2025-12-01' THEN ROUND(100.0 * COALESCE(MAX(active_customers) FILTER (WHERE months_since_first = 12), 0) / MAX(cohort_size), 1) END AS m12
FROM with_size
GROUP BY cohort_month
ORDER BY cohort_month;

-- Q6.2 Quarterly cohort retention matrix (larger cohorts, easier to read).
-- Blank (NULL) = quarter not yet observable; 0.0 = observed, nobody returned.
WITH customer_orders AS (
    SELECT DISTINCT customer_id, DATE_TRUNC('quarter', transaction_date)::date AS order_quarter
    FROM orders
    WHERE customer_id IS NOT NULL
),
cohorts AS (
    SELECT customer_id, MIN(order_quarter) AS cohort_quarter
    FROM customer_orders
    GROUP BY customer_id
),
activity AS (
    SELECT c.cohort_quarter, co.customer_id,
           ((EXTRACT(YEAR FROM co.order_quarter) - EXTRACT(YEAR FROM c.cohort_quarter)) * 4
            + (EXTRACT(QUARTER FROM co.order_quarter) - EXTRACT(QUARTER FROM c.cohort_quarter)))::int AS q_since_first
    FROM customer_orders co
    JOIN cohorts c USING (customer_id)
),
sizes AS (
    SELECT cohort_quarter, COUNT(*) AS cohort_size FROM cohorts GROUP BY cohort_quarter
)
SELECT
    EXTRACT(YEAR FROM a.cohort_quarter) || '-Q' || EXTRACT(QUARTER FROM a.cohort_quarter) AS cohort,
    s.cohort_size,
    CASE WHEN a.cohort_quarter + INTERVAL '3 months' <= DATE '2025-10-01' THEN ROUND(100.0 * COUNT(DISTINCT a.customer_id) FILTER (WHERE q_since_first = 1) / s.cohort_size, 1) END AS q1,
    CASE WHEN a.cohort_quarter + INTERVAL '6 months' <= DATE '2025-10-01' THEN ROUND(100.0 * COUNT(DISTINCT a.customer_id) FILTER (WHERE q_since_first = 2) / s.cohort_size, 1) END AS q2,
    CASE WHEN a.cohort_quarter + INTERVAL '9 months' <= DATE '2025-10-01' THEN ROUND(100.0 * COUNT(DISTINCT a.customer_id) FILTER (WHERE q_since_first = 3) / s.cohort_size, 1) END AS q3,
    CASE WHEN a.cohort_quarter + INTERVAL '12 months' <= DATE '2025-10-01' THEN ROUND(100.0 * COUNT(DISTINCT a.customer_id) FILTER (WHERE q_since_first = 4) / s.cohort_size, 1) END AS q4,
    CASE WHEN a.cohort_quarter + INTERVAL '15 months' <= DATE '2025-10-01' THEN ROUND(100.0 * COUNT(DISTINCT a.customer_id) FILTER (WHERE q_since_first = 5) / s.cohort_size, 1) END AS q5,
    CASE WHEN a.cohort_quarter + INTERVAL '18 months' <= DATE '2025-10-01' THEN ROUND(100.0 * COUNT(DISTINCT a.customer_id) FILTER (WHERE q_since_first = 6) / s.cohort_size, 1) END AS q6,
    CASE WHEN a.cohort_quarter + INTERVAL '21 months' <= DATE '2025-10-01' THEN ROUND(100.0 * COUNT(DISTINCT a.customer_id) FILTER (WHERE q_since_first = 7) / s.cohort_size, 1) END AS q7
FROM activity a
JOIN sizes s USING (cohort_quarter)
GROUP BY a.cohort_quarter, s.cohort_size
ORDER BY a.cohort_quarter;

-- Q6.3 Repeat-purchase rate by cohort year, measured over the SAME window
-- (first 6 months after first purchase) so 2024 and 2025 cohorts are comparable.
-- Only customers whose first purchase was by 2025-06-30 have a full 6 months.
WITH firsts AS (
    SELECT customer_id, MIN(transaction_date) AS first_date
    FROM orders WHERE customer_id IS NOT NULL
    GROUP BY customer_id
),
repeat_6m AS (
    SELECT f.customer_id, f.first_date,
           EXISTS (SELECT 1 FROM orders o
                   WHERE o.customer_id = f.customer_id
                     AND o.transaction_date >  f.first_date
                     AND o.transaction_date <= f.first_date + INTERVAL '6 months') AS returned_within_6m
    FROM firsts f
    WHERE f.first_date <= DATE '2025-06-30'
)
SELECT
    EXTRACT(YEAR FROM first_date)                                         AS cohort_year,
    COUNT(*)                                                              AS customers,
    SUM(CASE WHEN returned_within_6m THEN 1 ELSE 0 END)                   AS returned_within_6_months,
    ROUND(100.0 * AVG(CASE WHEN returned_within_6m THEN 1 ELSE 0 END), 1) AS repeat_rate_6m_pct
FROM repeat_6m
GROUP BY 1
ORDER BY 1;
