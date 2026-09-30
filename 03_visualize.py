"""
03_visualize.py
Makes the four charts used in the README. Colours are set at the top so they
stay consistent: blue for normal values, blue/red for delay (red = late), and
green/orange/red for on-time / late / cancelled.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd

# colours
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS = "#c3c2b7"

BLUE = "#2a78d6"
RED = "#e34948"
GOOD = "#0ca30c"
SERIOUS = "#ec835a"
CRITICAL = "#d03b3b"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_SECONDARY,
    "text.color": INK_PRIMARY,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "grid.color": GRIDLINE,
    "axes.grid": True,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "font.size": 11,
})

# load the summary files from step 2
by_supplier = pd.read_csv("data/summary_by_supplier.csv")
by_category = pd.read_csv("data/summary_by_category.csv")
monthly = pd.read_csv("data/summary_monthly.csv")
orders = pd.read_csv("data/supply_chain_orders.csv")

overall_on_time = (orders.loc[orders["status"] != "Cancelled", "status"] == "On-Time").mean()

# Chart A: on-time rate by supplier
fig, ax = plt.subplots(figsize=(8, 5.5))
d = by_supplier.sort_values("on_time_rate")
bars = ax.barh(d["supplier_name"], d["on_time_rate"] * 100, color=BLUE, height=0.6)
ax.axvline(overall_on_time * 100, color=INK_MUTED, linestyle="--", linewidth=1.2)
ax.text(overall_on_time * 100 + 1, -0.8, f"Overall avg {overall_on_time:.0%}",
        color=INK_SECONDARY, fontsize=9, va="top")
for bar, val in zip(bars, d["on_time_rate"]):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2, f"{val:.0%}",
            va="center", fontsize=9, color=INK_SECONDARY)
ax.set_xlim(0, 80)
ax.set_xlabel("On-time delivery rate")
ax.set_title("On-Time Delivery Rate by Supplier", fontsize=13, fontweight="bold", loc="left", pad=14)
ax.grid(axis="y", visible=False)
plt.tight_layout()
plt.savefig("charts/A_on_time_by_supplier.png", dpi=180)
plt.close()

# Chart B: monthly on-time trend
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(monthly["order_month"], monthly["on_time_rate"] * 100, color=BLUE, linewidth=2,
        marker="o", markersize=4)
ax.axhline(overall_on_time * 100, color=INK_MUTED, linestyle="--", linewidth=1)
ax.set_ylabel("On-time delivery rate (%)")
ax.set_title("Monthly On-Time Delivery Rate Trend", fontsize=13, fontweight="bold", loc="left", pad=14)
ax.set_ylim(30, 80)
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.tight_layout()
plt.savefig("charts/B_monthly_on_time_trend.png", dpi=180)
plt.close()

# Chart C: on-time / late / cancelled split
status_counts = orders["status"].value_counts()
status_order = ["On-Time", "Late", "Cancelled"]
status_colors = {"On-Time": GOOD, "Late": SERIOUS, "Cancelled": CRITICAL}
vals = [status_counts.get(s, 0) for s in status_order]
pct = [v / status_counts.sum() * 100 for v in vals]

fig, ax = plt.subplots(figsize=(7, 4.5))
bars = ax.bar(status_order, pct, color=[status_colors[s] for s in status_order], width=0.55)
for bar, v, p in zip(bars, vals, pct):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
            f"{p:.1f}%\n({v:,} orders)", ha="center", fontsize=9.5, color=INK_PRIMARY)
ax.set_ylim(0, 70)
ax.set_ylabel("Share of orders")
ax.set_title("Order Outcome Breakdown (18 months)", fontsize=13, fontweight="bold", loc="left", pad=14)
ax.grid(axis="x", visible=False)
plt.tight_layout()
plt.savefig("charts/C_status_breakdown.png", dpi=180)
plt.close()

# Chart D: average delay by category (red = late, blue = early)
d = by_category.copy()
delivered = orders[orders["status"] != "Cancelled"].merge(
    pd.read_csv("data/products.csv"), on="product_id", how="left"
)
avg_delay_by_cat = delivered.groupby("category")["delay_days"].mean().sort_values()

fig, ax = plt.subplots(figsize=(8, 4.8))
colors = [RED if v > 0 else BLUE for v in avg_delay_by_cat.values]
bars = ax.barh(avg_delay_by_cat.index, avg_delay_by_cat.values, color=colors, height=0.55)
ax.axvline(0, color=INK_MUTED, linewidth=1)
for bar, v in zip(bars, avg_delay_by_cat.values):
    align = "left" if v >= 0 else "right"
    offset = 0.05 if v >= 0 else -0.05
    ax.text(v + offset, bar.get_y() + bar.get_height() / 2, f"{v:+.2f}d",
            va="center", ha=align, fontsize=9, color=INK_SECONDARY)
ax.set_xlabel("Avg. delay vs. promised lead time (days), negative = early")
ax.set_title("Average Delivery Delay by Product Category", fontsize=13, fontweight="bold", loc="left", pad=14)
ax.grid(axis="y", visible=False)
plt.tight_layout()
plt.savefig("charts/D_delay_by_category.png", dpi=180)
plt.close()

print("Saved 4 charts to charts/: A_on_time_by_supplier.png, B_monthly_on_time_trend.png, "
      "C_status_breakdown.png, D_delay_by_category.png")
