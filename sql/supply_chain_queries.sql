-- supply_chain_queries.sql
-- Queries for the supply chain project. Plain SQL (CTEs + window functions),
-- should work on MySQL 8+, PostgreSQL and SQLite 3.25+. I ran them on
-- sql/supply_chain.db (SQLite) through 05_run_queries.py.
-- Note: Q3 uses strftime(), which is SQLite only. On MySQL use DATE_FORMAT().


-- Q1. On-time % and average delay per supplier, worst first
SELECT
    s.supplier_name,
    s.region,
    COUNT(*)                                                   AS delivered_orders,
    ROUND(100.0 * SUM(CASE WHEN o.status = 'On-Time' THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct,
    ROUND(AVG(o.delay_days), 2)                                AS avg_delay_days
FROM orders o
JOIN suppliers s ON s.supplier_id = o.supplier_id
WHERE o.status <> 'Cancelled'
GROUP BY s.supplier_name, s.region
ORDER BY on_time_pct ASC;


-- Q2. Worst supplier in each region (CTE + RANK window function)
WITH supplier_perf AS (
    SELECT
        s.supplier_name,
        s.region,
        COUNT(*)                                                                AS orders,
        100.0 * SUM(CASE WHEN o.status = 'On-Time' THEN 1 ELSE 0 END) / COUNT(*) AS on_time_pct
    FROM orders o
    JOIN suppliers s ON s.supplier_id = o.supplier_id
    WHERE o.status <> 'Cancelled'
    GROUP BY s.supplier_name, s.region
)
SELECT
    region,
    supplier_name,
    orders,
    ROUND(on_time_pct, 1) AS on_time_pct,
    RANK() OVER (PARTITION BY region ORDER BY on_time_pct ASC) AS worst_in_region_rank
FROM supplier_perf
QUALIFY worst_in_region_rank = 1   -- QUALIFY isn't supported in MySQL/SQLite, use Q2b below
ORDER BY on_time_pct ASC;

-- Q2b. Same as Q2 but with a subquery instead of QUALIFY (MySQL 8 / SQLite)
SELECT * FROM (
    SELECT
        s.supplier_name,
        s.region,
        COUNT(*) AS orders,
        ROUND(100.0 * SUM(CASE WHEN o.status = 'On-Time' THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct,
        RANK() OVER (
            PARTITION BY s.region
            ORDER BY 100.0 * SUM(CASE WHEN o.status = 'On-Time' THEN 1 ELSE 0 END) / COUNT(*) ASC
        ) AS worst_in_region_rank
    FROM orders o
    JOIN suppliers s ON s.supplier_id = o.supplier_id
    WHERE o.status <> 'Cancelled'
    GROUP BY s.supplier_name, s.region
) ranked
WHERE worst_in_region_rank = 1
ORDER BY on_time_pct ASC;


-- Q3. Monthly orders and spend, plus a 3-month moving average of on-time %
WITH monthly AS (
    SELECT
        strftime('%Y-%m', order_date) AS order_month,
        COUNT(*)                                                                AS orders,
        ROUND(SUM(quantity * unit_cost_usd), 2)                                 AS spend_usd,
        100.0 * SUM(CASE WHEN status = 'On-Time' THEN 1 ELSE 0 END) / COUNT(*)  AS on_time_pct
    FROM orders
    GROUP BY order_month
)
SELECT
    order_month,
    orders,
    spend_usd,
    ROUND(on_time_pct, 1) AS on_time_pct,
    ROUND(AVG(on_time_pct) OVER (
        ORDER BY order_month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 1) AS on_time_pct_3mo_avg
FROM monthly
ORDER BY order_month;


-- Q4. Late orders over $10,000, biggest first (what to chase first)
SELECT
    o.order_id,
    s.supplier_name,
    p.product_name,
    o.order_date,
    o.delay_days,
    ROUND(o.quantity * o.unit_cost_usd, 2) AS order_value_usd
FROM orders o
JOIN suppliers s ON s.supplier_id = o.supplier_id
JOIN products  p ON p.product_id  = o.product_id
WHERE o.status = 'Late'
  AND (o.quantity * o.unit_cost_usd) > 10000
ORDER BY order_value_usd DESC
LIMIT 20;


-- Q5. Promised vs actual lead time by category
SELECT
    p.category,
    COUNT(*)                                    AS delivered_orders,
    ROUND(AVG(o.promised_lead_time_days), 2)    AS avg_promised_days,
    ROUND(AVG(o.actual_lead_time_days), 2)      AS avg_actual_days,
    ROUND(AVG(o.actual_lead_time_days) - AVG(o.promised_lead_time_days), 2) AS avg_gap_days
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.status <> 'Cancelled'
GROUP BY p.category
ORDER BY avg_gap_days DESC;
