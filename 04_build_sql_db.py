"""
04_build_sql_db.py
Loads the CSVs into a SQLite file (sql/supply_chain.db) so I can run the SQL
queries against it. I used SQLite because it needs no server setup. The queries
are plain SQL (CTEs, window functions) so they should also work on MySQL 8+.
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect("sql/supply_chain.db")

orders = pd.read_csv("data/supply_chain_orders.csv")
suppliers = pd.read_csv("data/suppliers.csv")
products = pd.read_csv("data/products.csv")

orders.to_sql("orders", conn, if_exists="replace", index=False)
suppliers.to_sql("suppliers", conn, if_exists="replace", index=False)
products.to_sql("products", conn, if_exists="replace", index=False)

# indexes on the join columns
conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_supplier ON orders(supplier_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id)")
conn.commit()

print("Loaded tables into sql/supply_chain.db:")
for tbl in ["orders", "suppliers", "products"]:
    n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"  {tbl}: {n:,} rows")

conn.close()
