"""
analytics/product.py
=====================
Product 360 (ТЗ §10): procurement view, sales view, and the data behind the
Product Profitability Matrix.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from metrics import aggregate_batches, safe_div


def product_list(batch_full: pd.DataFrame) -> pd.DataFrame:
    """The full Product 360 table -- one row per product (ТЗ §10.1)."""
    agg = aggregate_batches(batch_full, "product_id")
    meta = batch_full.drop_duplicates("product_id")[
        ["product_id", "product_name", "category_id", "category_name", "brand", "standard_cost"]
    ]
    out = agg.merge(meta, on="product_id", how="left")
    return out.sort_values("revenue", ascending=False)


def product_360(batch_full: pd.DataFrame, sales_full: pd.DataFrame, product_id: str) -> dict:
    pb = batch_full[batch_full["product_id"] == product_id]
    if pb.empty:
        return {"found": False}

    row = product_list(batch_full)
    row = row[row["product_id"] == product_id]
    kpi = row.iloc[0].to_dict() if not row.empty else {}

    # 10.2 Procurement view: suppliers of this product
    procurement = pb.groupby("supplier_name").agg(
        n_batches=("batch_id", "nunique"),
        avg_price=("purchase_unit_price", "mean"),
        min_price=("purchase_unit_price", "min"),
        max_price=("purchase_unit_price", "max"),
        avg_lead=("supply_lead_days", "mean"),
    ).reset_index()
    delay = pb.groupby("supplier_name").apply(
        lambda x: (x["delay_days"] > 0).mean() * 100, include_groups=False
    ).rename("delay_rate_pct").reset_index()
    procurement = procurement.merge(delay, on="supplier_name", how="left").sort_values("avg_price")
    if len(procurement) >= 2:
        cheapest = procurement.sort_values("avg_price").iloc[0]
        most_reliable = procurement.sort_values("delay_rate_pct").iloc[0]
        cheapest_is_most_reliable = cheapest["supplier_name"] == most_reliable["supplier_name"]
    else:
        cheapest_is_most_reliable = None

    # 10.3 Sales view
    ps = sales_full[sales_full["product_id"] == product_id]
    sales_by_segment = ps.groupby("customer_segment")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)
    sales_by_region = ps.groupby("region")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)
    sales_by_channel = ps.groupby("sales_channel")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)

    batches_tbl = pb[[
        "batch_id", "supplier_name", "channel_name", "warehouse_name", "received_date",
        "quantity_received", "quantity_sold", "pct_sold", "purchase_unit_price",
        "revenue_total", "net_contribution", "return_rate_qty", "supply_lead_days", "days_to_first_sale",
    ]].sort_values("received_date", ascending=False)

    return {
        "found": True, "kpi": kpi, "procurement": procurement, "sales_by_segment": sales_by_segment,
        "sales_by_region": sales_by_region, "sales_by_channel": sales_by_channel, "batches": batches_tbl,
        "cheapest_is_most_reliable": cheapest_is_most_reliable,
        "n_customers": int(ps["customer_id"].nunique()),
    }
