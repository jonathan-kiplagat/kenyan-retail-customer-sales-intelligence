-- =============================================================================
-- 03_data_quality_checks.sql
-- Verify the loaded database. Every check should return the "expected" value;
-- PRIMARY KEY, FOREIGN KEY and CHECK constraints already block most problems,
-- these queries prove it and cover rules that constraints cannot express.
-- =============================================================================
SET search_path TO retail;

-- Q3.1 Row counts against the cleaned CSV files (Milestone 2).
SELECT 'orders' AS table_name, COUNT(*) AS actual_rows, 2650 AS expected_rows FROM orders
UNION ALL SELECT 'sales_transactions', COUNT(*), 2988 FROM sales_transactions
UNION ALL SELECT 'customers', COUNT(*), 1800 FROM customers
UNION ALL SELECT 'products', COUNT(*), 40 FROM products
UNION ALL SELECT 'stores', COUNT(*), 6 FROM stores;

-- Q3.2 Orphan check: lines whose order, product or promotion does not exist.
-- (LEFT JOIN ... IS NULL finds rows with no match.) Expected: 0 everywhere.
SELECT
    COUNT(*) FILTER (WHERE o.order_id IS NULL)                              AS lines_without_order,
    COUNT(*) FILTER (WHERE p.product_id IS NULL)                            AS lines_without_product,
    COUNT(*) FILTER (WHERE s.promotion_id IS NOT NULL AND pr.promotion_id IS NULL) AS lines_with_unknown_promo
FROM sales_transactions s
LEFT JOIN orders o      ON o.order_id = s.order_id
LEFT JOIN products p    ON p.product_id = s.product_id
LEFT JOIN promotions pr ON pr.promotion_id = s.promotion_id;

-- Q3.3 Orders with no product lines (should never happen). Expected: 0.
SELECT COUNT(*) AS orders_without_lines
FROM orders o
WHERE NOT EXISTS (SELECT 1 FROM sales_transactions s WHERE s.order_id = o.order_id);

-- Q3.4 Missing values in key columns. Walk-in orders (NULL customer) are
-- expected: 21 lines were kept as walk-ins in Milestone 2.
SELECT
    COUNT(*) FILTER (WHERE customer_id IS NULL)       AS walk_in_orders,
    COUNT(*) FILTER (WHERE payment_method = 'Unknown') AS unknown_payment_orders,
    COUNT(*) FILTER (WHERE store_id IS NULL)          AS orders_missing_store
FROM orders;

-- Q3.5 Study period: every order must fall in 2024-01-01 .. 2025-12-31.
SELECT MIN(transaction_date) AS first_order, MAX(transaction_date) AS last_order,
       COUNT(*) FILTER (WHERE transaction_date NOT BETWEEN '2024-01-01' AND '2025-12-31') AS out_of_range
FROM orders;

-- Q3.6 Database-generated money columns vs the Python-cleaned CSV values.
-- Proves both tools calculate revenue, discount and profit identically.
SELECT
    COUNT(*)                                                                     AS lines_compared,
    COUNT(*) FILTER (WHERE ABS(s.total_amount   - st.total_amount::numeric)    > 0.01) AS total_mismatches,
    COUNT(*) FILTER (WHERE ABS(s.discount_amount - st.discount_amount::numeric) > 0.01) AS discount_mismatches,
    COUNT(*) FILTER (WHERE ABS(s.profit         - st.profit::numeric)          > 0.01) AS profit_mismatches,
    SUM(s.total_amount)                                                          AS db_revenue,
    SUM(st.total_amount::numeric)                                                AS csv_revenue
FROM sales_transactions s
JOIN staging.sales st ON st.transaction_id = s.transaction_id;

-- Q3.7 Promotion rules: a promoted line must fall inside its campaign window,
-- carry the campaign's discount and belong to the target category. Expected: 0.
SELECT
    COUNT(*) FILTER (WHERE o.transaction_date NOT BETWEEN pr.start_date AND pr.end_date) AS outside_window,
    COUNT(*) FILTER (WHERE s.discount_percentage <> pr.discount_percentage)              AS wrong_discount,
    COUNT(*) FILTER (WHERE p.category <> pr.target_category)                             AS wrong_category
FROM sales_transactions s
JOIN orders o      ON o.order_id = s.order_id
JOIN products p    ON p.product_id = s.product_id
JOIN promotions pr ON pr.promotion_id = s.promotion_id;

-- Q3.8 Customers who registered after their first purchase. Expected: 0.
SELECT COUNT(*) AS registered_after_first_purchase
FROM customers c
JOIN (SELECT customer_id, MIN(transaction_date) AS first_purchase
      FROM orders WHERE customer_id IS NOT NULL GROUP BY customer_id) f USING (customer_id)
WHERE c.registration_date > f.first_purchase;

-- Q3.9 Constraint inventory: proof that keys and rules are enforced by the database.
SELECT tc.table_name, tc.constraint_type, COUNT(*) AS constraints
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'retail' AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK')
  AND tc.constraint_name NOT LIKE '%_not_null'
GROUP BY tc.table_name, tc.constraint_type
ORDER BY tc.table_name, tc.constraint_type;
