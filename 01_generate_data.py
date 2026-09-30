"""
01_generate_data.py
Makes a fake purchase order dataset for the project. I didn't want to use real
company data, so I simulated a food manufacturer buying from suppliers in the
Gulf and India. Seeded so the numbers are the same every run.

Writes: data/supply_chain_orders.csv, data/suppliers.csv, data/products.csv
"""

import numpy as np
import pandas as pd
from datetime import timedelta

rng = np.random.default_rng(42)

# suppliers and products (small lookup tables)
suppliers = pd.DataFrame({
    "supplier_id": [f"SUP-{i:02d}" for i in range(1, 13)],
    "supplier_name": [
        "Alpine Dairy Co", "GreenLeaf Packaging", "Coastal Cold Storage",
        "Nordic Freight Partners", "Prime Poultry Supply", "Sunrise Grain Traders",
        "BlueBox Logistics", "Highland Meats Ltd", "Delta Plastics & Film",
        "Everest Ingredients", "Metro Distribution", "Harbor Fresh Produce",
    ],
    "region": rng.choice(
        ["UAE", "Saudi Arabia", "Qatar", "Kuwait", "India"], size=12,
        p=[0.30, 0.25, 0.15, 0.10, 0.20]
    ),
    # hidden "true" reliability, only used to drive the delays below (dropped before saving)
    "reliability_score": rng.beta(a=6, b=2.2, size=12).round(3),
})

products = pd.DataFrame({
    "product_id": [f"PRD-{i:02d}" for i in range(1, 9)],
    "product_name": [
        "Frozen Poultry Cuts", "Dairy Base Mix", "Corrugated Cartons",
        "Flexible Packaging Film", "Grain & Cereal Base", "Cold Chain Pallets",
        "Preservative Additives", "Produce - Mixed Vegetables",
    ],
    "category": [
        "Raw Material", "Raw Material", "Packaging", "Packaging",
        "Raw Material", "Logistics Equipment", "Additives", "Raw Material",
    ],
})

# orders, 18 months worth
N_ORDERS = 3200
start_date = pd.Timestamp("2025-01-01")
end_date = pd.Timestamp("2026-06-30")
date_range_days = (end_date - start_date).days

order_dates = start_date + pd.to_timedelta(
    rng.integers(0, date_range_days, size=N_ORDERS), unit="D"
)

supplier_idx = rng.integers(0, len(suppliers), size=N_ORDERS)
product_idx = rng.integers(0, len(products), size=N_ORDERS)

warehouse_regions = rng.choice(
    ["Dubai DC", "Riyadh DC", "Doha DC", "Kuwait City DC", "Mumbai DC"],
    size=N_ORDERS, p=[0.30, 0.25, 0.15, 0.10, 0.20]
)

promised_lead_time = rng.integers(3, 15, size=N_ORDERS)  # days the supplier promised
quantity = rng.integers(50, 5000, size=N_ORDERS)
unit_cost = np.round(rng.uniform(0.8, 45.0, size=N_ORDERS), 2)

orders = pd.DataFrame({
    "order_id": [f"PO-{100000+i}" for i in range(N_ORDERS)],
    "order_date": order_dates,
    "supplier_id": suppliers["supplier_id"].values[supplier_idx],
    "product_id": products["product_id"].values[product_idx],
    "warehouse_region": warehouse_regions,
    "quantity": quantity,
    "unit_cost_usd": unit_cost,
    "promised_lead_time_days": promised_lead_time,
})

# bring in reliability so worse suppliers actually deliver worse
orders = orders.merge(suppliers[["supplier_id", "reliability_score"]], on="supplier_id", how="left")

# delay = random noise around the promise. lower reliability means a bigger
# average delay and more spread. negative = early, 0 = on time, positive = late
noise_scale = (1 - orders["reliability_score"]) * 6 + 0.6
delay_days = rng.normal(loc=(1 - orders["reliability_score"]) * 3 - 0.8, scale=noise_scale)
delay_days = np.round(delay_days).astype(int)

orders["actual_delivery_date"] = orders["order_date"] + pd.to_timedelta(
    orders["promised_lead_time_days"] + delay_days, unit="D"
)
orders["actual_lead_time_days"] = (orders["actual_delivery_date"] - orders["order_date"]).dt.days
orders["delay_days"] = orders["actual_lead_time_days"] - orders["promised_lead_time_days"]

# ~2.5% of orders get cancelled, so no delivery info for those
cancel_mask = rng.random(N_ORDERS) < 0.025
orders.loc[cancel_mask, "actual_delivery_date"] = pd.NaT
orders.loc[cancel_mask, "actual_lead_time_days"] = np.nan
orders.loc[cancel_mask, "delay_days"] = np.nan

orders["status"] = np.select(
    [
        cancel_mask,
        orders["delay_days"] <= 0,
        orders["delay_days"] > 0,
    ],
    ["Cancelled", "On-Time", "Late"],
    default="On-Time",
)

# knock out ~1% of unit costs on purpose so there's something to clean in step 2
missing_mask = rng.random(N_ORDERS) < 0.01
orders.loc[missing_mask, "unit_cost_usd"] = np.nan

orders = orders.drop(columns=["reliability_score"])
orders["total_value_usd"] = (orders["quantity"] * orders["unit_cost_usd"]).round(2)

# save (data/ folder needs to exist already)
suppliers.drop(columns=["reliability_score"]).to_csv("data/suppliers.csv", index=False)
products.to_csv("data/products.csv", index=False)
orders.to_csv("data/supply_chain_orders.csv", index=False)

print(f"Generated {len(orders):,} orders across {len(suppliers)} suppliers and {len(products)} products.")
print(orders["status"].value_counts(normalize=True).round(3))
