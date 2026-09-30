"""
02_clean_and_analyze.py
Cleans the orders file and works out the main delivery KPIs: on-time rate
(overall / supplier / category / region / month), delay vs promise, and how
much spend is sitting in late orders. Pandas only. Step 04 redoes the same
things in SQL as a cross-check.

Saves summary CSVs to data/ for the charts.
"""

import numpy as np
import pandas as pd

pd.set_option("display.width", 120)

orders = pd.read_csv("data/supply_chain_orders.csv", parse_dates=["order_date", "actual_delivery_date"])
suppliers = pd.read_csv("data/suppliers.csv")
products = pd.read_csv("data/products.csv")

# --- cleaning ---
# a few unit costs are missing, fill with that product's median cost
orders["unit_cost_usd"] = orders.groupby("product_id")["unit_cost_usd"].transform(
    lambda s: s.fillna(s.median())
)
orders["total_value_usd"] = (orders["quantity"] * orders["unit_cost_usd"]).round(2)

# quick checks
assert orders["order_id"].is_unique, "Duplicate order_id found"
assert orders["unit_cost_usd"].isna().sum() == 0, "Unit cost still has nulls after imputation"

orders["order_month"] = orders["order_date"].dt.to_period("M").astype(str)

# add supplier / product names
df = (
    orders
    .merge(suppliers, on="supplier_id", how="left")
    .merge(products, on="product_id", how="left")
)

# cancelled orders have no delivery so leave them out of delivery metrics
delivered = df[df["status"] != "Cancelled"].copy()

# --- headline numbers ---
overall_on_time_rate = (delivered["status"] == "On-Time").mean()
avg_delay_days = delivered["delay_days"].mean()
cancelled_rate = (df["status"] == "Cancelled").mean()
late_value_exposure = df.loc[df["status"] == "Late", "total_value_usd"].sum()
total_spend = df["total_value_usd"].sum()

print("=== Headline KPIs ===")
print(f"Overall on-time delivery rate : {overall_on_time_rate:.1%}")
print(f"Average delay vs. promise     : {avg_delay_days:+.2f} days")
print(f"Order cancellation rate       : {cancelled_rate:.1%}")
print(f"Total spend (18 months)       : ${total_spend:,.0f}")
print(f"Spend tied up in late orders  : ${late_value_exposure:,.0f} ({late_value_exposure/total_spend:.1%} of spend)")

# --- by supplier ---
by_supplier = (
    delivered.groupby(["supplier_id", "supplier_name", "region"])
    .agg(
        orders=("order_id", "count"),
        on_time_rate=("status", lambda s: (s == "On-Time").mean()),
        avg_delay_days=("delay_days", "mean"),
        total_spend_usd=("total_value_usd", "sum"),
    )
    .reset_index()
    .sort_values("on_time_rate")
)
by_supplier.to_csv("data/summary_by_supplier.csv", index=False)

# --- by category ---
by_category = (
    delivered.groupby("category")
    .agg(
        orders=("order_id", "count"),
        on_time_rate=("status", lambda s: (s == "On-Time").mean()),
        avg_lead_time_days=("actual_lead_time_days", "mean"),
        total_spend_usd=("total_value_usd", "sum"),
    )
    .reset_index()
    .sort_values("on_time_rate")
)
by_category.to_csv("data/summary_by_category.csv", index=False)

# --- by warehouse ---
by_region = (
    delivered.groupby("warehouse_region")
    .agg(
        orders=("order_id", "count"),
        on_time_rate=("status", lambda s: (s == "On-Time").mean()),
        avg_delay_days=("delay_days", "mean"),
    )
    .reset_index()
    .sort_values("on_time_rate")
)
by_region.to_csv("data/summary_by_region.csv", index=False)

# --- monthly ---
# uses df (not delivered) so cancelled orders count toward monthly volume/spend
monthly = (
    df.groupby("order_month")
    .agg(
        orders=("order_id", "count"),
        on_time_rate=("status", lambda s: (s == "On-Time").mean()),
        spend_usd=("total_value_usd", "sum"),
    )
    .reset_index()
    .sort_values("order_month")
)
monthly.to_csv("data/summary_monthly.csv", index=False)

print("\n=== Bottom 3 suppliers by on-time rate ===")
print(by_supplier[["supplier_name", "region", "orders", "on_time_rate", "avg_delay_days"]].head(3).to_string(index=False))

print("\nSaved summary tables to data/: summary_by_supplier.csv, summary_by_category.csv, "
      "summary_by_region.csv, summary_monthly.csv")
