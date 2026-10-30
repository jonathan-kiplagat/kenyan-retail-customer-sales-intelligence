-- =============================================================================
-- 05_customer_analysis.sql
-- Who are the best customers, who has stopped buying, and how concentrated is
-- customer value? Walk-in orders (customer_id IS NULL) are excluded throughout.
-- Analysis date = 2025-12-31 (last day of data), used for "days since purchase".
-- =============================================================================
SET search_path TO retail;

-- Reusable per-customer summary as a view (also used by 07_rfm_analysis.sql).
CREATE OR REPLACE VIEW v_customer_summary AS
SELECT
    o.customer_id,
    COUNT(DISTINCT o.order_id)                       AS orders,
    SUM(s.total_amount)                              AS total_spend_kes,
    SUM(s.profit)                                    AS total_profit_kes,
    MIN(o.transaction_date)                          AS first_purchase,
    MAX(o.transaction_date)                          AS last_purchase,
    DATE '2025-12-31' - MAX(o.transaction_date)      AS days_since_last_purchase
FROM orders o
JOIN sales_transactions s ON s.order_id = o.order_id
WHERE o.customer_id IS NOT NULL
GROUP BY o.customer_id;

-- Q5.1 Who are the top 10 customers by spend?
SELECT
    RANK() OVER (ORDER BY cs.total_spend_kes DESC)        AS spend_rank,
    cs.customer_id,
    c.loyalty_member,
    st.town                                               AS preferred_store,
    cs.orders,
    cs.total_spend_kes,
    ROUND(cs.total_spend_kes / cs.orders, 2)              AS avg_order_value_kes,
    cs.last_purchase,
    cs.days_since_last_purchase
FROM v_customer_summary cs
JOIN customers c ON c.customer_id = cs.customer_id
JOIN stores st   ON st.store_id = c.preferred_store_id
ORDER BY spend_rank
LIMIT 10;

-- Q5.2 Which customers have not purchased recently?
-- Focus on customers who were ENGAGED (2+ orders) but have been silent for
-- more than 180 days: these are the most valuable win-back targets.
-- (A data-driven inactivity threshold is set in Milestone 6.)
SELECT
    cs.customer_id,
    cs.orders,
    cs.total_spend_kes,
    cs.last_purchase,
    cs.days_since_last_purchase,
    CASE
        WHEN cs.days_since_last_purchase > 365 THEN 'Silent > 1 year'
        WHEN cs.days_since_last_purchase > 270 THEN 'Silent 9-12 months'
        ELSE 'Silent 6-9 months'
    END AS inactivity_band
FROM v_customer_summary cs
WHERE cs.orders >= 2
  AND cs.days_since_last_purchase > 180
ORDER BY cs.total_spend_kes DESC
LIMIT 15;

-- Q5.2b How many lapsed repeat customers are there, and how much did they spend?
SELECT
    CASE
        WHEN days_since_last_purchase > 365 THEN '1. Silent > 1 year'
        WHEN days_since_last_purchase > 270 THEN '2. Silent 9-12 months'
        WHEN days_since_last_purchase > 180 THEN '3. Silent 6-9 months'
        ELSE '4. Active in last 6 months'
    END                                        AS status,
    COUNT(*)                                   AS repeat_customers,
    SUM(total_spend_kes)                       AS lifetime_spend_kes
FROM v_customer_summary
WHERE orders >= 2
GROUP BY 1
ORDER BY 1;

-- Q5.3 Customer value tiers with NTILE: split customers into 10 equal groups
-- (deciles) by spend and show each decile's share of revenue.
WITH deciles AS (
    SELECT customer_id, total_spend_kes,
           NTILE(10) OVER (ORDER BY total_spend_kes DESC) AS spend_decile
    FROM v_customer_summary
)
SELECT
    spend_decile,
    COUNT(*)                                                          AS customers,
    ROUND(MIN(total_spend_kes), 0)                                    AS min_spend_kes,
    ROUND(MAX(total_spend_kes), 0)                                    AS max_spend_kes,
    SUM(total_spend_kes)                                              AS revenue_kes,
    ROUND(100.0 * SUM(total_spend_kes) / SUM(SUM(total_spend_kes)) OVER (), 1) AS revenue_share_pct,
    ROUND(100.0 * SUM(SUM(total_spend_kes)) OVER (ORDER BY spend_decile)
          / SUM(SUM(total_spend_kes)) OVER (), 1)                     AS cumulative_share_pct
FROM deciles
GROUP BY spend_decile
ORDER BY spend_decile;

-- Q5.4 Purchase frequency: one-off vs repeat customers.
SELECT
    CASE WHEN orders = 1 THEN '1 order'
         WHEN orders = 2 THEN '2 orders'
         WHEN orders BETWEEN 3 AND 5 THEN '3-5 orders'
         ELSE '6+ orders' END                                         AS frequency_band,
    COUNT(*)                                                          AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                AS customer_share_pct,
    SUM(total_spend_kes)                                              AS revenue_kes,
    ROUND(100.0 * SUM(total_spend_kes) / SUM(SUM(total_spend_kes)) OVER (), 1) AS revenue_share_pct
FROM v_customer_summary
GROUP BY 1
ORDER BY MIN(orders);

-- Q5.5 Loyalty members vs non-members (association, not proof of cause).
SELECT
    c.loyalty_member,
    COUNT(*)                                     AS customers,
    ROUND(AVG(cs.orders), 2)                     AS avg_orders,
    ROUND(AVG(cs.total_spend_kes), 0)            AS avg_spend_kes,
    ROUND(100.0 * AVG(CASE WHEN cs.orders >= 2 THEN 1 ELSE 0 END), 1) AS repeat_rate_pct
FROM v_customer_summary cs
JOIN customers c ON c.customer_id = cs.customer_id
GROUP BY c.loyalty_member
ORDER BY c.loyalty_member DESC;

-- Q5.6 Where do customers shop? Share of each customer's orders at their
-- preferred (home) store, a measure of store loyalty.
SELECT
    ROUND(100.0 * AVG(CASE WHEN o.store_id = c.preferred_store_id THEN 1 ELSE 0 END), 1) AS pct_orders_at_home_store
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id;
