-- =============================================================================
-- 07_rfm_analysis.sql
-- RFM segmentation: which customers are most valuable, and which are at risk?
--
--   R (Recency)   = days since last purchase at 2025-12-31 (lower is better)
--   F (Frequency) = number of orders
--   M (Monetary)  = total net spend (KES)
--
-- Scoring (1 = worst, 5 = best):
--   * R uses FIXED business bands: <=90 days (5), 91-180 (4), 181-365 (3),
--     366-545 (2), >545 (1). Quintiles were tried first but produced bands so
--     wide (e.g. 255-406 days = score 3) that a customer silent for ten months
--     could be labelled "loyal". Fixed bands read naturally to management
--     ("bought within the last quarter / half-year / year").
--   * F uses FIXED bands (1, 2, 3, 4-5, 6+ orders). 77% of customers have
--     exactly one order, so quintiles would give identical customers
--     different F scores at random. Fixed bands treat equal behaviour equally.
--   * M uses NTILE(5) quintiles: spend varies smoothly, so equal-sized groups
--     are a fair relative ranking.
-- Depends on v_customer_summary (created in 05_customer_analysis.sql).
-- =============================================================================
SET search_path TO retail;

CREATE OR REPLACE VIEW v_customer_rfm AS
WITH scored AS (
    SELECT
        customer_id,
        days_since_last_purchase AS recency_days,
        orders                   AS frequency,
        total_spend_kes          AS monetary_kes,
        CASE WHEN days_since_last_purchase <= 90  THEN 5
             WHEN days_since_last_purchase <= 180 THEN 4
             WHEN days_since_last_purchase <= 365 THEN 3
             WHEN days_since_last_purchase <= 545 THEN 2
             ELSE 1 END                                         AS r_score,
        CASE WHEN orders >= 6 THEN 5
             WHEN orders >= 4 THEN 4
             WHEN orders = 3  THEN 3
             WHEN orders = 2  THEN 2
             ELSE 1 END                                         AS f_score,
        NTILE(5) OVER (ORDER BY total_spend_kes)                AS m_score    -- highest spend -> 5
    FROM v_customer_summary
)
SELECT
    *,
    r_score::text || f_score::text || m_score::text AS rfm_code,
    CASE
        -- Active in the last 6 months (R4-R5)
        WHEN r_score >= 4 AND f_score >= 4                  THEN 'Champions'
        WHEN r_score >= 4 AND f_score = 3                   THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score = 2                   THEN 'Potential Loyalists'
        WHEN r_score >= 4 AND f_score = 1                   THEN 'New / Recent One-off'
        -- Silent for more than 6 months but previously frequent
        WHEN f_score >= 4 AND m_score = 5                   THEN 'Cannot Lose Them'
        WHEN f_score >= 3                                   THEN 'At Risk'
        -- Silent for more than 6 months, infrequent
        WHEN r_score = 3                                    THEN 'Needs Attention'
        WHEN r_score = 2                                    THEN 'Hibernating'
        ELSE 'Lost'
    END AS rfm_segment
FROM scored;

-- Q7.1 Score boundaries: what does each R and M score actually mean?
SELECT
    r_score AS score,
    MIN(recency_days) AS recency_from_days, MAX(recency_days) AS recency_to_days
FROM v_customer_rfm GROUP BY r_score ORDER BY r_score;

SELECT
    m_score AS score,
    MIN(monetary_kes) AS spend_from_kes, MAX(monetary_kes) AS spend_to_kes
FROM v_customer_rfm GROUP BY m_score ORDER BY m_score;

-- Q7.2 Which customers are most valuable? Segment summary.
SELECT
    rfm_segment,
    COUNT(*)                                                         AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)               AS customer_share_pct,
    ROUND(AVG(recency_days), 0)                                      AS avg_recency_days,
    ROUND(AVG(frequency), 1)                                         AS avg_orders,
    ROUND(AVG(monetary_kes), 0)                                      AS avg_spend_kes,
    SUM(monetary_kes)                                                AS revenue_kes,
    ROUND(100.0 * SUM(monetary_kes) / SUM(SUM(monetary_kes)) OVER (), 1) AS revenue_share_pct
FROM v_customer_rfm
GROUP BY rfm_segment
ORDER BY revenue_kes DESC;

-- Q7.3 Recency x Frequency grid (customer counts): the shape behind the segments.
SELECT
    r_score,
    COUNT(*) FILTER (WHERE f_score = 1) AS f1_one_order,
    COUNT(*) FILTER (WHERE f_score = 2) AS f2_two_orders,
    COUNT(*) FILTER (WHERE f_score = 3) AS f3_three_orders,
    COUNT(*) FILTER (WHERE f_score = 4) AS f4_four_five,
    COUNT(*) FILTER (WHERE f_score = 5) AS f5_six_plus
FROM v_customer_rfm
GROUP BY r_score
ORDER BY r_score DESC;

-- Q7.4 Champions: the most valuable active customers (reward and retain).
SELECT customer_id, recency_days, frequency, monetary_kes, rfm_code
FROM v_customer_rfm
WHERE rfm_segment = 'Champions'
ORDER BY monetary_kes DESC
LIMIT 10;

-- Q7.5 At-risk high-value customers to win back first, with their preferred
-- store and loyalty status so the store team can act.
SELECT r.customer_id, r.rfm_segment, r.recency_days, r.frequency, r.monetary_kes,
       st.town AS preferred_store, c.loyalty_member
FROM v_customer_rfm r
JOIN customers c ON c.customer_id = r.customer_id
JOIN stores st   ON st.store_id = c.preferred_store_id
WHERE r.rfm_segment IN ('Cannot Lose Them', 'At Risk')
ORDER BY r.monetary_kes DESC
LIMIT 15;

-- Q7.6 Segment mix by preferred store: where are the at-risk customers?
SELECT
    st.town AS preferred_store,
    COUNT(*)                                                                    AS customers,
    COUNT(*) FILTER (WHERE r.rfm_segment IN ('Champions', 'Loyal Customers'))   AS champions_or_loyal,
    COUNT(*) FILTER (WHERE r.rfm_segment IN ('At Risk', 'Cannot Lose Them'))    AS at_risk,
    ROUND(100.0 * COUNT(*) FILTER (WHERE r.rfm_segment IN ('At Risk', 'Cannot Lose Them')) / COUNT(*), 1) AS at_risk_pct
FROM v_customer_rfm r
JOIN customers c ON c.customer_id = r.customer_id
JOIN stores st   ON st.store_id = c.preferred_store_id
GROUP BY st.town
ORDER BY at_risk_pct DESC;
