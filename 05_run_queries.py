"""
05_run_queries.py
Runs the SQL queries against the SQLite db and prints the results, so the
numbers in the README come from actual output. Q2 has a QUALIFY version in
the .sql file for engines that support it, but SQLite doesn't, so Q2b (same
thing with a subquery) is what runs here.
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect("sql/supply_chain.db")

queries = {
    "Q1: On-time % by supplier (worst first)": """
        SELECT
            s.supplier_name, s.region, COUNT(*) AS delivered_orders,
            ROUND(100.0 * SUM(CASE WHEN o.status = 'On-Time' THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct,
            ROUND(AVG(o.delay_days), 2) AS avg_delay_days
        FROM orders o JOIN suppliers s ON s.supplier_id = o.supplier_id
        WHERE o.status <> 'Cancelled'
        GROUP BY s.supplier_name, s.region
        ORDER BY on_time_pct ASC
        LIMIT 5;
    """,
    "Q2b: Worst supplier per region (RANK window function)": """
        SELECT * FROM (
            SELECT
                s.supplier_name, s.region, COUNT(*) AS orders,
                ROUND(100.0 * SUM(CASE WHEN o.status = 'On-Time' THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct,
                RANK() OVER (
                    PARTITION BY s.region
                    ORDER BY 100.0 * SUM(CASE WHEN o.status = 'On-Time' THEN 1 ELSE 0 END) / COUNT(*) ASC
                ) AS worst_in_region_rank
            FROM orders o JOIN suppliers s ON s.supplier_id = o.supplier_id
            WHERE o.status <> 'Cancelled'
            GROUP BY s.supplier_name, s.region
        ) ranked
        WHERE worst_in_region_rank = 1
        ORDER BY on_time_pct ASC;
    """,
    "Q3: Monthly spend + 3-month moving avg on-time %": """
        WITH monthly AS (
            SELECT
                strftime('%Y-%m', order_date) AS order_month,
                COUNT(*) AS orders,
                ROUND(SUM(quantity * unit_cost_usd), 2) AS spend_usd,
                100.0 * SUM(CASE WHEN status = 'On-Time' THEN 1 ELSE 0 END) / COUNT(*) AS on_time_pct
            FROM orders GROUP BY order_month
        )
        SELECT order_month, orders, spend_usd, ROUND(on_time_pct, 1) AS on_time_pct,
            ROUND(AVG(on_time_pct) OVER (ORDER BY order_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1) AS on_time_pct_3mo_avg
        FROM monthly ORDER BY order_month LIMIT 6;
    """,
    "Q4: Late orders over $10k, biggest first": """
        SELECT o.order_id, s.supplier_name, p.product_name, o.order_date,
               o.delay_days, ROUND(o.quantity * o.unit_cost_usd, 2) AS order_value_usd
        FROM orders o
        JOIN suppliers s ON s.supplier_id = o.supplier_id
        JOIN products  p ON p.product_id  = o.product_id
        WHERE o.status = 'Late' AND (o.quantity * o.unit_cost_usd) > 10000
        ORDER BY order_value_usd DESC LIMIT 5;
    """,
    "Q5: Lead time gap vs. promise by category": """
        SELECT p.category, COUNT(*) AS delivered_orders,
            ROUND(AVG(o.promised_lead_time_days), 2) AS avg_promised_days,
            ROUND(AVG(o.actual_lead_time_days), 2) AS avg_actual_days,
            ROUND(AVG(o.actual_lead_time_days) - AVG(o.promised_lead_time_days), 2) AS avg_gap_days
        FROM orders o JOIN products p ON p.product_id = o.product_id
        WHERE o.status <> 'Cancelled'
        GROUP BY p.category ORDER BY avg_gap_days DESC;
    """,
}

report_lines = []
for title, q in queries.items():
    df = pd.read_sql_query(q, conn)
    report_lines.append(f"### {title}\n")
    report_lines.append(df.to_string(index=False))
    report_lines.append("\n")
    print(f"=== {title} ===")
    print(df.to_string(index=False))
    print()

with open("sql/query_results.txt", "w") as f:
    f.write("\n".join(report_lines))

conn.close()
print("Saved full output to sql/query_results.txt")
