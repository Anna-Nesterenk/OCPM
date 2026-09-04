"""
analytics/supplier.py
======================
Supplier 360 (ТЗ §11) and the Supplier Investigation drill-down
Supplier -> Batch -> Product -> Customer -> Return (ТЗ §8.1).
"""
from __future__ import annotations

import pandas as pd

from metrics import aggregate_batches


def supplier_list(batch_full: pd.DataFrame) -> pd.DataFrame:
    agg = aggregate_batches(batch_full, "supplier_id")
    meta = batch_full.drop_duplicates("supplier_id")[
        ["supplier_id", "supplier_name", "country", "supplier_type", "rating"]
    ]
    out = agg.merge(meta, on="supplier_id", how="left")
    n_po = batch_full.groupby("supplier_id")["po_id"].nunique().rename("n_purchase_orders").reset_index()
    n_del = batch_full.groupby("supplier_id")["delivery_id"].nunique().rename("n_deliveries").reset_index()
    out = out.merge(n_po, on="supplier_id", how="left").merge(n_del, on="supplier_id", how="left")
    return out.sort_values("revenue", ascending=False)


def supplier_360(batch_full: pd.DataFrame, sales_full: pd.DataFrame, supplier_id: str) -> dict:
    sb = batch_full[batch_full["supplier_id"] == supplier_id]
    if sb.empty:
        return {"found": False}

    row = supplier_list(batch_full)
    row = row[row["supplier_id"] == supplier_id]
    kpi = row.iloc[0].to_dict() if not row.empty else {}

    # Downstream: Supplier -> Batch -> Product -> Customer -> Return
    by_product = aggregate_batches(sb, "product_id").merge(
        sb.drop_duplicates("product_id")[["product_id", "product_name"]], on="product_id", how="left"
    ).sort_values("revenue", ascending=False)

    ss = sales_full[sales_full["supplier_id"] == supplier_id]
    customers = ss.groupby(["customer_id", "customer_name", "customer_segment"]).agg(
        revenue=("revenue", "sum"), units=("quantity", "sum"),
    ).reset_index().sort_values("revenue", ascending=False)

    returns_chain = sb[sb["return_qty"] > 0][
        ["batch_id", "product_name", "return_qty", "return_cost_total", "return_rate_qty"]
    ].sort_values("return_rate_qty", ascending=False)

    batches_tbl = sb[[
        "batch_id", "product_name", "channel_name", "warehouse_name", "received_date",
        "quantity_received", "pct_sold", "purchase_unit_price", "revenue_total",
        "net_contribution", "return_rate_qty", "supply_lead_days", "delay_days",
    ]].sort_values("received_date", ascending=False)

    return {
        "found": True, "kpi": kpi, "by_product": by_product, "customers": customers,
        "returns_chain": returns_chain, "batches": batches_tbl,
        "n_customers": int(ss["customer_id"].nunique()),
    }
